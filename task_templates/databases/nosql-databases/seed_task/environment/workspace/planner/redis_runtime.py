from __future__ import annotations

import json

import redis


def connect() -> redis.Redis:
    return redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)


def write_runtime_state(client: redis.Redis, namespace: str, stations: list[dict], plan_rows: list[dict], summary: dict, run_digest: str) -> None:
    manifest_key = f"{namespace}:manifest"
    client.hset(
        manifest_key,
        mapping={
            "run_digest": run_digest,
            "station_rows": len(stations),
            "plan_rows": len(plan_rows),
            "window_id": summary["window"]["window_id"],
        },
    )

    for row in stations:
        client.hset(
            f"{namespace}:station:{row['station_id']}",
            mapping={
                "station_name": row["name"],
                "region_id": row["region_id"],
                "region_name": row["region_name"],
                "capacity": row["capacity"],
                "num_bikes_available": row["num_bikes_available"],
                "num_docks_available": row["num_docks_available"],
            },
        )

    for row in plan_rows:
        client.hset(
            f"{namespace}:plan:{row['station_id']}",
            mapping={
                "station_name": row["station_name"],
                "region": row["region"],
                "action": row["action"],
                "priority_score": row["priority_score"],
                "bikes_to_move": row["bikes_to_move"],
                "evidence": json.dumps(row["evidence"], separators=(",", ":")),
            },
        )
