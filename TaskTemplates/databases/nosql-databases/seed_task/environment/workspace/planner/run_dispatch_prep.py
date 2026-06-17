from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from .engine import build_plan, encode_evidence
from .io_bundle import build_station_rows, compute_run_digest, load_bundle
from .redis_runtime import connect, write_runtime_state


OUTPUT_DIR = Path(os.environ.get("TASK_OUTPUT_DIR", "/app/output"))
PLAN_PATH = OUTPUT_DIR / "rebalance_plan.csv"
SUMMARY_PATH = OUTPUT_DIR / "network_summary.json"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    bundle = load_bundle()
    stations = build_station_rows(bundle)
    run_digest = compute_run_digest()
    plan_rows, summary = build_plan(
        stations=stations,
        rules=bundle.dispatch_rules,
        run_digest=run_digest,
        system_information=bundle.system_information,
    )

    encoded_rows = encode_evidence(plan_rows)
    _write_csv(encoded_rows)
    _write_json(summary)

    client = connect()
    write_runtime_state(
        client=client,
        namespace=bundle.dispatch_rules["redis_namespace"],
        stations=stations,
        plan_rows=plan_rows,
        summary=summary,
        run_digest=run_digest,
    )


def _write_csv(rows: list[dict]) -> None:
    fieldnames = [
        "station_id",
        "station_name",
        "region",
        "action",
        "priority_score",
        "bikes_to_move",
        "evidence",
    ]
    with PLAN_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        normalized_rows = []
        for row in rows:
            normalized_rows.append(
                {name: row[name] for name in fieldnames}
            )
            normalized_rows[-1]["priority_score"] = f"{float(row['priority_score']):.2f}"
            normalized_rows[-1]["bikes_to_move"] = str(int(row["bikes_to_move"]))
        writer.writerows(normalized_rows)


def _write_json(payload: dict) -> None:
    SUMMARY_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
