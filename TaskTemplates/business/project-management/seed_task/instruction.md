You need to finalize the commitment plan for the next two-week Sprint for an internal product team, and deliver an executable schedule to the release manager.

Input data is under `/root/data/`:

- `planning_manifest.json`: sprint id, planning window, and the local planning service entrypoint.
- `backlog_export.csv`: an older export of candidate backlog items; may be outdated or incomplete.
- `team_capacity.csv`: capacity information for this Sprint.
- `delivery_policy.yaml`: delivery strategy and selection constraints for this Sprint.
- `planning_notes/`: requirement summaries, milestone background, and extra context normalized from the public backlog.

## Your Task

1. Review all candidate backlog items and produce a complete triage result for the candidate set.
2. Use the in-container planning service as the source of truth to determine which items can be committed in this Sprint.
3. Produce an executable Sprint plan that describes committed items, deferred items and reasons, capacity usage, and major risks.
4. Write a short update for the release manager summarizing the Sprint scope and key blockers.

## Business Constraints

1. All candidate items must appear in the triage output; none may be omitted.
2. `backlog_export.csv` is not the final source of truth. The in-container planning service is authoritative for backlog status and related planning data.
3. Items that are done, cancelled, or archived must not be committed into the Sprint.
4. Only items that satisfy the current delivery policy and capacity constraints may be committed.
5. Items with `must_ship = true` must be prioritized when they meet commitment conditions.
6. If an item is not included in the Sprint, you must provide a single, unique rejection reason.

## Output

If `/root/output/` does not exist, create it first.

Write `/root/output/backlog_triage.csv`. The column names must be exactly:

```csv
item_id,title,priority,story_points,owner_role,milestone_date,ready,blocked,must_ship,qa_required,selected,rejection_reason
```

Requirements:

- Must include all candidate items, and each `item_id` may appear only once.
- `milestone_date` uses `YYYY-MM-DD`.
- `ready`, `blocked`, `must_ship`, `qa_required`, `selected` must be `true` or `false`.
- `rejection_reason` must be an empty string or one of:
  - `already_closed`
  - `not_ready`
  - `blocked_dependency`
  - `insufficient_story_points`
  - `insufficient_qa_capacity`
  - `insufficient_review_capacity`
  - `below_cutline`

Write `/root/output/sprint_plan.json` with the following structure:

```json
{
  "sprint_id": "SPR-000",
  "committed_item_ids": ["ITEM-1"],
  "committed_items": [
    {
      "item_id": "ITEM-1",
      "title": "Example",
      "priority": "P1",
      "story_points": 3,
      "owner_role": "Backend Engineer",
      "depends_on": ["ITEM-0"],
      "why_selected": "Required for milestone and fits current sprint capacity."
    }
  ],
  "deferred_items": [
    {
      "item_id": "ITEM-9",
      "rejection_reason": "below_cutline",
      "explanation": "Lower priority than remaining committed work."
    }
  ],
  "capacity_summary": {
    "story_points_available": 0,
    "buffer_points_reserved": 0,
    "story_points_committed": 0,
    "qa_slots_available": 0,
    "qa_slots_used": 0,
    "review_slots_available": 0,
    "review_slots_used": 0
  },
  "risk_flags": [
    "Example risk"
  ],
  "notes": [
    "Example note"
  ]
}
```

Requirements:

- `committed_item_ids` must exactly match the set of `item_id` values in `committed_items`, and in the same order.
- `deferred_items` must cover all items where `selected = false` and `rejection_reason` is not `already_closed`.
- `depends_on` must list hard dependency item IDs for the item; if none, use an empty array.
- `story_points_committed` must not exceed the Sprint commitment upper bound allowed by policy.
- `qa_slots_used` and `review_slots_used` must not exceed the corresponding available capacities.
- `risk_flags` must include at least the most important delivery risk and capacity risk.

Write `/root/output/manager_update.md`. The content must include:

- the Sprint id;
- the total number of committed items;
- the list of committed item IDs;
- total committed story points;
- high-priority items that did not make the Sprint;
- the main capacity bottleneck(s);
- the most important delivery risk(s);
- a brief explanation of the tradeoff logic used.

## Notes

- Do not modify files under `/root/data/`.
- Do not treat `backlog_export.csv` as the only source of truth, and do not bypass the in-container planning service.
- Do not replace the real planning chain with hard-coded results, cached answers, or manually fabricated outputs.
- It is explicitly forbidden to replace the real chain, delete functionality to evade issues, or reduce the delivery scope to evade constraints.
- Do not modify verifier files, task metadata, or environment files.
- You may write helper scripts in the working directory, but the only required deliverables are the 3 files under `/root/output/`.
