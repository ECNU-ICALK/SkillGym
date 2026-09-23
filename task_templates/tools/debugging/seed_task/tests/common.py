from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path("/root")
OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"
ARTIFACTS_DIR = ROOT / "artifacts"
APP_DIR = ROOT / "app"
SKILL_DIR = ROOT / ".codex" / "skills"

EXPECTED_HASHES = {
    "data/flights.csv": "3454abd46fa4551a607b238cba77ddeb2f555ddceb5b81e9622377163729c5ae",
    "data/airports.csv": "903c7169e6d558eefb95295fe2947ec8503135fbb855ea5c737cf4a90ea603ad",
    "artifacts/profiles/overview.cpuprofile": "cc84aa4d288b6897fa88aafe27bc1ae8818c6e9cc0c348fa9b3fd1ce145142c0",
    "artifacts/profiles/route-explorer.cpuprofile": "b37808fb3b5cfa4d2a7833746c75ac7ce59c7922c60b6b89ed82d389c69ed387",
    "artifacts/traces/Trace-route-explorer.json": "10fa416b1df9f400c9ddbfe2dbbb1540ddb06554eeb96ee35272a9169a96ce19",
    "app/index.html": "4608584d9eed2f03bcbee7b8e64633b0594fe9161cb57ac3cf5f453d090ffddd",
    "app/src/overview.js": "2a57855adc4ad5397706ff68ea11ad02dc60ea5ad1dbd75ce01578246251ec5a",
    "app/src/route_explorer.js": "1ea21a2b665bd64d47343d297728f22f441d89a1d55a26aa63096cafc210d5ac",
    "app/src/dataset_summary.json": "f37ad55268c2d83f3a4475f8ea68fa1beaa70a3c1032d63f75fc5582f736d6bb",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_output_json() -> dict:
    return read_json(OUTPUT_DIR / "findings.json")


def load_output_markdown() -> str:
    return (OUTPUT_DIR / "investigation.md").read_text(encoding="utf-8")


def cpuprofile_self_time_ms(path: Path) -> dict[str, float]:
    profile = read_json(path)
    by_id = {node["id"]: node for node in profile["nodes"]}
    totals = defaultdict(float)
    for sample_id, delta in zip(profile["samples"], profile["timeDeltas"]):
        func = by_id[sample_id]["callFrame"]["functionName"]
        totals[func] += delta / 1000.0
    return dict(totals)


def cpuprofile_duration_ms(path: Path) -> float:
    profile = read_json(path)
    return (profile["endTime"] - profile["startTime"]) / 1000.0


def cpuprofile_timeline(path: Path) -> list[dict]:
    profile = read_json(path)
    nodes = {node["id"]: node for node in profile["nodes"]}
    parent_map = {}
    for node in profile["nodes"]:
        for child in node.get("children", []):
            parent_map[child] = node["id"]

    def stack_for(sample_id: int) -> list[str]:
        frames = []
        current = sample_id
        while current in nodes:
            frames.append(nodes[current]["callFrame"]["functionName"])
            current = parent_map.get(current)
            if current is None:
                break
        return frames

    current_ts = profile["startTime"]
    rows = []
    for sample_id, delta in zip(profile["samples"], profile["timeDeltas"]):
        current_ts += delta
        rows.append(
            {
                "offset_ms": (current_ts - profile["startTime"]) / 1000.0,
                "function": nodes[sample_id]["callFrame"]["functionName"],
                "stack": stack_for(sample_id),
            }
        )
    return rows


def differential_hotspots_ms() -> list[tuple[str, float]]:
    ref = cpuprofile_self_time_ms(ARTIFACTS_DIR / "profiles" / "overview.cpuprofile")
    affected = cpuprofile_self_time_ms(ARTIFACTS_DIR / "profiles" / "route-explorer.cpuprofile")
    diffs = []
    for name, value in affected.items():
        delta = value - ref.get(name, 0.0)
        if delta > 0:
            diffs.append((name, delta))
    diffs.sort(key=lambda item: item[1], reverse=True)
    return diffs


def route_trace_events() -> list[dict]:
    return read_json(ARTIFACTS_DIR / "traces" / "Trace-route-explorer.json")["traceEvents"]


def trace_user_marks() -> tuple[float, float]:
    events = route_trace_events()
    start = next(e for e in events if e.get("name") == "route-explorer:start")
    ready = next(e for e in events if e.get("name") == "route-explorer:ready")
    return start["ts"] / 1000.0, ready["ts"] / 1000.0


def trace_duration_ms() -> float:
    start, ready = trace_user_marks()
    return ready - start


def trace_event_duration(name: str) -> float:
    return sum((e.get("dur", 0) or 0) for e in route_trace_events() if e.get("name") == name) / 1000.0


def trace_has_signal(signal: str) -> bool:
    events = route_trace_events()
    for event in events:
        if event.get("name") == signal:
            return True
        data = event.get("args", {}).get("data", {})
        if data.get("functionName") == signal:
            return True
    return False


def expected_activity_regions() -> list[dict]:
    return [
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


def expected_stack_examples() -> list[dict]:
    return [
        {
            "label": "route-only-compute",
            "frames_leaf_to_root": [
                "groupFlightsByAirport",
                "renderRouteExplorer",
                "bootstrapDashboard",
                "(root)",
            ],
        },
        {
            "label": "render-tail",
            "frames_leaf_to_root": [
                "renderRouteCards",
                "renderRouteExplorer",
                "bootstrapDashboard",
                "(root)",
            ],
        },
    ]


def output_only_expected_files() -> list[str]:
    if not OUTPUT_DIR.exists():
        return []
    return sorted(item.name for item in OUTPUT_DIR.iterdir() if item.is_file())


def markdown_sections(md: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = None
    for line in md.splitlines():
        if line.startswith("# "):
            current = line
            sections[current] = [line]
            continue
        if line.startswith("## "):
            current = line
            sections[current] = [line]
            continue
        if current is not None:
            sections[current].append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def quoted_contains(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return all(needle.lower() in lowered for needle in needles)
