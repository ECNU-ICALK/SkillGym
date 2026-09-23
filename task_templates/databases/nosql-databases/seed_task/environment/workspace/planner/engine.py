from __future__ import annotations

import json
from datetime import UTC, datetime


def build_plan(stations: list[dict], rules: dict, run_digest: str, system_information: dict) -> tuple[list[dict], dict]:
    managed_regions = set(rules["managed_region_ids"])
    low_fill_ratio = float(rules["low_fill_ratio"])
    high_fill_ratio = float(rules["high_fill_ratio"])
    min_capacity = int(rules["min_capacity"])
    max_move_per_station = int(rules["max_move_per_station"])
    region_limits = rules["region_action_limits"]
    region_targets = rules["region_targets"]

    candidates: list[dict] = []
    eligible_count = 0
    for row in stations:
        if row["region_id"] not in managed_regions:
            continue
        if int(row.get("capacity") or 0) < min_capacity:
            continue
        if not (row.get("is_installed") == 1 and row.get("is_renting") == 1 and row.get("is_returning") == 1):
            continue
        eligible_count += 1
        capacity = int(row["capacity"])
        bikes = int(row["num_bikes_available"])
        docks = int(row["num_docks_available"])
        occupancy_ratio = bikes / capacity
        target_ratio = float(region_targets[row["region_id"]])
        if occupancy_ratio <= low_fill_ratio:
            action = "dropoff"
        elif occupancy_ratio >= high_fill_ratio:
            action = "pickup"
        else:
            continue
        # Placeholder calculations only. The production contract in instruction.md
        # defines the required rounding, movement, ranking, and summary behavior.
        desired_bikes = max(1, round(target_ratio * capacity))
        bike_gap = abs(bikes - desired_bikes)
        movement_capacity = bikes if action == "pickup" else docks
        bikes_to_move = min(max_move_per_station, max(1, bike_gap), movement_capacity)
        priority_score = round(bike_gap + capacity, 2)
        candidates.append(
            {
                "station_id": row["station_id"],
                "station_name": row["name"],
                "region": row["region_name"],
                "region_id": row["region_id"],
                "action": action,
                "priority_score": priority_score,
                "bikes_to_move": bikes_to_move,
                "evidence": {
                    "capacity": capacity,
                    "num_bikes_available": bikes,
                    "num_docks_available": docks,
                    "occupancy_ratio": round(occupancy_ratio, 4),
                    "target_ratio": target_ratio,
                    "run_digest": run_digest,
                },
            }
        )

    # Starter behavior: picks the strongest rows globally and ignores exclusions and per-region scoring details.
    candidates.sort(key=lambda row: (-row["priority_score"], row["station_name"], row["station_id"]))
    overall_limit = sum(int(value) for value in region_limits.values())
    selected = candidates[:overall_limit]

    action_counts = {"pickup": 0, "dropoff": 0}
    for row in selected:
        action_counts[row["action"]] += 1

    summary = {
        "window": {
            "window_id": rules["window_id"],
            "system_id": system_information["data"]["system_id"],
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "totals": {
            "eligible_stations": eligible_count,
            "candidate_stations": len(candidates),
            "plan_rows": len(selected),
            "pickup_rows": action_counts["pickup"],
            "dropoff_rows": action_counts["dropoff"],
        },
        "action_counts": action_counts,
        "regions": [],
        "ingest": {
            "run_digest": run_digest,
            "station_rows": len(stations),
            "status_rows": len(stations),
            "managed_region_count": len(managed_regions),
        },
        "notes": [
            "Starter implementation completed the basic candidate scan.",
            "Redis-backed ranking and per-region plan shaping may still need work.",
        ],
    }

    return selected, summary


def encode_evidence(plan_rows: list[dict]) -> list[dict]:
    encoded: list[dict] = []
    for row in plan_rows:
        encoded.append({**row, "evidence": json.dumps(row["evidence"], separators=(",", ":"))})
    return encoded
