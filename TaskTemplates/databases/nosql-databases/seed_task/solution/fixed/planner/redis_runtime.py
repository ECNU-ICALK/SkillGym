from __future__ import annotations

import json
from itertools import islice

import redis


def connect() -> redis.Redis:
    return redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)


def write_runtime_state(
    client: redis.Redis,
    namespace: str,
    stations: list[dict],
    plan_rows: list[dict],
    summary: dict,
    run_digest: str,
) -> None:
    _clear_namespace_state(client=client, namespace=namespace)

    manifest_key = f"{namespace}:manifest"
    stations_index_key = f"{namespace}:stations"
    plan_index_key = f"{namespace}:plan_stations"
    selected_membership_key = f"{namespace}:selected_plan"
    selected_index_key = f"{namespace}:selected_plan_index"
    summary_key = f"{namespace}:summary"
    selected_by_station_id = {row["station_id"]: row for row in plan_rows}

    pipeline = client.pipeline(transaction=True)
    pipeline.hset(
        manifest_key,
        mapping={
            "run_digest": run_digest,
            "station_rows": len(stations),
            "plan_rows": len(plan_rows),
            "window_id": summary["window"]["window_id"],
            "generated_at": summary["window"]["generated_at"],
            "selected_membership_key": selected_membership_key,
            "selected_index_key": selected_index_key,
        },
    )
    pipeline.set(summary_key, json.dumps(summary, separators=(",", ":")))

    for row in stations:
        station_key = f"{namespace}:station:{row['station_id']}"
        selected_row = selected_by_station_id.get(row["station_id"])
        pipeline.sadd(stations_index_key, row["station_id"])
        pipeline.hset(
            station_key,
            mapping={
                "station_id": row["station_id"],
                "station_name": row["name"],
                "region_id": row["region_id"],
                "region_name": row["region_name"],
                "capacity": row["capacity"],
                "num_bikes_available": row["num_bikes_available"],
                "num_docks_available": row["num_docks_available"],
                "is_installed": row["is_installed"],
                "is_renting": row["is_renting"],
                "is_returning": row["is_returning"],
                "last_reported": row["last_reported"],
                "selected_for_plan": "1" if selected_row else "0",
                "selected_action": selected_row["action"] if selected_row else "",
                "selected_priority_score": selected_row["priority_score"] if selected_row else "",
                "selected_bikes_to_move": selected_row["bikes_to_move"] if selected_row else "",
            },
        )

    for selected_rank, row in enumerate(plan_rows, start=1):
        plan_key = f"{namespace}:plan:{row['station_id']}"
        pipeline.sadd(plan_index_key, row["station_id"])
        pipeline.sadd(selected_membership_key, row["station_id"])
        pipeline.zadd(selected_index_key, {row["station_id"]: float(selected_rank)})
        pipeline.hset(
            plan_key,
            mapping={
                "station_id": row["station_id"],
                "station_name": row["station_name"],
                "region_id": row["region_id"],
                "region": row["region"],
                "action": row["action"],
                "priority_score": row["priority_score"],
                "bikes_to_move": row["bikes_to_move"],
                "selected_rank": selected_rank,
                "evidence": json.dumps(row["evidence"], separators=(",", ":")),
            },
        )

    pipeline.execute()


def _clear_namespace_state(client: redis.Redis, namespace: str) -> None:
    patterns = [
        f"{namespace}:manifest",
        f"{namespace}:summary",
        f"{namespace}:stations",
        f"{namespace}:plan_stations",
        f"{namespace}:selected_plan",
        f"{namespace}:selected_plan_index",
        f"{namespace}:station:*",
        f"{namespace}:plan:*",
    ]
    for pattern in patterns:
        _scan_delete(client, pattern)


def _scan_delete(client: redis.Redis, pattern: str, batch_size: int = 200) -> None:
    iterator = client.scan_iter(match=pattern, count=batch_size)
    while True:
        batch = list(islice(iterator, batch_size))
        if not batch:
            return
        client.delete(*batch)
