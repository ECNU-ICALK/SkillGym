# Batch Harmonization Reference

This workspace note is intentionally high level.

- Inspect the raw batch headers directly and normalize them into one reusable PostgreSQL fact relation.
- Treat `analysis_contract.json` as the authority for candidate-market scope, rolling windows, and ranking behavior.
- If the local PostgreSQL skill is available, use its airport rolling-mart references for the task-specific mapping and SQL organization details.
