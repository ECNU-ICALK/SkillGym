from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path


ACCESS_LOG = Path(os.environ.get("BIOINFO_SCANPY_ACCESS_LOG", "/var/log/bioinfo-scanpy/access.log"))
DATA_ROOT = Path(os.environ.get("DATA_DIR", "/root/data"))
SERVICE_ROOT = Path(os.environ.get("BIOINFO_SCANPY_SERVICE_ROOT", "/services/bioinfo-scanpy"))
SEED_ROOT = Path(os.environ.get("BIOINFO_SCANPY_SEED_DIR", "/opt/bioinfo-scanpy/seed"))
DATA_HASH_PATH = Path(os.environ.get("BIOINFO_SCANPY_DATA_HASH", "/opt/bioinfo-scanpy-data.sha256"))
SERVICE_HASH_PATH = Path(os.environ.get("BIOINFO_SCANPY_SERVICE_HASH", "/opt/bioinfo-scanpy-service.sha256"))
SEED_HASH_PATH = Path(os.environ.get("BIOINFO_SCANPY_SEED_HASH", "/opt/bioinfo-scanpy-seed.sha256"))
HEALTH_URL = os.environ.get("BIOINFO_SCANPY_HEALTH_URL", "http://127.0.0.1:8143/health")
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


def test_solver_used_current_policy_service_before_verifier() -> None:
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier service traffic was recorded"
    policy_calls = [record for record in records if record["path"] == "/api/analysis-policy/current"]
    marker_calls = [record for record in records if record["path"] == "/api/marker-panel/current"]
    assert policy_calls, "Solver did not query the current analysis policy endpoint"
    assert marker_calls, "Solver did not query the current marker panel endpoint"


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
    assert current_service == expected_service, "Hidden service files were modified"

    current_seed = subprocess.check_output(
        f"find {SEED_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_seed = SEED_HASH_PATH.read_text(encoding="utf-8")
    assert current_seed == expected_seed, "Hidden seed data was modified"


def test_live_service_still_healthy() -> None:
    with urllib.request.urlopen(HEALTH_URL, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "bioinfo-scanpy"
