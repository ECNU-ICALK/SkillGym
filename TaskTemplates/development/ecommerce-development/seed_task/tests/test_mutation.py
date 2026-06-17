from __future__ import annotations

import csv
import json
from pathlib import Path

from oracle import WORKSPACE_ROOT, expected_summary, extract_feed_items, request_json, run_cmd


SEED_PATH = Path("/app/data/met_print_seed.csv")
SUMMARY_PATH = WORKSPACE_ROOT / "output" / "seed-summary.json"


def mutate_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = [dict(row) for row in rows]
    for row in out:
        if row["objectID"] == "283170":
            row["launchState"] = "publish"
        if row["objectID"] == "492745":
            row["publicDomainClearance"] = "true"
            row["largeStock"] = "2"
    return out


def read_seed_rows() -> list[dict[str, str]]:
    with SEED_PATH.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_seed_rows(rows: list[dict[str, str]]) -> None:
    with SEED_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_summary_count() -> int:
    payload = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    return int(payload["launchFeedCount"])


def read_feed_count() -> int:
    status, payload = request_json("/wp-json/harbor-printshop/v1/launch-feed")
    if status != 200:
        raise AssertionError(f"launch-feed unavailable after reseed: status={status} payload={payload}")
    return len(extract_feed_items(payload))


def run_reseed() -> None:
    proc = run_cmd(["php", "/app/workspace/scripts/reseed.php"], check=True)
    if proc.returncode != 0:
        raise AssertionError(f"reseed failed: {proc.stdout}\n{proc.stderr}")


def main() -> None:
    original_rows = read_seed_rows()
    baseline_summary = read_summary_count()
    baseline_feed = read_feed_count()

    try:
        write_seed_rows(mutate_rows(original_rows))
        run_reseed()

        expected = expected_summary()
        mutated_summary = read_summary_count()
        mutated_feed = read_feed_count()

        if mutated_summary != expected["launchFeedCount"]:
            raise AssertionError(
                f"mutated summary launchFeedCount mismatch: got={mutated_summary} expected={expected['launchFeedCount']}"
            )
        if mutated_feed != expected["launchFeedCount"]:
            raise AssertionError(f"mutated feed count mismatch: got={mutated_feed} expected={expected['launchFeedCount']}")
        if mutated_summary == baseline_summary and mutated_feed == baseline_feed:
            raise AssertionError(
                "mutation did not affect outputs; reseed appears disconnected from input data"
            )
    finally:
        write_seed_rows(original_rows)
        run_reseed()

    print("PASS")


if __name__ == "__main__":
    main()
