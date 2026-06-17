from __future__ import annotations

import csv
import json
import os
import subprocess
import urllib.request
from pathlib import Path


ACCESS_LOG = Path(os.environ.get("HF_PLANNER_ACCESS_LOG", "/var/log/health-fitness-planner/access.log"))
DATA_ROOT = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
SERVICE_ROOT = Path(os.environ.get("HF_PLANNER_SERVICE_ROOT", "/services/health-fitness-planner"))
SEED_ROOT = Path(os.environ.get("HF_PLANNER_SEED_DIR", "/opt/health-fitness-planner/seed"))
DATA_HASH_PATH = Path(os.environ.get("HF_PLANNER_DATA_HASH", "/opt/health-fitness-data.sha256"))
SERVICE_HASH_PATH = Path(os.environ.get("HF_PLANNER_SERVICE_HASH", "/opt/health-fitness-service.sha256"))
SEED_HASH_PATH = Path(os.environ.get("HF_PLANNER_SEED_HASH", "/opt/health-fitness-seed.sha256"))
HEALTH_URL = os.environ.get("HF_PLANNER_HEALTH_URL", "http://127.0.0.1:8137/health")
PRE_VERIFIER_LOG = ACCESS_LOG.read_text(encoding="utf-8") if ACCESS_LOG.exists() else ""


def parse_pre_verifier_records() -> list[dict]:
    records = []
    for line in PRE_VERIFIER_LOG.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("client", "").startswith("verifier-"):
            continue
        records.append(record)
    return records


def load_workout_rows() -> list[dict]:
    with (OUTPUT_ROOT / "workout_plan.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_solver_used_live_planning_services_before_verifier() -> None:
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier service traffic was recorded"
    policy_calls = [record for record in records if record["path"] == "/api/policy/current"]
    exercise_calls = [record for record in records if record["path"] == "/api/exercises"]
    food_calls = [record for record in records if record["path"] == "/api/foods"]
    assert policy_calls, "Solver did not query the live policy endpoint"
    assert exercise_calls, "Solver did not query the live exercise endpoint"
    assert food_calls, "Solver did not query the live food endpoint"
    assert any(record.get("query", {}).get("cursor") for record in exercise_calls), "Solver did not follow exercise cursor pagination"
    assert any(record.get("query", {}).get("cursor") for record in food_calls), "Solver did not follow food cursor pagination"


def test_plan_uses_live_only_movements() -> None:
    rows = load_workout_rows()
    chosen_ids = {row["exercise_id"] for row in rows}
    required_live_only = {"EX011", "EX013"}
    assert required_live_only.issubset(chosen_ids), "Workout plan did not include the live-only movements required by the current catalog"
    assert "EX003" in chosen_ids, "Workout plan missed the required vertical-pull movement"


def test_inputs_and_hidden_assets_were_not_modified() -> None:
    current_data = subprocess.check_output(
        f"find {DATA_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_data = DATA_HASH_PATH.read_text(encoding="utf-8")
    assert current_data == expected_data, "Input data under /root/data was modified"

    current_service = subprocess.check_output(
        f"find {SERVICE_ROOT} -type f -name '*.py' -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_service = SERVICE_HASH_PATH.read_text(encoding="utf-8")
    assert current_service == expected_service, "Hidden planning service files were modified"

    current_seed = subprocess.check_output(
        f"find {SEED_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_seed = SEED_HASH_PATH.read_text(encoding="utf-8")
    assert current_seed == expected_seed, "Hidden seed data was modified"


def test_live_services_still_healthy() -> None:
    with urllib.request.urlopen(HEALTH_URL, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "health-fitness-planner"
