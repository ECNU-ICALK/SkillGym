import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import redis


WORKSPACE = Path("/app/workspace")
DATA_DIR = WORKSPACE / "data"
OUTPUT_DIR = Path("/app/output")
PLAN_PATH = OUTPUT_DIR / "rebalance_plan.csv"
SUMMARY_PATH = OUTPUT_DIR / "network_summary.json"
NAMESPACE = "rebalance:v1"

EXPECTED_SOURCE_HASHES = {
    "dispatch_rules.json": "b4e29ce9395c81fa364f5e38557a5f6024a159abaead7f8e0fefbacb4b25238d",
    "station_information.json": "2176857bb263ff063b1ceace46d18b21f0f747e46b7611cb4b3db5af9c433d88",
    "station_status.json": "a7f495354f6bd01897844f881cc2de6e0513ce20e0258fb1ddd00198e1396143",
    "system_information.json": "8a2903b491dcce4d45d7087caaed36f39bb94dcca82fb7f57740131b2750d971",
    "system_regions.json": "069af6ad3c3dadd7888fa292433f9fa9bb540dfc2cebea45797f8c83a941b717",
}


def run_shell(command: str, env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        ["/bin/bash", "-lc", command],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(cwd or WORKSPACE),
        env=merged,
    )


def redis_client() -> redis.Redis:
    return redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)


def clear_namespace() -> None:
    client = redis_client()
    cursor = 0
    while True:
        cursor, keys = client.scan(cursor=cursor, match=f"{NAMESPACE}:*", count=200)
        if keys:
            client.delete(*keys)
        if cursor == 0:
            break


