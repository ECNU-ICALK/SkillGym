# Rolling Leaderboard Checklist

This workspace checklist is intentionally brief.

- Read the ranking and rolling-window rules from `analysis_contract.json`.
- Implement the leaderboard from reusable PostgreSQL relations so `query_pack.sql` can replay it.
- If the local PostgreSQL skill is present, use the airport rolling-mart reference there for the concrete SQL organization pattern.
