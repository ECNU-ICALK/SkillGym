You need to prepare an action worklist for the Revenue Operations team to use in the next renewal and collections meeting. The container includes older exports of CRM and invoice snapshots, but they may be incomplete or stale; for this delivery, the in-container revops service referenced by `ops_manifest.json` is the source of truth.

Input data is under `/root/data/`:

- `ops_manifest.json`: workspace id, cohort date, delivery requirements, and the local revops service URL.
- `crm_export.csv`: an older export of the renewal cohort and CRM fields; may be incomplete.
- `invoice_snapshot.ndjson`: an older export of invoice and dunning status; may no longer reflect the current state.
- `action_policy.yaml`: action routing rules and thresholds for this renewal workbench.
- `contact_directory.csv`: account owners, regions, and escalation contacts.

## Your Task

1. Review all accounts in the current cohort and determine the appropriate renewal action routing for each account.
2. Using the current account facts provided by the revops service, decide which accounts require sending an invoice, collecting payment, escalating to the account owner, updating an expansion quote, or pausing renewal.
3. Produce a structured worklist that the Revenue Operations team can use directly, a summary JSON, and a short business brief.

## Business Constraints

1. Every account in the cohort must appear in the final worklist; none may be omitted.
2. `crm_export.csv` and `invoice_snapshot.ndjson` are background references only and must not replace the current revops service.
3. Renewal actions must be decided based on facts returned by the current service and the rules in `action_policy.yaml`.
4. If an account requires action, you must provide a single `action_bucket` and a single `action_reason`.
5. You must not evade constraints by removing accounts, removing fields, deleting output files, stopping the service, or changing the environment.

## Output

If `/root/output/` does not exist, create it first.

1. Write `/root/output/renewal_worklist.csv`

The column names must be exactly:

```csv
account_id,company_name,crm_deal_id,owner_name,renewal_date,renewal_arr_usd,invoice_status,dunning_stage,seat_delta,action_bucket,action_reason,next_step
```

Requirements:

- Must cover all accounts in the current cohort, and each `account_id` may appear only once.
- `renewal_date` uses `YYYY-MM-DD`.
- `renewal_arr_usd` must be the current renewal amount.
- `seat_delta` must be the seat change value from the current preview.
- `action_bucket` must be one of the following:
  - `send_invoice`
  - `collect_payment`
  - `escalate_csm`
  - `update_expansion_quote`
  - `pause_renewal`
  - `monitor`
- `action_reason` must be one of the following:
  - `draft_invoice_ready`
  - `overdue_payment_attempts`
  - `missing_purchase_order`
  - `expansion_quote_required`
  - `legal_hold`
  - `healthy_autopay`
- `next_step` must be a short, actionable instruction.

2. Write `/root/output/renewal_control_summary.json`

The top-level structure must be exactly:

```json
{
  "workspace_id": "revops-000",
  "cohort_date": "YYYY-MM-DD",
  "totals": {
    "accounts_reviewed": 0,
    "renewal_arr_reviewed_usd": 0.0,
    "accounts_needing_action": 0,
    "revenue_at_risk_usd": 0.0
  },
  "action_counts": {
    "send_invoice": 0,
    "collect_payment": 0,
    "escalate_csm": 0,
    "update_expansion_quote": 0,
    "pause_renewal": 0,
    "monitor": 0
  },
  "workflow_blocked_account_ids": ["ACC-000"],
  "service_checks": {
    "revops_manifest": true,
    "accounts": true,
    "account_details": true,
    "renewal_previews": true,
    "dunning_events": true
  },
  "notes": [
    "Example note"
  ]
}
```

Requirements:

- `workspace_id` and `cohort_date` must match the task input.
- `accounts_reviewed` must equal the number of accounts in the current cohort.
- `renewal_arr_reviewed_usd` must equal the sum of the current `renewal_arr_usd` across all accounts.
- `accounts_needing_action` must equal the number of accounts with `action_bucket != monitor`.
- `revenue_at_risk_usd` must equal the sum of `renewal_arr_usd` for accounts with `action_bucket != monitor`.
- `workflow_blocked_account_ids` must include only accounts currently blocked from progressing the renewal workflow due to procurement blockers or legal holds, sorted by `account_id` ascending.
- All 5 fields in `service_checks` must be `true`.
- `notes` must contain at least 2 brief business-summary notes.

3. Write `/root/output/ops_brief.md`

The content must include:

- the workspace id;
- the cohort date;
- the total number of current accounts;
- the number of accounts needing action;
- the current workflow-blocked account IDs;
- the highest-amount expansion quote account;
- the most urgent collections account;
- a brief explanation of the action routing logic used.

## Notes

- Do not modify any input files under `/root/data/`.
- Do not treat the older exported CSV or NDJSON as the only source of truth, and do not bypass the in-container revops service.
- Do not replace the real chain with hard-coded results, cached answers, or manually assembled placeholder outputs.
- Do not modify tests, verifier, task metadata, environment files, or anything under any `skills` directory.
- You may write helper scripts in the working directory, but the only required deliverables are the 3 files under `/root/output/`.
