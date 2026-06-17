from __future__ import annotations

import json
from datetime import UTC, datetime
from math import floor


def build_plan(stations: list[dict], rules: dict, run_digest: str, system_information: dict) -> tuple[list[dict], dict]:
    managed_regions = set(rules["managed_region_ids"])
    excluded_station_ids = set(rules["excluded_station_ids"])
    low_fill_ratio = float(rules["low_fill_ratio"])
    high_fill_ratio = float(rules["high_fill_ratio"])
    min_capacity = int(rules["min_capacity"])
    max_move_per_station = int(rules["max_move_per_station"])
    region_limits = rules["region_action_limits"]
    region_targets = rules["region_targets"]
    priority_weights = rules["priority_weights"]

    eligible_rows: list[dict] = []
    excluded_count = 0
    for row in stations:
        if row["station_id"] in excluded_station_ids:
            excluded_count += 1
            continue
        if row["region_id"] not in managed_regions:
            continue
        if int(row.get("capacity") or 0) < min_capacity:
            continue
        if not (
            row.get("is_installed") == 1
            and row.get("is_renting") == 1
            and row.get("is_returning") == 1
        ):
            continue
        eligible_rows.append(row)

    region_context = _build_region_context(eligible_rows, region_targets, region_limits)
    candidates_by_region: dict[str, list[dict]] = {region_id: [] for region_id in managed_regions}
    eligible_count = 0
    over_capacity_count = 0

    for row in eligible_rows:
        eligible_count += 1
        capacity = int(row["capacity"])
        bikes = int(row["num_bikes_available"])
        docks = int(row["num_docks_available"])
        occupancy_ratio = bikes / capacity
        region_id = row["region_id"]
        target_ratio = float(region_targets[region_id])
        if bikes > capacity:
            over_capacity_count += 1

        if occupancy_ratio <= low_fill_ratio:
            action = "dropoff"
        elif occupancy_ratio >= high_fill_ratio:
            action = "pickup"
        else:
            continue

        desired_bikes = max(1, _round_half_up(target_ratio * capacity))
        bike_gap = abs(bikes - desired_bikes)
        movement_capacity = bikes if action == "pickup" else docks
        bikes_to_move = min(max_move_per_station, max(1, bike_gap), movement_capacity)
        if bikes_to_move <= 0:
            continue

        region_fill_ratio = region_context[region_id]["fill_ratio"]
        region_pressure = _directional_region_pressure(
            action=action,
            region_fill_ratio=region_fill_ratio,
            target_ratio=target_ratio,
        )
        zero_side_bonus = _zero_side_bonus(
            action=action,
            bikes=bikes,
            docks=docks,
            weight=float(priority_weights["zero_side_bonus"]),
        )
        priority_score = round(
            bike_gap * float(priority_weights["bike_gap_weight"])
            + capacity * float(priority_weights["capacity_weight"])
            + region_pressure * float(priority_weights["region_pressure_weight"])
            + zero_side_bonus,
            2,
        )

        candidates_by_region[region_id].append(
            {
                "station_id": row["station_id"],
                "station_name": row["name"],
                "region": row["region_name"],
                "region_id": region_id,
                "action": action,
                "priority_score": priority_score,
                "bikes_to_move": bikes_to_move,
                "evidence": {
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
                    "priority_weights": priority_weights,
                    "thresholds": {
                        "low_fill_ratio": low_fill_ratio,
                        "high_fill_ratio": high_fill_ratio,
                        "min_capacity": min_capacity,
                        "max_move_per_station": max_move_per_station,
                    },
                    "operational_flags": {
                        "is_installed": row["is_installed"],
                        "is_renting": row["is_renting"],
                        "is_returning": row["is_returning"],
                    },
                    "last_reported": row["last_reported"],
                    "run_digest": run_digest,
                },
            }
        )

    candidates: list[dict] = []
    for region_id, region_candidates in candidates_by_region.items():
        region_candidates.sort(
            key=lambda row: (-row["priority_score"], row["station_name"], row["station_id"])
        )
        limit = int(region_limits.get(region_id, 0))
        for rank, candidate in enumerate(region_candidates, start=1):
            candidate["evidence"]["region_rank"] = rank
            candidate["evidence"]["region_limit"] = limit
        candidates.extend(region_candidates)

    selected: list[dict] = []
    for region_id in sorted(candidates_by_region):
        selected.extend(candidates_by_region[region_id][: int(region_limits.get(region_id, 0))])
    selected.sort(
        key=lambda row: (-row["priority_score"], row["region"], row["station_name"], row["station_id"])
    )

    action_counts = {"pickup": 0, "dropoff": 0}
    bikes_by_action = {"pickup": 0, "dropoff": 0}
    for row in selected:
        action_counts[row["action"]] += 1
        bikes_by_action[row["action"]] += int(row["bikes_to_move"])

    region_summaries = _build_region_summaries(
        selected=selected,
        candidates_by_region=candidates_by_region,
        region_context=region_context,
        region_limits=region_limits,
        region_targets=region_targets,
    )

    summary = {
        "window": {
            "window_id": rules["window_id"],
            "system_id": system_information["data"]["system_id"],
            "system_name": system_information["data"]["name"],
            "timezone": system_information["data"]["timezone"],
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "totals": {
            "eligible_stations": eligible_count,
            "candidate_stations": len(candidates),
            "plan_rows": len(selected),
            "pickup_rows": action_counts["pickup"],
            "dropoff_rows": action_counts["dropoff"],
            "pickup_bikes": bikes_by_action["pickup"],
            "dropoff_bikes": bikes_by_action["dropoff"],
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

    return selected, summary


def encode_evidence(plan_rows: list[dict]) -> list[dict]:
    encoded: list[dict] = []
    for row in plan_rows:
        encoded.append({**row, "evidence": json.dumps(row["evidence"], separators=(",", ":"))})
    return encoded


def _build_region_context(eligible_rows: list[dict], region_targets: dict, region_limits: dict) -> dict[str, dict]:
    context: dict[str, dict] = {}
    for region_id, target_ratio in region_targets.items():
        region_rows = [row for row in eligible_rows if row["region_id"] == region_id]
        capacity_total = sum(int(row["capacity"]) for row in region_rows)
        bikes_total = sum(int(row["num_bikes_available"]) for row in region_rows)
        fill_ratio = (bikes_total / capacity_total) if capacity_total else 0.0
        context[region_id] = {
            "region_id": region_id,
            "region_name": region_rows[0]["region_name"] if region_rows else region_id,
            "eligible_stations": len(region_rows),
            "capacity_total": capacity_total,
            "bikes_total": bikes_total,
            "fill_ratio": fill_ratio,
            "target_ratio": float(target_ratio),
            "action_limit": int(region_limits.get(region_id, 0)),
        }
    return context


def _directional_region_pressure(action: str, region_fill_ratio: float, target_ratio: float) -> float:
    if action == "pickup":
        return max(0.0, region_fill_ratio - target_ratio)
    return max(0.0, target_ratio - region_fill_ratio)


def _zero_side_bonus(action: str, bikes: int, docks: int, weight: float) -> float:
    if action == "pickup" and docks == 0:
        return weight
    if action == "dropoff" and bikes == 0:
        return weight
    return 0.0


def _round_half_up(value: float) -> int:
    return floor(value + 0.5)


def _build_region_summaries(
    selected: list[dict],
    candidates_by_region: dict[str, list[dict]],
    region_context: dict[str, dict],
    region_limits: dict,
    region_targets: dict,
) -> list[dict]:
    selected_by_region: dict[str, list[dict]] = {}
    for row in selected:
        selected_by_region.setdefault(row["region_id"], []).append(row)

    summaries: list[dict] = []
    for region_id in sorted(region_targets):
        region_rows = selected_by_region.get(region_id, [])
        pickup_rows = [row for row in region_rows if row["action"] == "pickup"]
        dropoff_rows = [row for row in region_rows if row["action"] == "dropoff"]
        priorities = [float(row["priority_score"]) for row in region_rows]
        context = region_context[region_id]
        summaries.append(
            {
                "region_id": region_id,
                "region": context["region_name"],
                "selected_rows": len(region_rows),
                "candidate_rows": len(candidates_by_region.get(region_id, [])),
                "action_limit": int(region_limits.get(region_id, 0)),
                "pickup_rows": len(pickup_rows),
                "dropoff_rows": len(dropoff_rows),
                "pickup_bikes": sum(int(row["bikes_to_move"]) for row in pickup_rows),
                "dropoff_bikes": sum(int(row["bikes_to_move"]) for row in dropoff_rows),
                "avg_priority_score": round(sum(priorities) / len(priorities), 2) if priorities else 0.0,
                "region_fill_ratio": round(float(context["fill_ratio"]), 4),
                "target_ratio": round(float(context["target_ratio"]), 4),
                "eligible_stations": int(context["eligible_stations"]),
            }
        )
    return summaries
