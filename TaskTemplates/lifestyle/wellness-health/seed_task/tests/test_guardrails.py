from __future__ import annotations

import csv
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


ACCESS_LOG = Path(os.environ.get("WELLNESS_PLANNER_ACCESS_LOG", "/var/log/wellness-planner/access.log"))
DATA_ROOT = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
DATA_HASH_PATH = Path(os.environ.get("WELLNESS_PLANNER_DATA_HASH", "/opt/wellness-data.sha256"))
HEALTH_URL = os.environ.get("WELLNESS_PLANNER_HEALTH_URL", "http://127.0.0.1:8147/health")
HIDDEN_POLICY_URL = os.environ.get("WELLNESS_PLANNER_HIDDEN_POLICY_URL", "http://127.0.0.1:8147/api/policy/hidden")
SERVICE_ROOT = Path(os.environ.get("WELLNESS_PLANNER_SERVICE_ROOT", "/services/wellness-planner"))
SEED_ROOT = Path(os.environ.get("WELLNESS_PLANNER_SEED_DIR", "/opt/wellness-planner/seed"))
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


def load_schedule_rows() -> list[dict]:
    with (OUTPUT_ROOT / "activity_schedule.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_solver_used_live_planning_service_before_verifier() -> None:
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier service traffic was recorded"
    manifest_calls = [record for record in records if record["path"] == "/api/manifest"]
    hourly_calls = [record for record in records if record["path"] == "/api/conditions/hourly"]
    assert manifest_calls, "Solver did not query the service manifest"
    assert hourly_calls, "Solver did not query the live hourly conditions endpoint"
    seen_dates = {record.get("query", {}).get("date", [""])[0] for record in hourly_calls}
    assert seen_dates >= {"2026-05-04", "2026-05-05", "2026-05-06"}, "Solver did not inspect the full planning window"


def test_solver_did_not_leave_action_level_failures() -> None:
    rows = load_schedule_rows()
    by_id = {row["session_id"]: row for row in rows}
    assert by_id["S002"]["decision"] == "move_indoors", "S002 still needs an indoor adjustment"
    assert by_id["S003"]["decision"] == "move_indoors", "S003 still needs an indoor adjustment"
    assert by_id["S004"]["decision"] == "move_indoors", "S004 still needs an indoor adjustment"
    assert by_id["S005"]["final_start_local"] == "2026-05-06T09:00:00-05:00", "S005 still needs a same-day time adjustment"
    assert by_id["S005"]["decision"] in {"reschedule", "move_to_lower_exposure"}, "S005 still needs a lower-exposure time adjustment"


def test_inputs_and_hidden_assets_were_not_modified() -> None:
    current_data = subprocess.check_output(
        f"find {DATA_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_data = DATA_HASH_PATH.read_text(encoding="utf-8")
    assert current_data == expected_data, "Input data under /root/data was modified"


def test_live_service_still_healthy() -> None:
    with urllib.request.urlopen(HEALTH_URL, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "wellness-planner"


def test_hidden_policy_and_service_files_are_not_exposed() -> None:
    try:
        urllib.request.urlopen(HIDDEN_POLICY_URL, timeout=10)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("Hidden policy endpoint is still exposed")

    assert not SERVICE_ROOT.exists(), "Hidden service source is still exposed in the runtime"
    assert not SEED_ROOT.exists(), "Hidden seed data is still exposed in the runtime"