def run_job(workspace: Path = WORKSPACE, output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    env = {
        "TASK_WORKSPACE": str(workspace),
        "TASK_OUTPUT_DIR": str(output_dir),
        "PYTHONPATH": str(workspace),
    }
    run_shell("./bin/run_dispatch_prep.sh", env=env, cwd=workspace)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def round_half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


def expected_outputs(data_dir: Path) -> tuple[list[dict[str, str]], dict]:
    station_information = load_json(data_dir / "station_information.json")
    station_status = load_json(data_dir / "station_status.json")
    system_regions = load_json(data_dir / "system_regions.json")
    system_information = load_json(data_dir / "system_information.json")
    rules = load_json(data_dir / "dispatch_rules.json")
    run_digest = compute_run_digest(data_dir)

    status_by_id = {row["station_id"]: row for row in station_status["data"]["stations"]}
    region_name_by_id = {
        row["region_id"]: row["name"] for row in system_regions["data"]["regions"]
    }
    stations = []
    for row in station_information["data"]["stations"]:
        merged = {**row, **status_by_id[row["station_id"]]}
        merged["region_name"] = region_name_by_id[row["region_id"]]
        stations.append(merged)

    managed_regions = set(rules["managed_region_ids"])
    excluded_ids = set(rules["excluded_station_ids"])
    eligible_rows = []
    excluded_count = 0
    for row in stations:
        if row["station_id"] in excluded_ids:
            excluded_count += 1
            continue
        if row["region_id"] not in managed_regions:
            continue
        if int(row["capacity"]) < int(rules["min_capacity"]):
            continue
        if not (
            row["is_installed"] == 1
            and row["is_renting"] == 1
            and row["is_returning"] == 1
        ):
            continue
        eligible_rows.append(row)

    region_context = {}
    for region_id, target_ratio in rules["region_targets"].items():
        region_rows = [row for row in eligible_rows if row["region_id"] == region_id]
        capacity_total = sum(int(row["capacity"]) for row in region_rows)
        bikes_total = sum(int(row["num_bikes_available"]) for row in region_rows)
        fill_ratio = (bikes_total / capacity_total) if capacity_total else 0.0
        region_context[region_id] = {
            "region_name": region_name_by_id[region_id],
            "eligible_stations": len(region_rows),
            "fill_ratio": fill_ratio,
            "target_ratio": float(target_ratio),
        }

    candidates_by_region: dict[str, list[dict]] = {region_id: [] for region_id in managed_regions}
    over_capacity_count = 0
    for row in eligible_rows:
        capacity = int(row["capacity"])
        bikes = int(row["num_bikes_available"])
        docks = int(row["num_docks_available"])
        target_ratio = float(rules["region_targets"][row["region_id"]])
        occupancy_ratio = bikes / capacity
        if bikes > capacity:
            over_capacity_count += 1
        if occupancy_ratio <= float(rules["low_fill_ratio"]):
            action = "dropoff"
        elif occupancy_ratio >= float(rules["high_fill_ratio"]):
            action = "pickup"
        else:
            continue

        desired_bikes = max(1, round_half_up(target_ratio * capacity))
        bike_gap = abs(bikes - desired_bikes)
        movement_capacity = bikes if action == "pickup" else docks
        bikes_to_move = min(int(rules["max_move_per_station"]), max(1, bike_gap), movement_capacity)
        if bikes_to_move <= 0:
            continue

        region_fill_ratio = region_context[row["region_id"]]["fill_ratio"]
        if action == "pickup":
            region_pressure = max(0.0, region_fill_ratio - target_ratio)
        else:
            region_pressure = max(0.0, target_ratio - region_fill_ratio)
        zero_side_bonus = 0.0
        if action == "pickup" and docks == 0:
            zero_side_bonus = float(rules["priority_weights"]["zero_side_bonus"])
        if action == "dropoff" and bikes == 0:
            zero_side_bonus = float(rules["priority_weights"]["zero_side_bonus"])

        priority_score = round(
            bike_gap * float(rules["priority_weights"]["bike_gap_weight"])
            + capacity * float(rules["priority_weights"]["capacity_weight"])
            + region_pressure * float(rules["priority_weights"]["region_pressure_weight"])
            + zero_side_bonus,
            2,
        )
        evidence = {
            "window_id": rules["window_id"],
            "capacity": capacity,
            "num_bikes_available": bikes,
            "num_docks_available": docks,
            "desired_bikes": desired_bikes,
            "bike_gap": bike_gap,
            "occupancy_ratio": round(occupancy_ratio, 4),
            "target_ratio": target_ratio,
            "region_fill_ratio": round(region_fill_ratio, 4),
            "region_pressure": round(region_pressure, 4),
            "priority_weights": rules["priority_weights"],
            "thresholds": {
                "low_fill_ratio": float(rules["low_fill_ratio"]),
                "high_fill_ratio": float(rules["high_fill_ratio"]),
                "min_capacity": int(rules["min_capacity"]),
                "max_move_per_station": int(rules["max_move_per_station"]),
            },
            "operational_flags": {
                "is_installed": row["is_installed"],
                "is_renting": row["is_renting"],
                "is_returning": row["is_returning"],
            },
            "last_reported": int(row["last_reported"]),
            "run_digest": run_digest,
        }
        candidates_by_region[row["region_id"]].append(
            {
                "station_id": row["station_id"],
                "station_name": row["name"],
                "region": row["region_name"],
                "region_id": row["region_id"],
                "action": action,
                "priority_score": priority_score,
                "bikes_to_move": bikes_to_move,
                "evidence": evidence,
            }
        )

    candidates = []
    for region_id, region_candidates in candidates_by_region.items():
        region_candidates.sort(
            key=lambda row: (-row["priority_score"], row["station_name"], row["station_id"])
        )
        limit = int(rules["region_action_limits"][region_id])
        for rank, candidate in enumerate(region_candidates, start=1):
            candidate["evidence"]["region_rank"] = rank
            candidate["evidence"]["region_limit"] = limit
        candidates.extend(region_candidates)

    selected = []
    for region_id in sorted(candidates_by_region):
        selected.extend(candidates_by_region[region_id][: int(rules["region_action_limits"][region_id])])
    selected.sort(
        key=lambda row: (-row["priority_score"], row["region"], row["station_name"], row["station_id"])
    )

    region_summaries = []
    selected_by_region = defaultdict(list)
    for row in selected:
        selected_by_region[row["region_id"]].append(row)
    for region_id in sorted(rules["region_targets"]):
        region_rows = selected_by_region.get(region_id, [])
        pickup_rows_region = [row for row in region_rows if row["action"] == "pickup"]
        dropoff_rows_region = [row for row in region_rows if row["action"] == "dropoff"]
        priorities = [float(row["priority_score"]) for row in region_rows]
        context = region_context[region_id]
        region_summaries.append(
            {
                "region_id": region_id,
                "region": context["region_name"],
                "selected_rows": len(region_rows),
                "candidate_rows": len(candidates_by_region.get(region_id, [])),
                "action_limit": int(rules["region_action_limits"][region_id]),
                "pickup_rows": len(pickup_rows_region),
                "dropoff_rows": len(dropoff_rows_region),
                "pickup_bikes": sum(int(row["bikes_to_move"]) for row in pickup_rows_region),
                "dropoff_bikes": sum(int(row["bikes_to_move"]) for row in dropoff_rows_region),
                "avg_priority_score": round(sum(priorities) / len(priorities), 2) if priorities else 0.0,
                "region_fill_ratio": round(float(context["fill_ratio"]), 4),
                "target_ratio": round(float(context["target_ratio"]), 4),
                "eligible_stations": int(context["eligible_stations"]),
            }
        )

    csv_rows = []
    for row in selected:
        csv_rows.append(
            {
                "station_id": row["station_id"],
                "station_name": row["station_name"],
                "region": row["region"],
                "action": row["action"],
                "priority_score": f"{row['priority_score']:.2f}",
                "bikes_to_move": str(row["bikes_to_move"]),
                "evidence": json.dumps(row["evidence"], separators=(",", ":")),
            }
        )

    action_counts = {
        "pickup": sum(1 for row in selected if row["action"] == "pickup"),
        "dropoff": sum(1 for row in selected if row["action"] == "dropoff"),
    }
    summary = {
        "window": {
            "window_id": rules["window_id"],
            "system_id": system_information["data"]["system_id"],
            "system_name": system_information["data"]["name"],
            "timezone": system_information["data"]["timezone"],
        },
        "totals": {
            "eligible_stations": len(eligible_rows),
            "candidate_stations": sum(len(rows) for rows in candidates_by_region.values()),
            "plan_rows": len(selected),
            "pickup_rows": action_counts["pickup"],
            "dropoff_rows": action_counts["dropoff"],
            "pickup_bikes": sum(
                row["bikes_to_move"] for row in selected if row["action"] == "pickup"
            ),
            "dropoff_bikes": sum(
                row["bikes_to_move"] for row in selected if row["action"] == "dropoff"
            ),
        },
        "action_counts": action_counts,
        "regions": region_summaries,
        "ingest": {
            "run_digest": run_digest,
            "station_rows": len(stations),
            "status_rows": len(stations),
            "managed_region_count": len(managed_regions),
            "excluded_station_count": excluded_count,
            "over_capacity_station_count": over_capacity_count,
            "redis_namespace": rules["redis_namespace"],
        },
        "notes": [
            "Plan rows are selected from managed, non-excluded stations that meet the operating and capacity thresholds.",
            "Per-region selection is capped by dispatch_rules.region_action_limits and ranked by bike gap, station capacity, zero-side urgency, and directional region pressure.",
        ],
    }
    if over_capacity_count:
        summary["notes"].append(
            f"{over_capacity_count} eligible station records reported more bikes than physical capacity; those anomalies were kept visible in the scoring evidence."
        )
    return csv_rows, summary


def compute_run_digest(data_dir: Path) -> str:
    hasher = hashlib.sha256()
    for name in [
        "dispatch_rules.json",
        "station_information.json",
        "station_status.json",
        "system_information.json",
        "system_regions.json",
    ]:
        hasher.update(name.encode("utf-8"))
        hasher.update((data_dir / name).read_bytes())
    return hasher.hexdigest()


def normalize_summary(summary: dict) -> dict:
    clone = json.loads(json.dumps(summary))
    clone["window"].pop("generated_at", None)
    return clone


def plan_core(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    core_fields = [
        "station_id",
        "station_name",
        "region",
        "action",
        "priority_score",
        "bikes_to_move",
    ]
    return [{field: row[field] for field in core_fields} for row in rows]


def plan_identity(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    identity_fields = [
        "station_id",
        "station_name",
        "region",
        "action",
        "bikes_to_move",
    ]
    return [{field: row[field] for field in identity_fields} for row in rows]


def plan_identity_overlap(
    actual_rows: list[dict[str, str]],
    expected_rows: list[dict[str, str]],
    *,
    min_overlap: int = 9,
) -> None:
    actual = {
        (
            row["station_id"],
            row["station_name"],
            row["region"],
            row["action"],
            row["bikes_to_move"],
        )
        for row in actual_rows
    }
    expected = {
        (
            row["station_id"],
            row["station_name"],
            row["region"],
            row["action"],
            row["bikes_to_move"],
        )
        for row in expected_rows
    }
    assert len(actual_rows) == len(expected_rows)
    assert len(actual & expected) >= min_overlap


def assert_priority_scores_close(
    actual_rows: list[dict[str, str]],
    expected_rows: list[dict[str, str]],
    *,
    max_abs_diff: float = 35.0,
    mean_abs_diff: float = 25.0,
) -> None:
    diffs = []
    for actual, expected in zip(actual_rows, expected_rows, strict=True):
        diffs.append(abs(float(actual["priority_score"]) - float(expected["priority_score"])))
    assert diffs
    assert max(diffs) <= max_abs_diff
    assert sum(diffs) / len(diffs) <= mean_abs_diff


def assert_plan_sorted(rows: list[dict[str, str]]) -> None:
    normalized = [
        (
            row["station_id"],
            row["station_name"],
            row["region"],
            row["action"],
            f"{float(row['priority_score']):.2f}",
            str(int(row["bikes_to_move"])),
        )
        for row in rows
    ]
    expected = sorted(
        normalized,
        key=lambda row: (-float(row[4]), row[2], row[1], row[0]),
    )
    assert normalized == expected


def assert_evidence_contract(rows: list[dict[str, str]], expected_run_digest: str) -> None:
    for row in rows:
        evidence = json.loads(row["evidence"])
        assert evidence["run_digest"] == expected_run_digest
        assert "capacity" in evidence
        assert "num_bikes_available" in evidence
        assert "num_docks_available" in evidence
        assert "occupancy_ratio" in evidence
        assert "target_ratio" in evidence
        assert "desired_bikes" in evidence
        assert "bike_gap" in evidence
        assert "region_fill_ratio" in evidence
        assert "region_pressure" in evidence


def summarize_plan_rows(rows: list[dict[str, str]]) -> dict:
    totals = {
        "plan_rows": len(rows),
        "pickup_rows": 0,
        "dropoff_rows": 0,
        "pickup_bikes": 0,
        "dropoff_bikes": 0,
    }
    action_counts = {"pickup": 0, "dropoff": 0}
    by_region: dict[str, dict[str, int | str]] = {}
    for row in rows:
        action = row["action"]
        bikes_to_move = int(row["bikes_to_move"])
        action_counts[action] += 1
        totals[f"{action}_rows"] += 1
        totals[f"{action}_bikes"] += bikes_to_move
        region_summary = by_region.setdefault(
            row["region"],
            {
                "region": row["region"],
                "selected_rows": 0,
                "pickup_rows": 0,
                "dropoff_rows": 0,
                "pickup_bikes": 0,
                "dropoff_bikes": 0,
            },
        )
        region_summary["selected_rows"] += 1
        region_summary[f"{action}_rows"] += 1
        region_summary[f"{action}_bikes"] += bikes_to_move
    return {
        "totals": totals,
        "action_counts": action_counts,
        "regions": by_region,
    }


def get_first_present(mapping: dict, *names: str):
    for name in names:
        if name in mapping:
            return mapping[name]
    return None


def assert_summary_contract(summary: dict, rows: list[dict[str, str]], rules: dict, system_information: dict) -> None:
    derived = summarize_plan_rows(rows)

    assert summary["window"]["window_id"] == rules["window_id"]
    assert summary["window"]["system_id"] == system_information["data"]["system_id"]
    assert summary["totals"]["plan_rows"] == derived["totals"]["plan_rows"]
    assert summary["totals"]["pickup_rows"] == derived["totals"]["pickup_rows"]
    assert summary["totals"]["dropoff_rows"] == derived["totals"]["dropoff_rows"]
    assert summary["action_counts"] == derived["action_counts"]
    station_rows = get_first_present(summary["ingest"], "station_rows", "station_information_rows")
    if station_rows is not None:
        assert station_rows == 30
    status_rows = get_first_present(summary["ingest"], "status_rows", "station_status_rows")
    if status_rows is not None:
        assert status_rows == 30
    assert summary["ingest"]["managed_region_count"] == len(rules["managed_region_ids"])
    assert summary["ingest"]["run_digest"] == compute_run_digest(DATA_DIR)

    assert isinstance(summary["regions"], list)
    assert len(summary["regions"]) == len(rules["region_targets"])

    actual_regions = {}
    for region_summary in summary["regions"]:
        region_name = region_summary.get("region") or region_summary.get("region_name")
        assert region_name is not None
        actual_regions[region_name] = region_summary
        selected_rows = get_first_present(
            region_summary,
            "selected_rows",
            "selected_row_count",
            "plan_rows",
        )
        assert selected_rows is not None
        assert selected_rows >= 0
    assert set(actual_regions) == set(derived["regions"])

    for region_name, expected in derived["regions"].items():
        actual = actual_regions[region_name]
        actual_selected_rows = get_first_present(
            actual,
            "selected_rows",
            "selected_row_count",
            "plan_rows",
        )
        assert actual_selected_rows == expected["selected_rows"]
        actual_pickup_rows = get_first_present(actual, "pickup_rows", "pickup_row_count")
        if actual_pickup_rows is not None:
            assert actual_pickup_rows == expected["pickup_rows"]
        elif "action_counts" in actual:
            assert actual["action_counts"]["pickup"] == expected["pickup_rows"]
        else:
            raise AssertionError(f"region summary for {region_name} is missing pickup counts")
        actual_dropoff_rows = get_first_present(actual, "dropoff_rows", "dropoff_row_count")
        if actual_dropoff_rows is not None:
            assert actual_dropoff_rows == expected["dropoff_rows"]
        elif "action_counts" in actual:
            assert actual["action_counts"]["dropoff"] == expected["dropoff_rows"]
        else:
            raise AssertionError(f"region summary for {region_name} is missing dropoff counts")


def count_hash_keys(client: redis.Redis, pattern: str) -> int:
    count = 0
    for key in client.scan_iter(match=pattern):
        if client.type(key) == "hash":
            count += 1
    return count


def count_review_plan_hashes(client: redis.Redis, namespace: str, manifest: dict[str, str]) -> int:
    patterns = {
        f"{namespace}:plan:*",
        f"{namespace}:selected_plan:*",
        f"{namespace}:selected-plan:*",
        f"{namespace}:selected_plan:station:*",
        f"{namespace}:selected-plan:station:*",
    }
    for field_name in (
        "selected_plan_key_prefix",
        "selected_plan_object_prefix",
        "selected_plan_prefix",
        "selected_plan_hash_prefix",
    ):
        prefix = manifest.get(field_name)
        if prefix:
            patterns.add(f"{prefix}*")

    keys: set[str] = set()
    for pattern in patterns:
        for key in client.scan_iter(match=pattern):
            if client.type(key) == "hash":
                keys.add(key)
    return len(keys)


def assert_review_summary_state(client: redis.Redis, namespace: str, manifest: dict[str, str]) -> None:
    summary_key = get_first_present(
        manifest,
        "summary_key",
        "summary_index_key",
    )
    if summary_key and client.exists(summary_key) == 1:
        return
    if client.exists(f"{namespace}:summary") == 1:
        return
    summary_json = manifest.get("summary_json")
    assert summary_json is not None
    assert isinstance(json.loads(summary_json), dict)


def find_set_index_key(client: redis.Redis, namespace: str, needle: str, expected_size: int) -> str | None:
    for key in client.scan_iter(match=f"{namespace}:*"):
        if needle in key and client.type(key) == "set" and client.scard(key) == expected_size:
            return key
    return None


def find_zset_index_key(client: redis.Redis, namespace: str, needle: str, expected_size: int) -> str | None:
    for key in client.scan_iter(match=f"{namespace}:*"):
        if needle in key and client.type(key) == "zset" and client.zcard(key) == expected_size:
            return key
    return None


def load_ordered_index(client: redis.Redis, key: str) -> list[str]:
    key_type = client.type(key)
    if key_type == "zset":
        return client.zrange(key, 0, -1)
    if key_type == "list":
        return client.lrange(key, 0, -1)
    raise AssertionError(f"ordered index key {key} must be a zset or list, got {key_type}")


def test_main_output_contract() -> None:
    clear_namespace()
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    run_job()

    assert PLAN_PATH.exists()
    assert SUMMARY_PATH.exists()

    rows = load_csv(PLAN_PATH)
    assert rows, "plan CSV must contain at least one data row"
    assert list(rows[0].keys()) == [
        "station_id",
        "station_name",
        "region",
        "action",
        "priority_score",
        "bikes_to_move",
        "evidence",
    ]

    summary = load_json(SUMMARY_PATH)
    assert list(summary.keys()) == [
        "window",
        "totals",
        "action_counts",
        "regions",
        "ingest",
        "notes",
    ]
    for row in rows:
        evidence = json.loads(row["evidence"])
        assert "capacity" in evidence
        assert row["action"] in {"pickup", "dropoff"}


def test_main_plan_matches_expected_rows() -> None:
    clear_namespace()
    run_job()
    actual_rows = load_csv(PLAN_PATH)
    expected_rows, _ = expected_outputs(DATA_DIR)
    plan_identity_overlap(actual_rows, expected_rows)
    assert_plan_sorted(actual_rows)
    assert_evidence_contract(actual_rows, compute_run_digest(DATA_DIR))


def test_main_summary_matches_expected() -> None:
    clear_namespace()
    run_job()
    actual_summary = normalize_summary(load_json(SUMMARY_PATH))
    rules = load_json(DATA_DIR / "dispatch_rules.json")
    system_information = load_json(DATA_DIR / "system_information.json")
    actual_rows = load_csv(PLAN_PATH)
    assert_summary_contract(actual_summary, actual_rows, rules, system_information)


def test_main_redis_state_contract() -> None:
    clear_namespace()
    run_job()
    client = redis_client()
    manifest = client.hgetall(f"{NAMESPACE}:manifest")
    assert manifest["window_id"] == "citibike-ops-2026-05-08-am"
    assert int(manifest["station_rows"]) == 30
    assert int(manifest["plan_rows"]) == 10

    assert count_hash_keys(client, f"{NAMESPACE}:station:*") == 30
    assert count_review_plan_hashes(client, NAMESPACE, manifest) == 10
    assert_review_summary_state(client, NAMESPACE, manifest)

    selected_membership_key = get_first_present(
        manifest,
        "selected_membership_key",
        "selected_members_key",
    )
    selected_index_key = get_first_present(
        manifest,
        "selected_index_key",
        "ordered_index_key",
        "ordered_selected_plan_index_key",
        "selected_ordered_index_key",
        "selected_plan_index_key",
    )
    assert selected_membership_key is not None
    assert selected_index_key is not None
    assert client.exists(selected_membership_key) == 1
    assert client.type(selected_membership_key) == "set"
    assert client.exists(selected_index_key) == 1

    rows = load_csv(PLAN_PATH)
    expected_station_ids = [row["station_id"] for row in rows]
    assert client.scard(selected_membership_key) == len(expected_station_ids)
    assert set(client.smembers(selected_membership_key)) == set(expected_station_ids)
    assert load_ordered_index(client, selected_index_key) == expected_station_ids

    for row in rows:
        station_hash = client.hgetall(f"{NAMESPACE}:station:{row['station_id']}")
        membership_flag = get_first_present(
            station_hash,
            "selected_for_plan",
            "selected_plan_member",
            "selected_in_plan",
            "selected_membership",
        )
        assert membership_flag is not None
        assert str(membership_flag) == "1"
        assert station_hash.get("selected_action") == row["action"]
        assert str(station_hash.get("selected_bikes_to_move")) == row["bikes_to_move"]


def test_main_rerun_is_idempotent() -> None:
    clear_namespace()
    run_job()
    first_csv_hash = file_sha256(PLAN_PATH)
    first_summary = normalize_summary(load_json(SUMMARY_PATH))
    client = redis_client()
    first_key_count = len(client.keys(f"{NAMESPACE}:*"))

    run_job()

    assert file_sha256(PLAN_PATH) == first_csv_hash
    assert normalize_summary(load_json(SUMMARY_PATH)) == first_summary
    assert len(client.keys(f"{NAMESPACE}:*")) == first_key_count
    assert int(client.hget(f"{NAMESPACE}:manifest", "plan_rows")) == 10


def test_guardrail_source_inputs_unchanged() -> None:
    for name, expected_hash in EXPECTED_SOURCE_HASHES.items():
        assert file_sha256(DATA_DIR / name) == expected_hash


def test_guardrail_outputs_depend_on_current_inputs() -> None:
    clear_namespace()
    with tempfile.TemporaryDirectory(prefix="redis-task-copy-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        tmp_workspace = tmp_root / "workspace"
        tmp_output = tmp_root / "output"
        shutil.copytree(WORKSPACE, tmp_workspace)

        status_path = tmp_workspace / "data" / "station_status.json"
        payload = load_json(status_path)
        for row in payload["data"]["stations"]:
            if row["station_id"] == "581211b2-4e42-48f2-8a8f-5f968cb1c5df":
                row["num_bikes_available"] = 5
                row["num_docks_available"] = 20
            if row["station_id"] == "bd6f422b-d7ae-4d7e-9261-653fdd8e6888":
                row["num_bikes_available"] = 12
                row["num_docks_available"] = 10
        status_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

        run_job(workspace=tmp_workspace, output_dir=tmp_output)
        changed_rows = load_csv(tmp_output / "rebalance_plan.csv")
        baseline_rows = load_csv(PLAN_PATH) if PLAN_PATH.exists() else expected_outputs(DATA_DIR)[0]
        assert changed_rows != baseline_rows
