# JCTaxLedger v1.0.0

## Milestone

This release marks the first stable `1.0.0` milestone for JCTaxLedger.

## Highlights

- Finalized the blockchain-style append-only ledger architecture with:
  - `LedgerBlock`
  - `LedgerEntry`
  - run-based chaining (`runId`, `blockHeight`, `prevHash`, `blockHash`)
- Kept compatibility reporting projections in `TaxBilling` and `TaxPayment`.
- Added operational ledger tooling:
  - `jctaxledger-verify-ledger`
  - `jctaxledger-diff-ledger`
- Updated docs and skills to standardize architecture/workflow updates and public-doc placeholder policy.

## Install

From a local checkout:

```bash
python -m pip install .
```

From built artifacts:

```bash
python -m pip install dist/jctaxledger-1.0.0-py3-none-any.whl
```

## CLI

Refresh all accounts from `taxjc`:

```bash
jctaxledger-etl
```

Verify ledger integrity:

```bash
jctaxledger-verify-ledger --database taxjc
```

Diff ledger snapshots:

```bash
jctaxledger-diff-ledger --database taxjc
```

Refresh specific accounts (placeholder examples):

```bash
jctaxledger-etl --accounts 123456,234567
```

## Environment

Set before running ETL or ledger tooling:

```bash
export Neo4jFinDBUrl="bolt://localhost:7687"
export Neo4jFinDBUserName="neo4j"
export Neo4jFinDBPassword="password"
export Neo4jFinDBName="taxjc"
```
