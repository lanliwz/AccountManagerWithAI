# JCTaxLedger v0.6.0

## Milestone

This release packages the project around the current tax-ledger workflow and repo-local agent skills.

## Highlights

- Rebranded the project docs around the `JCTaxLedger` name and purpose.
- Added a repo wrapper script:
  - `bin/jctaxledger-etl.sh`
- Added a proper ETL CLI with:
  - default full refresh from `taxjc`
  - `--database` override
  - `--accounts` for comma-separated partial refreshes
- Added repo-local skills under `skills/`:
  - `taxjc-etl`
  - `taxjc-reporting`
- Updated the README to explain the owner workflow, tax ledger reporting, and skill usage.
- Removed the unused PyQt6 SVG viewer from the package and docs.

## Install

From a local checkout:

```bash
python -m pip install .
```

From built artifacts:

```bash
python -m pip install dist/jctaxledger-0.6.0-py3-none-any.whl
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
