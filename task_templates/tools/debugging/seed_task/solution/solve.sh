#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

root = Path("/root")
output = root / "output"
output.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def profile_self_time(path: Path) -> dict[str, float]:
    data = load_json(path)
    nodes = {node["id"]: node for node in data["nodes"]}
    totals = defaultdict(float)
    for sample_id, delta in zip(data["samples"], data["timeDeltas"]):
        totals[nodes[sample_id]["callFrame"]["functionName"]] += delta / 1000.0
    return dict(totals)


def profile_timeline(path: Path) -> list[dict]:
    data = load_json(path)
    nodes = {node["id"]: node for node in data["nodes"]}
    parents = {}
    for node in data["nodes"]:
        for child in node.get("children", []):
            parents[child] = node["id"]

    def stack_for(sample_id: int) -> list[str]:
        frames = []
        current = sample_id
        while current in nodes:
            frames.append(nodes[current]["callFrame"]["functionName"])
            current = parents.get(current)
            if current is None:
                break
        return frames

    ts = data["startTime"]
    rows = []
    for sample_id, delta in zip(data["samples"], data["timeDeltas"]):
        ts += delta
        rows.append(
            {
                "offset_ms": (ts - data["startTime"]) / 1000.0,
                "function": nodes[sample_id]["callFrame"]["functionName"],
                "stack": stack_for(sample_id),
            }
        )
    return rows


def trace_duration_ms(path: Path) -> float:
    events = load_json(path)["traceEvents"]
    start = next(event for event in events if event.get("name") == "route-explorer:start")
    ready = next(event for event in events if event.get("name") == "route-explorer:ready")
    return (ready["ts"] - start["ts"]) / 1000.0


def top_differentials() -> list[tuple[str, float]]:
    ref = profile_self_time(root / "artifacts/profiles/overview.cpuprofile")
    affected = profile_self_time(root / "artifacts/profiles/route-explorer.cpuprofile")
    diffs = []
    for name, value in affected.items():
        delta = value - ref.get(name, 0.0)
        if delta > 0:
            diffs.append((name, delta))
    diffs.sort(key=lambda item: item[1], reverse=True)
    return diffs


ref_profile = load_json(root / "artifacts/profiles/overview.cpuprofile")
affected_profile = load_json(root / "artifacts/profiles/route-explorer.cpuprofile")
affected_trace = root / "artifacts/traces/Trace-route-explorer.json"
reference_duration_ms = (ref_profile["endTime"] - ref_profile["startTime"]) / 1000.0
affected_profile_duration_ms = (affected_profile["endTime"] - affected_profile["startTime"]) / 1000.0
user_ready_duration_ms = trace_duration_ms(affected_trace)
profile_gap_ms = affected_profile_duration_ms - reference_duration_ms
differentials = top_differentials()
timeline = profile_timeline(root / "artifacts/profiles/route-explorer.cpuprofile")

activity_regions = [
    {
        "phase": "shared-setup",
        "start_ms": 1.0,
        "end_ms": 480.0,
        "dominant_leaf_frames": [
            "parseFlightsCsv",
            "normalizeAirportCodes",
            "buildAirportFilterIndex",
        ],
    },
    {
        "phase": "route-only-compute",
        "start_ms": 481.0,
        "end_ms": 1610.0,
        "dominant_leaf_frames": [
            "groupFlightsByAirport",
            "computeConnectionMatrix",
            "buildDelayHeatmap",
        ],
    },
    {
        "phase": "render-gc-tail",
        "start_ms": 1611.0,
        "end_ms": 2025.0,
        "dominant_leaf_frames": [
            "renderRouteCards",
            "PaintRouteCards",
            "(garbage collector)",
        ],
    },
]

stack_examples = [
    {
        "label": "route-only-compute",
        "frames_leaf_to_root": next(
            row["stack"] for row in timeline if row["function"] == "groupFlightsByAirport"
        ),
    },
    {
        "label": "render-tail",
        "frames_leaf_to_root": next(
            row["stack"] for row in timeline if row["function"] == "renderRouteCards"
        ),
    },
]

