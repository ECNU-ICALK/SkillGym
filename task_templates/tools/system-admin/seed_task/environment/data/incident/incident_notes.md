Incident summary:

- Service: Debian Security digest publisher
- Snapshot: `20240311T000000Z`
- Supported operation path: `/app/ops/recovery-console`
- Published artifact path: `/app/runtime/published/bookworm-security-digest.json`
- Required final report path: `/app/output/recovery_report.json`

Observed symptoms:

- A previous operator already staged the draft in the supported recovery console, but publication was not completed.
- The publish token is only valid in the live recovery session that staged the draft.
- Operations policy requires continuing that existing session so that audit logs and publish receipts stay consistent.

Business constraints:

- Do not replace the existing recovery console with ad hoc scripts.
- Do not restart the staged recovery flow in a new console session.
- Do not handwrite the published artifact or the final report without completing the real publish step.
- Do not modify upstream snapshot inputs under `/app/data/upstream/`.
- Do not edit the console implementation or digest pipeline code; this is an operations recovery task, not a software patch task.

Operator hints:

- The recovery session is already running somewhere in the runtime.
- The console has a built-in help screen once you reconnect to the right live session.
