import argparse
import json
import os
from collections import defaultdict

from neo4j import GraphDatabase


DEFAULT_DATABASE = "taxjc"
ENTRY_EXCLUDED_FIELDS = {
    "entryId",
    "entryHash",
    "blockId",
    "createdAt",
}
ENTRY_SUMMARY_FIELDS = [
    "eventType",
    "sourceId",
    "Year",
    "Qtr",
    "Description",
    "TransactionDate",
    "Billed",
    "Paid",
    "Adjusted",
    "OpenBalance",
]


def _parse_account_list(raw_accounts):
    if not raw_accounts:
        return None

    parsed_accounts = []
    for value in raw_accounts.split(","):
        account = value.strip()
        if not account:
            continue
        parsed_accounts.append(int(account))

    return parsed_accounts or None


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Diff two ledger snapshots in Neo4j using LedgerBlock and "
            "LedgerEntry data."
        )
    )
    parser.add_argument(
        "--accounts",
        help=(
            "Comma-separated account numbers to diff. Defaults to all accounts "
            "with at least two ledger blocks."
        ),
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_DATABASE,
        help=f"Neo4j database to inspect. Default: {DEFAULT_DATABASE}.",
    )
    parser.add_argument(
        "--old-block-id",
        help="Explicit older blockId to compare.",
    )
    parser.add_argument(
        "--new-block-id",
        help="Explicit newer blockId to compare.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Default: text.",
    )
    return parser.parse_args()


def _connect_driver():
    neo4j_url = os.getenv("Neo4jFinDBUrl")
    username = os.getenv("Neo4jFinDBUserName")
    password = os.getenv("Neo4jFinDBPassword")

    if not neo4j_url or not username or not password:
        raise RuntimeError(
            "Missing Neo4j connection env vars. Expected Neo4jFinDBUrl, "
            "Neo4jFinDBUserName, and Neo4jFinDBPassword."
        )

    return GraphDatabase.driver(neo4j_url, auth=(username, password))


def _load_account_blocks(driver, database, accounts=None):
    query = """
    MATCH (a:Account)
    WHERE $accounts IS NULL OR a.Account IN $accounts
    MATCH (b:LedgerBlock)-[:LEDGER_FOR]->(a)
    OPTIONAL MATCH (b)-[:PREVIOUS_BLOCK]->(prev:LedgerBlock)
    RETURN a.Account AS account,
           a.address AS address,
           b.blockId AS blockId,
           b.blockHeight AS blockHeight,
           b.runId AS runId,
           b.createdAt AS createdAt,
           b.sourceHash AS sourceHash,
           b.entryCount AS entryCount,
           prev.blockId AS previousBlockId
    ORDER BY account, blockHeight
    """

    with driver.session(database=database) as session:
        result = session.run(query, accounts=accounts)
        records = [record.data() for record in result]

    blocks_by_account = defaultdict(list)
    for record in records:
        blocks_by_account[record["account"]].append(record)
    return blocks_by_account


def _load_blocks_by_id(driver, database, old_block_id, new_block_id):
    query = """
    MATCH (b:LedgerBlock)
    WHERE b.blockId IN [$oldBlockId, $newBlockId]
    MATCH (b)-[:LEDGER_FOR]->(a:Account)
    OPTIONAL MATCH (b)-[:PREVIOUS_BLOCK]->(prev:LedgerBlock)
    RETURN a.Account AS account,
           a.address AS address,
           b.blockId AS blockId,
           b.blockHeight AS blockHeight,
           b.runId AS runId,
           b.createdAt AS createdAt,
           b.sourceHash AS sourceHash,
           b.entryCount AS entryCount,
           prev.blockId AS previousBlockId
    ORDER BY b.blockHeight
    """

    with driver.session(database=database) as session:
        result = session.run(
            query,
            oldBlockId=old_block_id,
            newBlockId=new_block_id,
        )
        records = [record.data() for record in result]

    if len(records) != 2:
        raise RuntimeError(
            "Could not load both requested blocks. "
            f"Expected 2 blocks, found {len(records)}."
        )

    accounts = {record["account"] for record in records}
    if len(accounts) != 1:
        raise RuntimeError("Requested blocks do not belong to the same account.")

    records_by_id = {record["blockId"]: record for record in records}
    return records_by_id[old_block_id], records_by_id[new_block_id]


