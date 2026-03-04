# JCTaxLedger v0.7.0

## Milestone

This release establishes the blockchain-style ledger architecture for JCTaxLedger.

## Highlights

- Added append-only `LedgerBlock` and `LedgerEntry` history in Neo4j.
- Switched ledger identity from snapshot-only deduplication to run-based chaining.
- Added `runId`, `sourceHash`, `blockHash`, `prevHash`, and `blockHeight` to support ledger verification and run-to-run change detection.
- Added a ledger verification CLI:
  - `jctaxledger-verify-ledger`
  - `bin/jctaxledger-verify-ledger.sh`
- Added ledger comparison queries to the reporting references.
- Updated repo skills to reflect the active ledger model and the required documentation workflow.
- Updated `README.md` and `README4ETL.md` to make the blockchain-style ledger the primary architecture.

## Install

From a local checkout:

```bash
python -m pip install .
```

From built artifacts:

```bash
python -m pip install dist/jctaxledger-0.7.0-py3-none-any.whl
```

## CLI

Refresh all accounts from `taxjc`:

```bash
jctaxledger-etl
```

From the repo checkout without installation:

```bash
bin/jctaxledger-etl.sh
```

Verify ledger integrity:

```bash
jctaxledger-verify-ledger --database taxjc
```

From the repo checkout without installation:

```bash
bin/jctaxledger-verify-ledger.sh --database taxjc
```

Refresh specific accounts:

```bash
jctaxledger-etl --accounts 123456,234567
```

Use a different database:

```bash
jctaxledger-etl --database taxjc
```

## Environment

Set before running ETL or ledger verification:

```bash
export Neo4jFinDBUrl="bolt://localhost:7687"
export Neo4jFinDBUserName="neo4j"
export Neo4jFinDBPassword="password"
export Neo4jFinDBName="taxjc"
```
