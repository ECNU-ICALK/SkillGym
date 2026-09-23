#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

PGHOST = "/tmp/sql-databases-pg"
PGPORT = "55433"
PGUSER = "postgres"
DB_NAME = "airport_ops_task"


def ensure_local_postgres() -> None:
    subprocess.run(
        ["/root/workspace/bin/init_airport_ops.sh"],
        check=True,
        capture_output=True,
        text=True,
    )


def load_contract(data_root: Path) -> dict:
    return json.loads((data_root / "analysis_contract.json").read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    data_root = Path(args.data)
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    ensure_local_postgres()
    contract = load_contract(data_root)
    snapshots = ", ".join(contract["rolling_window"]["snapshot_dates"])
    raise SystemExit(
        "Pipeline not implemented yet. Use the local PostgreSQL database, the input data, "
        "and analysis_contract.json to build the indexed rolling demand mart deliverables in /root/output, "
        f"including the configured snapshot dates ({snapshots})."
    )


if __name__ == "__main__":
    main()
