# TaxJC ETL Runbook

## Files
- `/Users/weizhang/github/AccountManagerWithAI/etl/jcTaxEtl.py`
- `/Users/weizhang/github/AccountManagerWithAI/etl/jcTaxJson2node.py`
- `/Users/weizhang/github/AccountManagerWithAI/neo4j_storage/dataService.py`

## Source
Current landing page:
- `https://apps.hlssystems.com/JerseyCity/PropertyTaxInquiry`

Current detail endpoint:
- `https://apps.hlssystems.com/JerseyCity/PropertyTaxInquiry/GetAccountDetails`

Current request parameters:
- `accountNumber`
- `interestThruDate`

## Current mapping
- `Account` nodes are refreshed from `accountInquiryVM`.
- `TaxBilling` holds billing-like rows.
- `TaxPayment` holds payment-like rows.
- `(:TaxBilling)-[:BILL_FOR]->(:Account)`
- `(:TaxPayment)-[:PAYMENT_FOR]->(:Account)`

## Safe run commands
From repo root:

```bash
bin/jctaxledger-etl.sh
```

Partial refresh:

```bash
bin/jctaxledger-etl.sh --accounts 123456,234567
```

Direct Python equivalent:

```bash
Neo4jFinDBName=taxjc PYTHONPATH=/Users/weizhang/github/AccountManagerWithAI /opt/anaconda3/bin/python3 /Users/weizhang/github/AccountManagerWithAI/etl/jcTaxEtl.py
```

## Basic compile check
```bash
/opt/anaconda3/bin/python3 -m py_compile /Users/weizhang/github/AccountManagerWithAI/etl/jcTaxEtl.py
/opt/anaconda3/bin/python3 -m py_compile /Users/weizhang/github/AccountManagerWithAI/etl/jcTaxJson2node.py
/opt/anaconda3/bin/python3 -m py_compile /Users/weizhang/github/AccountManagerWithAI/neo4j_storage/dataService.py
```

## Verification queries
Node counts:
```cypher
MATCH (n) RETURN labels(n) AS labels, count(*) AS count ORDER BY count DESC
```

Relationship counts:
```cypher
MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC
```

Per-account counts:
```cypher
MATCH (a:Account)
OPTIONAL MATCH (b:TaxBilling)-[:BILL_FOR]->(a)
OPTIONAL MATCH (p:TaxPayment)-[:PAYMENT_FOR]->(a)
RETURN a.Account AS account, count(DISTINCT b) AS billing_rows, count(DISTINCT p) AS payment_rows
ORDER BY account
```

2025 totals:
```cypher
MATCH (a:Account)
CALL {
  WITH a
  MATCH (b:TaxBilling)-[:BILL_FOR]->(a)
  WHERE b.Year = '2025'
  RETURN round(sum(coalesce(b.Billed, 0.0)) * 100) / 100.0 AS billed_2025
}
CALL {
  WITH a
  MATCH (p:TaxPayment)-[:PAYMENT_FOR]->(a)
  WHERE p.Year = '2025'
  RETURN round(sum(coalesce(p.Paid, 0.0)) * 100) / 100.0 AS paid_2025
}
RETURN a.Account AS account, billed_2025, paid_2025, round((billed_2025 + paid_2025) * 100) / 100.0 AS balance_2025
ORDER BY account
```

## Cleanup rule
When asked to clean `taxjc`, keep only:
- `Account`
- `TaxBilling`
- `TaxPayment`
- `BILL_FOR`
- `PAYMENT_FOR`
