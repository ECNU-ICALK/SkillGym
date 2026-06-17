name: leiloeiro-edital
description: Build a committee-ready audit pack for a foreclosure auction asset by draining the local authority service, reconciling stale exports, recomputing transfer cash, and writing a compact bid recommendation.
---

# Leiloeiro Edital

Use this skill when a task asks for a foreclosure-auction or edital review package with structured facts, a risk register, buyer cash requirements, and a bid recommendation. It is especially useful when stale internal exports exist and a local authority service exposes the current policy or risk data.

## Recommended workflow

1. Read `/root/data/job_manifest.json` first and treat the listed local service URLs as the current authority.
2. Query the manifest endpoint before anything else so you discover the service shape and pagination rules.
3. Pull the current asset facts and current cost model from the service; do not rebuild those fields from stale exports.
4. Drain paginated risk endpoints until `next_cursor` is `null`. Do not stop after the first page.
5. Use stale files only as background context or discrepancy checks. They are not the final source for bid values, payment flags, or risk coverage.
6. Keep the output files internally consistent:
   - `notice_extract.json` should mirror the authority asset record.
   - `risk_register.csv` should cover the full live risk set with the given evidence sources.
   - `cash_requirements.json` should mirror the current cost model and preserve 2 decimals.
   - the memo should cite the same facts, risks, and amounts.
7. Derive the final recommendation from the current decision policy, total modeled cash out, and the number of high-severity risks.

## Helper script

- `scripts/build_audit_package.py`: reads the task manifest, drains the local authority service including cursor pagination, and writes all four required outputs. Review the generated files before final submission.

The helper is intended to reduce diagnosis time and to keep pagination, totals, and recommendation logic aligned with the task rules. You are still responsible for checking the final files.
