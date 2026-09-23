You are investigating a performance incident in a local flight operations dashboard.

Input data is available in `/root/`:

- `/root/app/`: dashboard source code and local runtime scripts.
- `/root/data/flights.csv`: flight and delay snapshot used by the dashboard.
- `/root/data/airports.csv`: airport metadata used for route labels and filters.
- `/root/artifacts/profiles/overview.cpuprofile`: CPU profile for a lower-latency reference flow.
- `/root/artifacts/profiles/route-explorer.cpuprofile`: CPU profile for the affected Route Explorer flow.
- `/root/artifacts/traces/Trace-route-explorer.json`: DevTools performance capture for the affected Route Explorer flow.

Your task

1. Investigate the provided performance captures and determine the main causes behind the Route Explorer slowdown.
2. Compare the affected flow against the lower-latency reference flow and identify which costs are concentrated in the affected path.
3. Produce an evidence-backed handoff that another engineer can use to plan follow-up work.

Output

If `/root/output/` does not exist, create it first.

1. Write `/root/output/findings.json`

The top-level structure must be exactly:

```json
{
  "incident_id": "route-explorer-latency",
  "reference_path": "",
  "affected_path": "",
  "top_findings": [
    {
      "rank": 1,
      "title": "",
      "category": "",
      "confidence": "",
      "evidence_files": [],
      "signals": [],
      "user_impact": "",
      "why_it_matters": ""
    }
  ],
  "timeline_summary": {
    "reference_profile_duration_ms": 0,
    "affected_profile_duration_ms": 0,
    "user_ready_duration_ms": 0,
    "profile_gap_ms": 0
  },
  "activity_regions": [
    {
      "phase": "",
      "start_ms": 0,
      "end_ms": 0,
      "dominant_leaf_frames": []
    }
  ],
  "stack_examples": [
    {
      "label": "",
      "frames_leaf_to_root": []
    }
  ]
}
```

Requirements:

- `incident_id` must be `route-explorer-latency`.
- `reference_path` must describe the reference flow you used.
- `affected_path` must describe the affected flow you analyzed.
- `top_findings` must contain exactly 3 items.
- `rank` values must be `1`, `2`, and `3` in ascending order.
- `category` must be one of `javascript`, `rendering`, `data-processing`, `gc`, or `other`.
- `confidence` must be one of `high`, `medium`, or `low`.
- `evidence_files` must reference only files from `/root/artifacts/profiles/` or `/root/artifacts/traces/`.
- `signals` must contain 1 to 5 evidence labels for each finding.
- All values in `timeline_summary` must be numeric milliseconds.
- `reference_profile_duration_ms` must describe the sampled CPU span of the lower-latency reference profile.
- `affected_profile_duration_ms` must describe the sampled CPU span of the affected Route Explorer profile.
- `user_ready_duration_ms` must describe the `route-explorer:start` to `route-explorer:ready` span from the trace.
- `profile_gap_ms` must compare the affected and reference CPU profile spans, not the user-ready span.
- `activity_regions` must contain exactly 3 items, ordered by time, and each item must describe one contiguous region from the affected sampled CPU path.
- `phase` must be one of `shared-setup`, `route-only-compute`, or `render-gc-tail`.
- `start_ms` and `end_ms` must be numeric offsets relative to the start of `route-explorer.cpuprofile`.
- `dominant_leaf_frames` must list 1 to 4 sampled leaf frames in chronological order for that region.
- `stack_examples` must contain exactly 2 items.
- `label` must be one of `route-only-compute` or `render-tail`.
- `frames_leaf_to_root` must list the sampled stack from leaf frame to root frame.

2. Write `/root/output/investigation.md`

This file must contain these sections in this order:

- `# Route Explorer Performance Investigation`
- `## Symptoms`
- `## Comparison`
- `## Findings`
- `## Recommended Follow-up`

Requirements:

- In `## Comparison`, include a table with the columns `Path`, `Approx Duration (ms)`, and `Notes`.
- In `## Findings`, include exactly 3 numbered findings.
- The 3 findings in `investigation.md` must match the 3 items in `findings.json`.
- Include at least one timing comparison between the reference flow and the affected flow.
- Clearly separate the affected CPU profile span from the longer user-visible `start` to `ready` span.
- Explain which work belongs to the shared setup path before the Route Explorer-only phases begin, and avoid presenting that shared setup as the primary bottleneck.
- Include a short summary of the 3 sampled regions from `activity_regions`.
- Include at least one leaf-to-root stack example from `stack_examples`.
- Cite the relevant capture filenames when presenting evidence.

3. `/root/output/` must contain only:

- `findings.json`
- `investigation.md`

Notes:

- Treat the provided CPU profiles and trace file as the authoritative source for timing evidence.
- You may run the local dashboard for context if needed, but your conclusions must be supported by the provided captures.
- Do not modify files under `/root/data/`, `/root/artifacts/`, `/root/tests/`, or `/root/.codex/skills/`.
- Do not modify the dashboard source code.
- Do not write placeholder conclusions.
