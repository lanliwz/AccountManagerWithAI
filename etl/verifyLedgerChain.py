import argparse
import hashlib
import json
import os
import sys

from neo4j import GraphDatabase


DEFAULT_DATABASE = "taxjc"


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


def _compute_block_hash(block_id, prev_hash, source_hash, block_height, entry_count):
    return hashlib.sha1(
        json.dumps(
            {
                "blockId": block_id,
                "prevHash": prev_hash,
                "sourceHash": source_hash,
                "blockHeight": block_height,
                "entryCount": entry_count,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Verify LedgerBlock and LedgerEntry integrity for the JCTaxLedger "
            "append-only chain stored in Neo4j."
        )
    )
    parser.add_argument(
        "--accounts",
        help="Comma-separated account numbers to verify instead of all Account nodes in the database.",
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_DATABASE,
        help=f"Neo4j database to verify. Default: {DEFAULT_DATABASE}.",
    )
    return parser.parse_args()


def _load_account_chains(driver, database, accounts=None):
    query = """
    MATCH (a:Account)
    WHERE $accounts IS NULL OR a.Account IN $accounts
    OPTIONAL MATCH (b:LedgerBlock)-[:LEDGER_FOR]->(a)
    OPTIONAL MATCH (b)-[:CONTAINS]->(e:LedgerEntry)
    OPTIONAL MATCH (b)-[prev_rel]->(prev:LedgerBlock)
    WHERE prev_rel IS NULL OR type(prev_rel) = 'PREVIOUS_BLOCK'
    RETURN a.Account AS account,
           a.accountId AS accountId,
           b.blockId AS blockId,
           b.blockHash AS blockHash,
           properties(b)['prevHash'] AS prevHash,
           b.sourceHash AS sourceHash,
           b.blockHeight AS blockHeight,
           b.entryCount AS entryCount,
           count(DISTINCT e) AS actualEntryCount,
           collect(DISTINCT prev.blockId) AS prevBlockIds
    ORDER BY account, blockHeight, blockId
    """

    with driver.session(database=database) as session:
        result = session.run(query, accounts=accounts)
        return [record.data() for record in result]


def verify_ledger_chain(database=DEFAULT_DATABASE, accounts=None):
    neo4j_url = os.getenv("Neo4jFinDBUrl")
    username = os.getenv("Neo4jFinDBUserName")
    password = os.getenv("Neo4jFinDBPassword")

    if not neo4j_url or not username or not password:
        raise RuntimeError(
            "Missing Neo4j connection env vars. Expected Neo4jFinDBUrl, "
            "Neo4jFinDBUserName, and Neo4jFinDBPassword."
        )

    driver = GraphDatabase.driver(neo4j_url, auth=(username, password))
    try:
        records = _load_account_chains(driver, database, accounts)
    finally:
        driver.close()

    chains = {}
    for record in records:
        chains.setdefault(record["account"], []).append(record)

    if not chains:
        print(f"No Account nodes found in database '{database}'.")
        return 0

    failures = []

    for account, chain in chains.items():
        blocks = [record for record in chain if record["blockId"]]
        if not blocks:
            failures.append(f"Account {account}: missing LedgerBlock nodes")
            continue

        expected_prev_block_id = None
        expected_prev_hash = None

        for expected_height, block in enumerate(blocks):
            block_id = block["blockId"]
            block_height = block["blockHeight"]
            actual_entry_count = block["actualEntryCount"]
            declared_entry_count = block["entryCount"]
            prev_block_ids = [value for value in block["prevBlockIds"] if value is not None]

            if block_height != expected_height:
                failures.append(
                    f"Account {account} block {block_id}: expected blockHeight "
                    f"{expected_height}, found {block_height}"
                )

            if declared_entry_count != actual_entry_count:
                failures.append(
                    f"Account {account} block {block_id}: entryCount={declared_entry_count} "
                    f"but contains {actual_entry_count} LedgerEntry nodes"
                )

            if expected_height == 0:
                if block["prevHash"] is not None:
                    failures.append(
                        f"Account {account} genesis block {block_id}: prevHash should be null"
                    )
                if prev_block_ids:
                    failures.append(
                        f"Account {account} genesis block {block_id}: unexpected PREVIOUS_BLOCK link"
                    )
            else:
                if block["prevHash"] != expected_prev_hash:
                    failures.append(
                        f"Account {account} block {block_id}: prevHash does not match prior blockHash"
                    )
                if prev_block_ids != [expected_prev_block_id]:
                    failures.append(
                        f"Account {account} block {block_id}: PREVIOUS_BLOCK should target "
                        f"{expected_prev_block_id}, found {prev_block_ids or 'none'}"
                    )

            expected_hash = _compute_block_hash(
                block_id,
                block["prevHash"],
                block["sourceHash"],
                block_height,
                declared_entry_count,
            )
            if block["blockHash"] != expected_hash:
                failures.append(
                    f"Account {account} block {block_id}: blockHash mismatch "
                    f"(stored={block['blockHash']}, expected={expected_hash})"
                )

            expected_prev_block_id = block_id
            expected_prev_hash = block["blockHash"]

        print(
            f"Account {account}: verified {len(blocks)} block(s), "
            f"{sum(block['actualEntryCount'] for block in blocks)} entry link(s)"
        )

    if failures:
        print("\nLedger verification failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"\nLedger verification passed for database '{database}'.")
    return 0


def main():
    args = parse_args()
    raise SystemExit(
        verify_ledger_chain(
            database=args.database,
            accounts=_parse_account_list(args.accounts),
        )
    )


if __name__ == "__main__":
    main()