def _load_block_entries(driver, database, block_id):
    query = """
    MATCH (:LedgerBlock {blockId: $blockId})-[:CONTAINS]->(e:LedgerEntry)
    RETURN properties(e) AS entry
    ORDER BY e.sourceId, e.ordinal, e.entryId
    """

    with driver.session(database=database) as session:
        result = session.run(query, blockId=block_id)
        return [record["entry"] for record in result]


def _canonical_entry(entry):
    canonical = {}
    for key, value in entry.items():
        if key in ENTRY_EXCLUDED_FIELDS:
            continue
        canonical[key] = value
    return canonical


def _entry_signature(entry):
    return json.dumps(_canonical_entry(entry), sort_keys=True, separators=(",", ":"))


def _entry_summary(entry):
    return {field: entry.get(field) for field in ENTRY_SUMMARY_FIELDS}


def _group_entries_by_source_id(entries):
    grouped = defaultdict(list)
    for entry in entries:
        grouped[entry.get("sourceId")].append(entry)

    for source_id in grouped:
        grouped[source_id].sort(key=_entry_signature)

    return grouped


def _build_changed_field_map(old_entry, new_entry):
    changes = {}
    old_canonical = _canonical_entry(old_entry)
    new_canonical = _canonical_entry(new_entry)
    for key in sorted(set(old_canonical) | set(new_canonical)):
        if old_canonical.get(key) != new_canonical.get(key):
            changes[key] = {
                "old": old_canonical.get(key),
                "new": new_canonical.get(key),
            }
    return changes


def _diff_entries(old_entries, new_entries):
    added_rows = []
    removed_rows = []
    changed_rows = []

    old_grouped = _group_entries_by_source_id(old_entries)
    new_grouped = _group_entries_by_source_id(new_entries)

    for source_id in sorted(set(old_grouped) | set(new_grouped)):
        old_rows = old_grouped.get(source_id, [])
        new_rows = new_grouped.get(source_id, [])
        paired = min(len(old_rows), len(new_rows))

        for index in range(paired):
            old_entry = old_rows[index]
            new_entry = new_rows[index]
            changed_fields = _build_changed_field_map(old_entry, new_entry)
            if changed_fields:
                changed_rows.append(
                    {
                        "sourceId": source_id,
                        "old": _entry_summary(old_entry),
                        "new": _entry_summary(new_entry),
                        "changedFields": changed_fields,
                    }
                )

        for old_entry in old_rows[paired:]:
            removed_rows.append(_entry_summary(old_entry))

        for new_entry in new_rows[paired:]:
            added_rows.append(_entry_summary(new_entry))

    return {
        "addedRows": added_rows,
        "removedRows": removed_rows,
        "changedRows": changed_rows,
    }


def _build_comparison(old_block, new_block, old_entries, new_entries):
    diff = _diff_entries(old_entries, new_entries)
    source_changed = old_block["sourceHash"] != new_block["sourceHash"]

    return {
        "account": old_block["account"],
        "address": old_block["address"],
        "oldBlock": old_block,
        "newBlock": new_block,
        "sourceChanged": source_changed,
        "summary": {
            "oldEntryCount": len(old_entries),
            "newEntryCount": len(new_entries),
            "addedRowCount": len(diff["addedRows"]),
            "removedRowCount": len(diff["removedRows"]),
            "changedRowCount": len(diff["changedRows"]),
        },
        "addedRows": diff["addedRows"],
        "removedRows": diff["removedRows"],
        "changedRows": diff["changedRows"],
    }


