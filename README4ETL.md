# JCTaxLedger ETL README

This document describes the current Jersey City tax ETL implemented in this repository.

## Scope

The ETL code lives in:

- [`etl/jcTaxEtl.py`](etl/jcTaxEtl.py)
- [`etl/jcTaxJson2node.py`](etl/jcTaxJson2node.py)
- [`neo4j_storage/dataService.py`](neo4j_storage/dataService.py)

Its job is to fetch property tax account details from the Jersey City HLS site, normalize bill and payment history into graph properties, update `Account` metadata, and refresh `TaxBilling` and `TaxPayment` rows in Neo4j.

## Source System

The ETL no longer scrapes the old HTML table site.

It now uses:

- landing page:
  - [https://apps.hlssystems.com/JerseyCity/PropertyTaxInquiry](https://apps.hlssystems.com/JerseyCity/PropertyTaxInquiry)
- data endpoint:
  - [https://apps.hlssystems.com/JerseyCity/PropertyTaxInquiry/GetAccountDetails](https://apps.hlssystems.com/JerseyCity/PropertyTaxInquiry/GetAccountDetails)

The endpoint is called with:

- `accountNumber`
- `interestThruDate`

Example request shape:

```text
GET /JerseyCity/PropertyTaxInquiry/GetAccountDetails?accountNumber=123456&interestThruDate=Tue%20Mar%2003%202026
```

The response contains:

- `accountInquiryVM`
- `notesVM`
- `validAccountNumber`
- `genericTextVM`

The ETL uses `accountInquiryVM`, especially:

- account-level metadata such as `AccountId`, `AccountNumber`, `Address`, `OwnerName`, `PropertyLocation`, `Principal`, `Interest`, `TotalDue`
- `Details`, which contains bill and payment history rows

## End-to-End Flow

The ETL executes this sequence:

1. Open a Neo4j connection using `Neo4jFinDB*` environment variables.
2. Read all account numbers with:

```cypher
MATCH (n:Account) RETURN n.Account as account_num
```

3. For each account number, call the HLS detail endpoint.
4. Normalize account metadata into a single `Account` property map.
5. Normalize each source detail row into a tax history property map.
6. Upsert the `Account` node.
7. Delete that account's existing tax history nodes.
8. Insert refreshed `TaxBilling` and `TaxPayment` rows.
9. Recreate `(:TaxBilling)-[:BILL_FOR]->(:Account)` and `(:TaxPayment)-[:PAYMENT_FOR]->(:Account)` relationships.

The ETL refreshes history per account, not as an append-only load.

## How the Code Is Structured

### `etl/jcTaxEtl.py`

Main responsibilities:

- build the `interestThruDate` request parameter
- fetch `accountInquiryVM` JSON for each account number
- normalize data through helper functions
- refresh Neo4j for each account

Current source endpoint constant:

```python
PROPERTY_TAX_INQUIRY_URL = "https://apps.hlssystems.com/JerseyCity/PropertyTaxInquiry/GetAccountDetails"
```

Important behavior:

- the module runs only under `if __name__ == "__main__":`
- it exposes a CLI
- default CLI behavior refreshes all `Account` nodes from the `taxjc` database
- `--accounts` accepts a comma-separated list for partial refreshes
- `--database` overrides the target Neo4j database

### `etl/jcTaxJson2node.py`

Main responsibilities:

- normalize account-level source fields
- build a normalized `taxAccountId`
- normalize source detail rows into graph property maps

Account properties currently written include:

- `Account`
- `accountId`
- `taxAccountId`
- `address`
- `ownerName`
- `propertyLocation`
- `block`
- `lot`
- `qualifier`
- `bankName`
- `principal`
- `interest`
- `totalDue`
- `updatedFromSource`

Tax row properties currently written include:

- `sourceId`
- `Account`
- `AccountId`
- `Year`
- `Qtr`
- `DueDate`
- `TransactionDate`
- `Description`
- `Type`
- `Billed`
- `Paid`
- `Adjusted`
- `OpenBalance`
- `InterestDue`
- `Days`
- `BillSequence`
- `TransactionId`
- `TransCode`
- `DepositNumber`
- `SortCode`
- `PaymentSourceDescription`
- `CheckNumber`
- `CreatedBy`
- `PaidBy` when present

### `neo4j_storage/dataService.py`

Main responsibilities:

- manage the Neo4j driver
- read account numbers
- upsert `Account` metadata
- replace tax history for one account at a time

The refresh is split into separate writes:

1. upsert `Account`
2. delete existing tax history rows for that account
3. insert refreshed `TaxBilling` and `TaxPayment` rows with their relationships

## Current Graph Model

The ETL writes this shape:

```text
(:Account {
  Account,
  accountId,
  taxAccountId,
  address,
  ownerName,
  propertyLocation,
  principal,
  interest,
  totalDue,
  ...
})

(:TaxBilling {
  Account,
  AccountId,
  Year,
  Qtr,
  DueDate,
  TransactionDate,
  Description,
  Type,
  Billed,
  Paid,
  Adjusted,
  OpenBalance,
  InterestDue,
  ...
})

(:TaxPayment {
  Account,
  AccountId,
  Year,
  Qtr,
  DueDate,
  TransactionDate,
  Description,
  Type,
  Billed,
  Paid,
  Adjusted,
  OpenBalance,
  InterestDue,
  ...
})

(:TaxBilling)-[:BILL_FOR]->(:Account)
(:TaxPayment)-[:PAYMENT_FOR]->(:Account)
```

Join key:

- `Account.Account = TaxBilling.Account`
- `Account.Account = TaxPayment.Account`

## Important Constraint Behavior

The old `JerseyCityTaxBilling` constraint and related stale indexes were removed from `taxjc` after the model was split into `TaxBilling` and `TaxPayment`.

## Runtime Prerequisites

The ETL assumes all of the following are true:

- Neo4j is running and reachable
- `Account` nodes already exist
- each `Account` node has an `Account` property with the Jersey City account number
- the HLS site is reachable

Required environment variables:

```bash
export Neo4jFinDBUrl="bolt://localhost:7687"
export Neo4jFinDBUserName="neo4j"
export Neo4jFinDBPassword="your-password"
export Neo4jFinDBName="taxjc"
```

Python packages used by ETL:

```bash
pip install neo4j requests
```

## How To Run

From the repository root:

```bash
python etl/jcTaxEtl.py
```

Or use the repo wrapper script:

```bash
bin/jctaxledger-etl.sh
```

This default command:

- targets Neo4j database `taxjc`
- queries `Account` nodes from that database
- refreshes billing and payment history for every returned account

To refresh only selected accounts:

```bash
python etl/jcTaxEtl.py --accounts 123456,234567
```

Wrapper equivalent:

```bash
bin/jctaxledger-etl.sh --accounts 123456,234567
```

To override the database explicitly:

```bash
python etl/jcTaxEtl.py --database taxjc
```

Wrapper equivalent:

```bash
bin/jctaxledger-etl.sh --database taxjc
```

If your interpreter does not resolve local imports from the repo root, run with explicit `PYTHONPATH`:

```bash
PYTHONPATH=. python etl/jcTaxEtl.py
```

To force the target database:

```bash
Neo4jFinDBName=taxjc PYTHONPATH=. python etl/jcTaxEtl.py
```

To combine both:

```bash
PYTHONPATH=. python etl/jcTaxEtl.py --database taxjc --accounts 123456,234567
```

## Inputs and Outputs

Input from Neo4j:

- existing `Account` nodes
- specifically the `Account` property returned by `MATCH (n:Account)`

Input from the remote site:

- one JSON response per account from `GetAccountDetails`

Output written to Neo4j:

- refreshed `Account` metadata
- refreshed `TaxBilling` rows for each account
- refreshed `TaxPayment` rows for each account
- refreshed `BILL_FOR` and `PAYMENT_FOR` relationships

## Idempotency Characteristics

The ETL is mostly refresh-oriented.

What is stable across reruns:

- rerunning the ETL for the same source state should converge on the same account metadata and billing rows
- old billing rows for an account are deleted before the refreshed rows are inserted

What is not fully lossless:

- the billing/payment split is classification-based and depends on current HLS row semantics

## Operational Risks

These are the main ETL risks in the current implementation:

- the ETL depends on an external site with no retry or backoff policy yet
- it refreshes one account at a time and does not checkpoint progress
- if the HLS response shape changes, normalization code will need to be updated
- if HLS changes the meaning of row descriptions or `Type`, the billing/payment split rule may need to be updated

## Verified Current Load Shape

After the live refresh into `taxjc`, the current observed data shape is:

- graph total: `340` `TaxBilling` nodes and `404` `TaxPayment` nodes
- year coverage: `2005` through `2026`

For command examples in this document, account numbers such as `123456` and `234567` are fake placeholders.

## Recommended Next Improvements

If this ETL is going to be used repeatedly, these changes should come first:

1. Add retries, logging, and partial-failure reporting around the HLS requests.
2. Add tests for source normalization using captured endpoint payloads.
3. Make the billing/payment classification rule explicit in tests so future source changes are caught quickly.
