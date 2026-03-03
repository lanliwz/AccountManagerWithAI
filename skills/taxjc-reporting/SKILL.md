---
name: taxjc-reporting
description: Use when answering reporting questions over the `taxjc` Neo4j database, especially totals, balances, yearly increases, account-level billing/payment summaries, or comparisons built from `Account`, `TaxBilling`, and `TaxPayment`.
---

# TaxJC Reporting

## When to use
- Answer questions about tax billed, tax paid, or net balance in `taxjc`.
- Group tax results by account, address, year, quarter, or description.
- Compute year-over-year tax changes.
- Explain why current totals changed after an ETL refresh.

## Workflow
1. Confirm the active graph model before querying.
   - Current reporting model is `Account`, `TaxBilling`, and `TaxPayment`.
   - Billing flows through `BILL_FOR`; payments flow through `PAYMENT_FOR`.
2. Use the split model directly.
   - Do not assume the old `JerseyCityTaxBilling` label still exists.
3. Match the aggregation to the question:
   - billing-only questions: query `TaxBilling`
   - payment-only questions: query `TaxPayment`
   - balance questions: sum billing and payments separately, then combine
4. Be careful with joins.
   - For combined billing/payment answers, prefer subqueries or separate aggregations per account/year to avoid row multiplication.
5. Call out partial-year data when relevant.
   - 2026 currently looks partial in the source feed.
6. Round currency values to cents in the returned result.

## Guardrails
- If a result changed after ETL, mention that the source now includes detailed bill and payment history rather than the old summarized model.
- If an address differs from prior answers, prefer the current `Account.address` value in `taxjc` and mention that it came from the latest source refresh.
- If a query needs examples, read `references/report-queries.md`.

## References
- Read `references/report-queries.md` for common query patterns used in this repo.