def _select_latest_two_blocks(blocks_by_account):
    comparisons = []
    skipped_accounts = []

    for account, blocks in sorted(blocks_by_account.items()):
        if len(blocks) < 2:
            skipped_accounts.append(account)
            continue
        comparisons.append((blocks[-2], blocks[-1]))

    return comparisons, skipped_accounts


def diff_ledger_snapshots(
    database=DEFAULT_DATABASE,
    accounts=None,
    old_block_id=None,
    new_block_id=None,
):
    if bool(old_block_id) != bool(new_block_id):
        raise RuntimeError("Use both --old-block-id and --new-block-id together.")

    driver = _connect_driver()
    try:
        if old_block_id and new_block_id:
            block_pairs = [_load_blocks_by_id(driver, database, old_block_id, new_block_id)]
            skipped_accounts = []
        else:
            blocks_by_account = _load_account_blocks(driver, database, accounts)
            block_pairs, skipped_accounts = _select_latest_two_blocks(blocks_by_account)

        comparisons = []
        for old_block, new_block in block_pairs:
            old_entries = _load_block_entries(driver, database, old_block["blockId"])
            new_entries = _load_block_entries(driver, database, new_block["blockId"])
            comparisons.append(
                _build_comparison(old_block, new_block, old_entries, new_entries)
            )
    finally:
        driver.close()

    return {
        "database": database,
        "comparisonCount": len(comparisons),
        "skippedAccounts": skipped_accounts,
        "comparisons": comparisons,
    }


def _print_text_report(report):
    print(
        f"Ledger snapshot diff for database '{report['database']}' "
        f"({report['comparisonCount']} comparison(s))"
    )

    if report["skippedAccounts"]:
        skipped = ", ".join(str(account) for account in report["skippedAccounts"])
        print(f"Skipped accounts with fewer than two blocks: {skipped}")

    if not report["comparisons"]:
        print("No ledger snapshot pairs available to compare.")
        return 0

    for comparison in report["comparisons"]:
        old_block = comparison["oldBlock"]
        new_block = comparison["newBlock"]
        summary = comparison["summary"]

        print("")
        print(
            f"Account {comparison['account']} | "
            f"{comparison['address'] or 'address unavailable'}"
        )
        print(
            f"  old: blockHeight={old_block['blockHeight']} "
            f"runId={old_block['runId']} blockId={old_block['blockId']}"
        )
        print(
            f"  new: blockHeight={new_block['blockHeight']} "
            f"runId={new_block['runId']} blockId={new_block['blockId']}"
        )
        print(
            f"  sourceHash: {'CHANGED' if comparison['sourceChanged'] else 'UNCHANGED'} "
            f"({old_block['sourceHash']} -> {new_block['sourceHash']})"
        )
        print(
            f"  rows: +{summary['addedRowCount']} "
            f"-{summary['removedRowCount']} "
            f"~{summary['changedRowCount']}"
        )

        if comparison["addedRows"]:
            print("  added rows:")
            for row in comparison["addedRows"]:
                print(f"    + {json.dumps(row, sort_keys=True)}")

        if comparison["removedRows"]:
            print("  removed rows:")
            for row in comparison["removedRows"]:
                print(f"    - {json.dumps(row, sort_keys=True)}")

        if comparison["changedRows"]:
            print("  changed rows:")
            for row in comparison["changedRows"]:
                print(
                    "    ~ "
                    + json.dumps(
                        {
                            "sourceId": row["sourceId"],
                            "old": row["old"],
                            "new": row["new"],
                            "changedFields": row["changedFields"],
                        },
                        sort_keys=True,
                    )
                )

    return 0


def main():
    args = parse_args()
    report = diff_ledger_snapshots(
        database=args.database,
        accounts=_parse_account_list(args.accounts),
        old_block_id=args.old_block_id,
        new_block_id=args.new_block_id,
    )

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(0)

    raise SystemExit(_print_text_report(report))


if __name__ == "__main__":
    main()
