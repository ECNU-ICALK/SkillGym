---
name: billing-automation
description: Pull the current renewal cohort from the local revops service, expand each account into detail, renewal preview, and dunning facts, then classify one operational action per account before writing the final worklist and summary.
---

# Billing Automation

Use this skill when a task asks you to build or repair a billing, renewals, or revenue-operations action queue from local business-system data.

## What This Skill Is Good For

- Detecting when older CRM or invoice exports are incomplete.
- Pulling every page of a local renewal cohort before making decisions.
- Expanding each account into detail, renewal preview, and dunning history.
- Recomputing one deterministic action bucket per account from policy thresholds and current blockers.
- Writing a CSV worklist, a JSON control summary, and a short operator brief from the same decision set.

## Recommended Workflow

1. Read `/root/data/ops_manifest.json`, `/root/data/action_policy.yaml`, and `/root/data/contact_directory.csv`.
2. Query the revops manifest endpoint first and treat the local service URLs as authoritative.
3. Fetch the renewal cohort with cursor pagination until `has_next_page` is false.
4. For every account in the cohort, fetch:
   - `/api/accounts/<account_id>`
   - `/api/accounts/<account_id>/renewal-preview`
   - `/api/accounts/<account_id>/dunning-events`
5. Classify accounts with this priority order:
   - `pause_renewal` for legal hold;
   - `update_expansion_quote` for current quote-required expansion;
   - `escalate_csm` for procurement blockers;
   - `collect_payment` for overdue open invoices that cross the policy thresholds;
   - `send_invoice` for draft invoices without autopay;
   - `monitor` otherwise.
6. Build the CSV, JSON, and Markdown outputs from the same row set so counts and ARR totals stay aligned.

## Helper Scripts

- `python3 /root/.codex/skills/billing-automation/scripts/fetch_cohort.py`
  - Fetches every cohort page from the local service.
- `python3 /root/.codex/skills/billing-automation/scripts/inspect_account.py ACC-101`
  - Prints current detail, renewal preview, and dunning payloads for one account.
- `python3 /root/.codex/skills/billing-automation/scripts/build_worklist.py`
  - Recomputes a generic candidate worklist from the live service and local policy file.

## Notes

- The older exports are context only.
- Missing later pages changes the answer.
- Do not assign multiple action buckets to one account.