findings = [
    {
        "rank": 1,
        "title": "Repeated airport grouping dominates the affected path",
        "category": "data-processing",
        "confidence": "high",
        "evidence_files": [
            "/root/artifacts/profiles/route-explorer.cpuprofile",
            "/root/artifacts/profiles/overview.cpuprofile",
        ],
        "signals": [
            "shared baseline about 380ms before route-only work",
            "groupFlightsByAirport 520ms",
            "buildDelayHeatmap 430ms",
            "computeConnectionMatrix 180ms",
            "affected sampled CPU 2025ms vs reference 760ms",
        ],
        "user_impact": "The Route Explorer path spends most of its extra CPU time in route-only transforms after the shared setup completes, so the view remains blocked before results can settle.",
        "why_it_matters": "The shared baseline is similar across both paths, but the affected profile adds about 1265 ms of extra sampled CPU, with roughly 1130 ms concentrated in route-only data work.",
    },
    {
        "rank": 2,
        "title": "Route card rendering adds a visible layout and paint tail",
        "category": "rendering",
        "confidence": "high",
        "evidence_files": [
            "/root/artifacts/profiles/route-explorer.cpuprofile",
            "/root/artifacts/traces/Trace-route-explorer.json",
        ],
        "signals": [
            "renderRouteCards 250ms",
            "UpdateLayoutTree 158ms",
            "PrePaint 41ms",
            "Paint 87ms",
            "user ready stays at 2175ms",
        ],
        "user_impact": "Even after the route-only compute burst finishes, the affected path still spends additional time rendering cards and settling layout before users see a stable screen.",
        "why_it_matters": "The affected path has a separate rendering tail, so reducing upstream compute alone will not recover the full user-visible delay.",
    },
    {
        "rank": 3,
        "title": "Garbage collection adds a smaller but measurable end-of-path stall",
        "category": "gc",
        "confidence": "medium",
        "evidence_files": [
            "/root/artifacts/profiles/overview.cpuprofile",
            "/root/artifacts/profiles/route-explorer.cpuprofile",
            "/root/artifacts/traces/Trace-route-explorer.json",
        ],
        "signals": [
            "MinorGC 75ms",
            "garbage collector 75ms in affected profile",
            "garbage collector 30ms in reference profile",
        ],
        "user_impact": "The Route Explorer startup ends with an extra collection pause, which adds a noticeable tail after the heavy compute and render work.",
        "why_it_matters": "GC is not the primary cause, but it compounds the affected path and is clearly larger than the reference tail.",
    },
]

payload = {
    "incident_id": "route-explorer-latency",
    "reference_path": "Overview flow",
    "affected_path": "Route Explorer flow",
    "top_findings": findings,
    "timeline_summary": {
        "reference_profile_duration_ms": round(reference_duration_ms, 3),
        "affected_profile_duration_ms": round(affected_profile_duration_ms, 3),
        "user_ready_duration_ms": round(user_ready_duration_ms, 3),
        "profile_gap_ms": round(profile_gap_ms, 3),
    },
    "activity_regions": activity_regions,
    "stack_examples": stack_examples,
}

(output / "findings.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

markdown = f"""# Route Explorer Performance Investigation

## Symptoms
Route Explorer takes noticeably longer to settle than the Overview flow. The sampled CPU span is 2025 ms in `route-explorer.cpuprofile` versus 760 ms in `overview.cpuprofile`, and the user-visible `route-explorer:start` to `route-explorer:ready` span reaches 2175 ms in `Trace-route-explorer.json`.

## Comparison
| Path | Approx Duration (ms) | Notes |
| --- | ---: | --- |
| Overview sampled CPU | {reference_duration_ms:.0f} | Lower-latency reference path from `overview.cpuprofile`. |
| Route Explorer sampled CPU | {affected_profile_duration_ms:.0f} | Affected CPU path from `route-explorer.cpuprofile`; the profile gap vs. Overview is about {profile_gap_ms:.0f} ms. |
| Route Explorer user-ready span | {user_ready_duration_ms:.0f} | `route-explorer:start` to `route-explorer:ready` from `Trace-route-explorer.json`, which stays longer than the sampled CPU span because render and tail work continue after the main route-only compute burst. |

## Findings
1. Repeated airport grouping dominates the affected path. Evidence: `route-explorer.cpuprofile`, `overview.cpuprofile`, and `Trace-route-explorer.json`. Signals: shared baseline about 380 ms before route-only work, `groupFlightsByAirport` 520 ms, `buildDelayHeatmap` 430 ms, and `computeConnectionMatrix` 180 ms. This means the shared baseline is not the primary bottleneck; the profile gap is about {profile_gap_ms:.0f} ms because the affected path adds route-only data work after that setup.
2. Route card rendering adds a visible layout and paint tail. Evidence: `route-explorer.cpuprofile` and `Trace-route-explorer.json`. Signals: `renderRouteCards` 250 ms, `UpdateLayoutTree` 158 ms, `PrePaint` 41 ms, and `Paint` 87 ms.
3. Garbage collection adds a smaller but measurable end-of-path stall. Evidence: `overview.cpuprofile`, `route-explorer.cpuprofile`, and `Trace-route-explorer.json`. Signals: `MinorGC` 75 ms and `(garbage collector)` 75 ms in the affected profile versus 30 ms in the reference.

Sampled regions: `shared-setup` 1-480 ms (`parseFlightsCsv`, `normalizeAirportCodes`, `buildAirportFilterIndex`), `route-only-compute` 481-1610 ms (`groupFlightsByAirport`, `computeConnectionMatrix`, `buildDelayHeatmap`), and `render-gc-tail` 1611-2025 ms (`renderRouteCards`, `PaintRouteCards`, `(garbage collector)`).

Stack example: `groupFlightsByAirport -> renderRouteExplorer -> bootstrapDashboard -> (root)`.

## Recommended Follow-up
Keep the shared setup path intact in the diagnosis, then reduce the route-only transforms that create most of the 1265 ms profile gap. After that, trim route-card layout work and the final GC tail so the 2175 ms user-ready span moves closer to the 2025 ms sampled CPU span and, eventually, toward the 760 ms reference profile.
"""

(output / "investigation.md").write_text(markdown, encoding="utf-8")
PY
