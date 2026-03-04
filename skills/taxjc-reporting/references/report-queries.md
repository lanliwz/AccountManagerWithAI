# TaxJC Reporting Queries

## Current graph
- `(:Account)`
- `(:TaxBilling)-[:BILL_FOR]->(:Account)`
- `(:TaxPayment)-[:PAYMENT_FOR]->(:Account)`
- `(:LedgerBlock)-[:LEDGER_FOR]->(:Account)`
- `(:LedgerBlock)-[:CONTAINS]->(:LedgerEntry)`
- `(:LedgerBlock)-[:PREVIOUS_BLOCK]->(:LedgerBlock)`
- `(:LedgerEntry)-[:FOR_ACCOUNT]->(:Account)`

## Total billed by year and account
```cypher
MATCH (b:TaxBilling)-[:BILL_FOR]->(a:Account)
RETURN a.Account AS account, a.address AS address, b.Year AS year,
       round(sum(coalesce(b.Billed, 0.0)) * 100) / 100.0 AS total_billed
ORDER BY account, year
```

## Total paid by year and account
```cypher
MATCH (p:TaxPayment)-[:PAYMENT_FOR]->(a:Account)
RETURN a.Account AS account, a.address AS address, p.Year AS year,
       round(sum(coalesce(p.Paid, 0.0)) * 100) / 100.0 AS total_paid
ORDER BY account, year
```

## Net balance by year and account
Use subqueries to avoid multiplying billing and payment rows.

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
RETURN a.Account AS account, a.address AS address,
       billed_2025, paid_2025,
       round((billed_2025 + paid_2025) * 100) / 100.0 AS balance_2025
ORDER BY account
```

## Year-over-year billing increase
```cypher
MATCH (b:TaxBilling)-[:BILL_FOR]->(a:Account)
WITH a.Account AS account, a.address AS address, toInteger(b.Year) AS year, sum(coalesce(b.Billed, 0.0)) AS total_billed
ORDER BY account, year
WITH account, address, collect({year: year, total_billed: round(total_billed * 100) / 100.0}) AS rows
UNWIND range(0, size(rows) - 1) AS i
WITH account, address, rows[i] AS curr, CASE WHEN i = 0 THEN null ELSE rows[i - 1] END AS prev
RETURN account, address, curr.year AS year, curr.total_billed AS total_billed,
       CASE WHEN prev IS NULL THEN null ELSE round((curr.total_billed - prev.total_billed) * 100) / 100.0 END AS increase_vs_prior_year,
       CASE WHEN prev IS NULL OR prev.total_billed = 0 THEN null ELSE round(((curr.total_billed - prev.total_billed) / prev.total_billed) * 10000) / 100.0 END AS pct_increase_vs_prior_year
ORDER BY account, year
```

## Account list with current address
```cypher
MATCH (a:Account)
RETURN a.Account AS account, a.accountId AS account_id, a.address AS address
ORDER BY account
```

## Consecutive ledger runs by account
Use this to inspect append-only run history and see whether the source snapshot changed between runs.

```cypher
MATCH (b:LedgerBlock)-[:LEDGER_FOR]->(a:Account)
OPTIONAL MATCH (b)-[:PREVIOUS_BLOCK]->(prev:LedgerBlock)
RETURN a.Account AS account,
       a.address AS address,
       b.blockHeight AS block_height,
       b.runId AS run_id,
       b.createdAt AS loaded_at,
       b.blockId AS block_id,
       b.sourceHash AS source_hash,
       prev.blockId AS previous_block_id,
       prev.sourceHash AS previous_source_hash,
       CASE
         WHEN prev IS NULL THEN null
         WHEN b.sourceHash = prev.sourceHash THEN false
         ELSE true
       END AS source_changed_vs_previous_run
ORDER BY account, block_height
```

## Latest ledger change status by account
Use this to answer "did the latest ETL run change anything for this account?"

```cypher
MATCH (b:LedgerBlock)-[:LEDGER_FOR]->(a:Account)
WITH a, b
ORDER BY a.Account, b.blockHeight DESC
WITH a, collect(b)[0] AS latest
OPTIONAL MATCH (latest)-[:PREVIOUS_BLOCK]->(prev:LedgerBlock)
RETURN a.Account AS account,
       a.address AS address,
       latest.runId AS latest_run_id,
       latest.createdAt AS latest_loaded_at,
       latest.blockHeight AS latest_block_height,
       latest.sourceHash AS latest_source_hash,
       prev.runId AS previous_run_id,
       prev.createdAt AS previous_loaded_at,
       prev.sourceHash AS previous_source_hash,
       CASE
         WHEN prev IS NULL THEN null
         WHEN latest.sourceHash = prev.sourceHash THEN 'UNCHANGED'
         ELSE 'CHANGED'
       END AS latest_change_status
ORDER BY account
```
