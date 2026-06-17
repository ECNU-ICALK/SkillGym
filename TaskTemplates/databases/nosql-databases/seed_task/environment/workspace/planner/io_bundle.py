from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path


WORKSPACE_DIR = Path(os.environ.get("TASK_WORKSPACE", "/app/workspace"))
DATA_DIR = WORKSPACE_DIR / "data"


@dataclass(frozen=True)
class InputBundle:
    station_information: dict
    station_status: dict
    system_regions: dict
    system_information: dict
    dispatch_rules: dict


def load_bundle(data_dir: Path = DATA_DIR) -> InputBundle:
    return InputBundle(
        station_information=_load_json(data_dir / "station_information.json"),
        station_status=_load_json(data_dir / "station_status.json"),
        system_regions=_load_json(data_dir / "system_regions.json"),
        system_information=_load_json(data_dir / "system_information.json"),
        dispatch_rules=_load_json(data_dir / "dispatch_rules.json"),
    )


def compute_run_digest(data_dir: Path = DATA_DIR) -> str:
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


def build_station_rows(bundle: InputBundle) -> list[dict]:
    status_by_id = {
        row["station_id"]: row for row in bundle.station_status["data"]["stations"]
    }
    region_name_by_id = {
        row["region_id"]: row["name"] for row in bundle.system_regions["data"]["regions"]
    }
    rows: list[dict] = []
    for station in bundle.station_information["data"]["stations"]:
        status = status_by_id[station["station_id"]]
        merged = {**station, **status}
        merged["region_name"] = region_name_by_id.get(station["region_id"], station["region_id"])
        rows.append(merged)
    return rows


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
