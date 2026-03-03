# TaxJC Reporting Queries

## Current graph
- `(:Account)`
- `(:TaxBilling)-[:BILL_FOR]->(:Account)`
- `(:TaxPayment)-[:PAYMENT_FOR]->(:Account)`

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
