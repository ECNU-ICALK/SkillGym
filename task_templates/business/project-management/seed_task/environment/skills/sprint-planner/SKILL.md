---
name: sprint-planner
description: Pull a paginated live backlog, fetch detail facts for every item, and compute a sprint commitment that respects must-ship order, dependencies, story-point headroom, QA capacity, and review bandwidth.
---

# Sprint Planner

Use this skill when a task asks for sprint planning, backlog commitment, capacity balancing, dependency-aware cutlines, or release-manager planning outputs.

## What This Skill Is Good For

- Detecting when a stale backlog export is not enough.
- Pulling every page from a live planning service and expanding each item into a complete fact record.
- Recomputing a deterministic sprint commitment from policy, capacity, and dependency rules.
- Producing triage tables, committed/deferred lists, and capacity summaries from the same underlying facts.

## Recommended Workflow

1. Read `/root/data/planning_manifest.json`, `/root/data/team_capacity.csv`, and `/root/data/delivery_policy.yaml`.
2. Fetch the live backlog through the planning service, not just the stale export.
3. Pull detail records for every item before deciding readiness, blockers, `must_ship`, or dependencies.
4. Build the sprint cutline in two passes:
   - Commit every eligible `must_ship` item first.
   - Evaluate the remaining eligible items in policy order, applying capacity constraints after each addition.
5. Write the required CSV, JSON, and manager-facing summary from the same selected/deferred decisions.

## Helper Scripts

- `python3 /root/.codex/skills/sprint-planner/scripts/fetch_live_backlog.py`
  - Fetches all pages and all item details from the live planning service.
- `python3 /root/.codex/skills/sprint-planner/scripts/build_sprint_plan.py`
  - Recomputes the triage and sprint plan from live data plus local policy/capacity inputs.

## Notes

- Do not trust `backlog_export.csv` as the final source of truth.
- The live planning service is paginated; missing a page changes the answer.
- Closed items still need triage rows, but they must not be committed.
