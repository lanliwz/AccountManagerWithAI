# JCTaxLedger v0.5.0

## Milestone

This release establishes the first packaged milestone for JCTaxLedger.

## Highlights

- Rebranded the project to `JCTaxLedger`.
- Replaced the old unified tax history model with split `TaxBilling` and `TaxPayment` nodes.
- Added ETL refresh support for the Jersey City HLS `PropertyTaxInquiry` JSON source.
- Added an ETL CLI with:
  - default full refresh from `taxjc`
  - `--database` override
  - `--accounts` for comma-separated partial refreshes
- Added Python packaging metadata and a console script:
  - `jctaxledger-etl`

## Install

From a local checkout:

```bash
python -m pip install .
```

## CLI

Refresh all accounts from `taxjc`:

```bash
jctaxledger-etl
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

Set before running ETL:

```bash
export Neo4jFinDBUrl="bolt://localhost:7687"
export Neo4jFinDBUserName="neo4j"
export Neo4jFinDBPassword="password"
export Neo4jFinDBName="taxjc"
```
