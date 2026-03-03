# JCTaxLedger

JCTaxLedger is a Jersey City property tax ETL and reporting project backed by Neo4j.

Current milestone release: `v0.5.0`

## Purpose

The purpose of JCTaxLedger is to extract Jersey City, New Jersey property tax billing and payment data for individual accounts, load that history into a Neo4j graph database, and make it easy for the account owner to track and manage the account over time.

The intended workflow is:

1. Pull billing and payment history for one or more Jersey City property tax accounts from the public HLS tax system.
2. Load that data into Neo4j as `Account`, `TaxBilling`, and `TaxPayment` nodes with graph relationships.
3. Let the account owner query the graph in natural language to:
   - track billing and payment activity
   - check current and historical balance
   - monitor year-over-year tax increases
   - create alerts or reminders for upcoming payments
   - investigate changes after a refresh
4. Use project skills so an agent can help the account owner perform ETL, reporting, ledger creation, and follow-up workflows consistently.

This repository currently contains these active pieces:

- A small ETL script that pulls Jersey City tax bill and payment history from the public HLS tax inquiry site and writes account metadata, billing nodes, and relationships into Neo4j.

## What the project does

The active application logic in this repository is the ETL flow in [`etl/jcTaxEtl.py`](/Users/weizhang/github/AccountManagerWithAI/etl/jcTaxEtl.py). It fetches structured JSON from the Jersey City HLS property tax inquiry endpoint, normalizes account metadata and tax history through [`etl/jcTaxJson2node.py`](/Users/weizhang/github/AccountManagerWithAI/etl/jcTaxJson2node.py), and refreshes `TaxBilling`, `TaxPayment`, `BILL_FOR`, and `PAYMENT_FOR` data in Neo4j for the `taxjc` database.

The project is designed so the account owner can then use an agent and the repo skills to work with that graph in higher-level ways, such as producing ledger reports, checking balances, analyzing tax increases, and preparing reminder-oriented workflows.

## Project layout

```text
.
├── neo4j_storage/                       # Neo4j write/read helper
└── etl/                                 # Jersey City tax scraping + graph load
```

## Prerequisites

- Python 3.10+ recommended
- A running Neo4j database populated with `Account` nodes
Install from a local checkout:

```bash
python -m pip install .
```

If you want dependency-only installation without packaging:

```bash
python -m pip install -r requirements.txt
```

## Configuration

Set these environment variables before running the ETL:

```bash
export Neo4jFinDBUrl="bolt://localhost:7687"
export Neo4jFinDBUserName="neo4j"
export Neo4jFinDBPassword="password"
export Neo4jFinDBName="taxjc"
```

## Loading Jersey City tax data into Neo4j

The ETL script expects `Account` nodes to already exist in Neo4j. It reads each `Account.Account` value, calls the new HLS property tax inquiry endpoint, updates account metadata, replaces that account's `TaxBilling` and `TaxPayment` history, and recreates the `BILL_FOR` and `PAYMENT_FOR` relationships.

Run it with:

```bash
jctaxledger-etl
```

from the repo checkout without installing:

```bash
bin/jctaxledger-etl.sh
```

or directly:

```bash
python etl/jcTaxEtl.py
```

Behavior to be aware of:

- The script now runs only when executed as the main module.
- It loads data from `https://apps.hlssystems.com/JerseyCity/PropertyTaxInquiry/GetAccountDetails`.
- The request is keyed by account number and includes an `interestThruDate` parameter.
- The ETL writes bill rows into `TaxBilling` and payment rows into `TaxPayment`.
- The ETL refreshes account metadata such as `accountId`, `address`, `ownerName`, `propertyLocation`, `principal`, `interest`, and `totalDue`.
- The split between `TaxBilling` and `TaxPayment` is classification-based, so the billing/payment rule in the ETL should be kept in sync with the HLS source semantics.
- The packaged CLI supports `--accounts` for comma-separated partial refreshes and `--database` to override the target database.

## Packaging

Build release artifacts locally with:

```bash
python -m build
```

This produces:

- `dist/jctaxledger-0.5.0.tar.gz`
- `dist/jctaxledger-0.5.0-py3-none-any.whl`

Release notes for this milestone are in [`RELEASE_NOTES_v0.5.0.md`](/Users/weizhang/github/AccountManagerWithAI/RELEASE_NOTES_v0.5.0.md).

## Skills

The repo includes local skills under [`/Users/weizhang/github/AccountManagerWithAI/skills`](/Users/weizhang/github/AccountManagerWithAI/skills):

- [`/Users/weizhang/github/AccountManagerWithAI/skills/taxjc-etl/SKILL.md`](/Users/weizhang/github/AccountManagerWithAI/skills/taxjc-etl/SKILL.md)
- [`/Users/weizhang/github/AccountManagerWithAI/skills/taxjc-reporting/SKILL.md`](/Users/weizhang/github/AccountManagerWithAI/skills/taxjc-reporting/SKILL.md)

These skills are meant to be used by an agent on behalf of the account owner.

- Use `taxjc-etl` when the owner wants to refresh or validate tax history in Neo4j.
- Use `taxjc-reporting` when the owner wants account-level summaries, balances, year-over-year comparisons, tax ledger reports, or other reporting built from `Account`, `TaxBilling`, and `TaxPayment`.

As the project grows, additional skills can cover reminders, alerts, owner-facing summaries, and recurring tax monitoring workflows.

Supporting query examples live in:

- [`/Users/weizhang/github/AccountManagerWithAI/skills/taxjc-reporting/references/report-queries.md`](/Users/weizhang/github/AccountManagerWithAI/skills/taxjc-reporting/references/report-queries.md)

## Tax Ledger Report

To create a tax ledger report with the reporting skill:

1. Refresh the data first if needed:

```bash
bin/jctaxledger-etl.sh
```

2. Use the reporting skill and ask for the report you want.

Example prompts:

```text
Use $taxjc-reporting to create a tax ledger report for account 123456 for 2025, showing total billed, total paid, net balance, and the underlying billing and payment rows.
```

```text
Use $taxjc-reporting to create a yearly tax ledger report for all accounts in taxjc, grouped by account and year, with billed, paid, balance, and year-over-year billing increase.
```

```text
Use $taxjc-reporting to create a property tax ledger report grouped by address for 2024 and 2025, and call out any balance differences after the latest ETL refresh.
```

Recommended report sections:

- account or address
- reporting period
- total billed
- total paid
- net balance
- year-over-year increase where applicable
- detailed billing rows
- detailed payment rows

## Current limitations

- There is no packaged environment definition yet (`requirements.txt`, `pyproject.toml`, or lockfile).
- There are no automated tests in the repository.
- The repository currently includes generated `__pycache__` content in the working tree.

## License

Apache License 2.0. See [`LICENSE`](/Users/weizhang/github/AccountManagerWithAI/LICENSE).
