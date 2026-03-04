---
name: taxjc-etl
description: Use when refreshing, rewriting, or validating the Jersey City tax ETL for the `taxjc` Neo4j database, especially for the HLS PropertyTaxInquiry source, account metadata updates, `TaxBilling`/`TaxPayment` loads, or tax graph cleanup.
---

# TaxJC ETL

## When to use
- Refresh `taxjc` from the Jersey City HLS tax source.
- Change how tax source rows map into Neo4j.
- Validate or repair `TaxBilling`, `TaxPayment`, `BILL_FOR`, or `PAYMENT_FOR` data.
- Clean stale labels, relationships, constraints, or indexes from `taxjc` after ETL changes.

## Workflow
1. Confirm the target database and current model before making changes.
   - Expected target is usually `taxjc`.
   - Current tax model is `(:Account)`, `(:TaxBilling)`, `(:TaxPayment)`, `[:BILL_FOR]`, and `[:PAYMENT_FOR]`.
2. Inspect the live source contract before changing parsing logic.
   - The current source is the HLS endpoint described in `references/etl-runbook.md`.
   - Prefer checking the actual response shape with a real account over assuming fields are stable.
3. Read only the files you need:
   - `etl/jcTaxEtl.py`
   - `etl/jcTaxJson2node.py`
   - `neo4j_storage/dataService.py`
4. Make ETL changes with these constraints:
   - Keep loads idempotent at the account-refresh level.
   - Upsert `Account` metadata first, then replace per-account tax history.
   - Keep `TaxBilling` and `TaxPayment` classification explicit and easy to audit.
   - When cleaning schema objects, verify the label is no longer in use first.
5. Validate locally before the live run.
   - Run `python -m py_compile` on touched Python files.
6. Run the ETL against `taxjc` explicitly.
   - Prefer overriding `Neo4jFinDBName=taxjc` for safety.
7. Verify the graph after load.
   - Check node counts, relationship counts, year coverage, and 1-2 account totals.

## Guardrails
- Do not assume the shell environment is pointing at `taxjc`; verify or override it.
- Treat external HLS responses as unstable. Recheck the response shape when the ETL breaks.
- If a user asks to clean the database, remove only objects unrelated to the active tax model.
- If constraints or indexes mention labels that are no longer present, verify they are stale before dropping them.

## References
- Read `references/etl-runbook.md` for concrete commands, source endpoints, and verification queries.
