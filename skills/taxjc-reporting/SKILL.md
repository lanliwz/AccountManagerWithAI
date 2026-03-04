---
name: taxjc-reporting
description: Use when answering reporting questions over the `taxjc` Neo4j database, especially totals, balances, yearly increases, account-level billing/payment summaries, or ledger run comparisons built from `Account`, `TaxBilling`, `TaxPayment`, `LedgerBlock`, and `LedgerEntry`.
---

# TaxJC Reporting

## When to use
- Answer questions about tax billed, tax paid, or net balance in `taxjc`.
- Group tax results by account, address, year, quarter, or description.
- Compute year-over-year tax changes.
- Explain why current totals changed after an ETL refresh.
- Compare consecutive ledger runs and determine whether the source snapshot changed.

## Workflow
1. Confirm the active graph model before querying.
   - Current reporting model includes `Account`, `TaxBilling`, `TaxPayment`, `LedgerBlock`, and `LedgerEntry`.
   - Billing flows through `BILL_FOR`; payments flow through `PAYMENT_FOR`.
   - Ledger history flows through `LEDGER_FOR`, `CONTAINS`, `PREVIOUS_BLOCK`, and `FOR_ACCOUNT`.
2. Use the split model directly.
   - Do not assume the old `JerseyCityTaxBilling` label still exists.
   - For financial totals, prefer `TaxBilling` and `TaxPayment` unless the user specifically asks for ledger-native reporting.
   - For ETL run history, source change detection, or chain inspection, query `LedgerBlock`.
3. Match the aggregation to the question:
   - billing-only questions: query `TaxBilling`
   - payment-only questions: query `TaxPayment`
   - balance questions: sum billing and payments separately, then combine
   - run-vs-run comparison questions: compare each `LedgerBlock.sourceHash` to the previous block for the same account
4. Be careful with joins.
   - For combined billing/payment answers, prefer subqueries or separate aggregations per account/year to avoid row multiplication.
   - For ledger answers, anchor on one block per account/height before expanding to entries.
5. Call out partial-year data when relevant.
   - 2026 currently looks partial in the source feed.
6. Round currency values to cents in the returned result.
7. If the reporting model or architecture description changes materially, update `README.md` and any relevant reference docs in the same change.

## Guardrails
- If a result changed after ETL, mention that the source now includes detailed bill and payment history rather than the old summarized model.
- If an address differs from prior answers, prefer the current `Account.address` value in `taxjc` and mention that it came from the latest source refresh.
- If a query needs examples, read `references/report-queries.md`.
- Be explicit when a ledger answer is about ETL runs rather than tax economics. A new block can be appended even when `sourceHash` is unchanged.
- Do not introduce a new reporting model or ledger interpretation without updating the top-level docs that describe it.

## References
- Read `references/report-queries.md` for common query patterns used in this repo.
