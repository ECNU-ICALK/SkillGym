You are preparing a 3-day community wellness activity schedule for an Austin site team. The workspace already contains participant demand, venue rules, earlier condition exports, and a current local planning service. The schedule is not yet ready to publish. Your job is to deliver a compliant schedule and the supporting handoff for site operations.

Input data is in `/root/data/`:

- `planner_manifest.json`: site id, planning window, required session count, local timezone, and the base URLs of the current local planning service.
- `class_requests.csv`: requested sessions, preferred start times, attendance, accessibility needs, allowed venues, and adjustment preferences.
- `venue_catalog.csv`: approved venues, venue type, operating hours, capacity, accessibility support, and activity restrictions.
- `site_constraints.json`: program-wide operating rules, required advisory audiences, decision labels used by the schedule, and planning notes.
- `reference_weather_snapshot.json`: an earlier conditions export from a prior planning checkpoint.
- `reference_air_quality_snapshot.json`: an earlier conditions export from a prior planning checkpoint.

Your task

1. Evaluate every requested session against the current planning inputs and produce a session-level assessment.
2. Publish a final 3-day activity schedule that keeps every session compliant with operating rules, venue constraints, and participant support needs.
3. Adjust session timing or venue assignment when the requested setup is no longer compliant.
4. Produce participant advisories and an operations handoff that match the final schedule.

Output

If `/root/output/` does not exist, create it first.

1. Write `/root/output/session_risk_assessment.json`

Top-level structure must be exactly:

```json
{
  "site_id": "ATX-WELL-001",
  "planning_window_start": "2026-05-04T00:00:00-05:00",
  "planning_window_end": "2026-05-06T23:59:59-05:00",
  "sessions": [
    {
      "session_id": "S001",
      "risk_level": "green",
      "decision": "outdoor_ok",
      "primary_reasons": ["SAFE_TO_KEEP"],
      "recommended_setting": "outdoor",
      "recommended_window_start": "2026-05-04T08:00:00-05:00",
      "recommended_window_end": "2026-05-04T09:00:00-05:00"
    }
  ]
}
```

Requirements:

- Every session from `class_requests.csv` must appear exactly once in `sessions`.
- `risk_level` must be one of `green`, `amber`, or `red`.
- `decision` must be one of `outdoor_ok`, `move_indoors`, `move_to_lower_exposure`, `reschedule`, or `cancel`.
- `primary_reasons` must contain at least one machine-readable reason code.
- All timestamps must use the local timezone from the manifest.
- The assessment must follow the current planning service and the site constraints.

2. Write `/root/output/activity_schedule.csv`

Column names must be exactly:

```csv
session_id,program_day,activity_name,requested_start_local,final_start_local,final_end_local,venue_id,venue_name,setting,decision,expected_attendance,backup_plan,notes
```

Requirements:

- Every `session_id` from `class_requests.csv` must appear exactly once.
- `setting` must be `outdoor`, `covered`, or `indoor`.
- `decision` must align with `session_risk_assessment.json`.
- The final venue and time must satisfy venue hours, capacity, accessibility support, and activity restrictions.
- Keep the required number of sessions inside the planning window.
- Use `cancel` only if no compliant option exists in the current data.
- `backup_plan` must be a short actionable fallback.

3. Write `/root/output/participant_advisories.csv`

Column names must be exactly:

```csv
session_id,audience,advisory_code,message
```

Requirements:

- At least one advisory row is required for every session.
- `audience` must be `all`, `outdoor_only`, `high_heat_sensitive`, or `mobility_support`.
- `message` must be concise and actionable.
- Advisory content must match the final schedule and current operating conditions.

4. Write `/root/output/operations_handoff.md`

It must contain these H1 headings in this order:

- `# Safety Overview`
- `# Schedule Changes`
- `# Venue Notes`
- `# Participant Advisories`
- `# Open Risks`

Requirements:

- Summarize the main risk drivers for the planning window.
- Call out every moved, rescheduled, or canceled session.
- Mention venue-specific limits that affected the plan.
- Include any remaining watch items for staff.

Notes:

- Use the provided planning inputs to publish a compliant schedule.
- `reference_weather_snapshot.json` and `reference_air_quality_snapshot.json` come from an earlier planning checkpoint.
- Do not edit files under `/root/data/`.
- Do not invent venues, activities, or policy thresholds.
- Do not keep a requested setup unchanged when current constraints make it non-compliant and an allowed alternative exists.
- Do not bypass the local planning service, hardcode final outputs, or reduce scope by dropping sessions that can still be scheduled.
- Do not modify tests, verifier files, or environment files.
- You may write helper scripts in the workspace, but the final submission only needs the required files under `/root/output/`.
