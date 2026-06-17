import os
import json
import time
import urllib.request
from pathlib import Path

from oracle import expected_feed_contract, expected_summary, feed_matches_contract, summary_matches_contract


BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:3000")
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))


def extract_feed_items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("items", [])
    return []


def extract_feed_total(payload, items):
    if isinstance(payload, dict) and isinstance(payload.get("total"), int):
        return payload["total"]
    return len(items)


def wait_for_server():
    for _ in range(120):
        try:
            with urllib.request.urlopen(BASE_URL + "/api/highlight-lanes/feed", timeout=5) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(1)
    raise RuntimeError("server did not become ready after reseed")


def main():
    wait_for_server()

    summary = json.loads((WORKSPACE_ROOT / "output" / "seed-summary.json").read_text(encoding="utf-8"))
    matches, reason = summary_matches_contract(summary, WORKSPACE_ROOT)
    if not matches:
        raise SystemExit(f"summary did not update after input mutation: {reason}; actual={summary}; expected={expected_summary(WORKSPACE_ROOT)}")

    with urllib.request.urlopen(BASE_URL + "/api/highlight-lanes/feed", timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    expected_items = expected_feed_contract(WORKSPACE_ROOT)
    actual_items = extract_feed_items(payload)
    matches, reason = feed_matches_contract(actual_items, WORKSPACE_ROOT)
    if not matches:
        raise SystemExit(f"mutated feed payload does not match derived expected items: {reason}")

    leaked = sorted(
        item["objectURL"]
        for item in actual_items
        if item["objectURL"] in {
            "https://www.metmuseum.org/art/collection/search/436532",
            "https://www.metmuseum.org/art/collection/search/488319",
        }
    )
    if leaked:
        raise SystemExit(f"mutated feed still contains invalid items: {leaked}")

    total = extract_feed_total(payload, actual_items)
    if total != len(expected_items):
        raise SystemExit(f"mutated feed expected total={len(expected_items)}, got {total}")

    print("PASS")
