from __future__ import annotations

import csv
import json
import os
import subprocess
import urllib.request
from pathlib import Path


ACCESS_LOG = Path(os.environ.get("REAUCTION_ACCESS_LOG", "/var/log/real-estate-legal-audit/access.log"))
DATA_ROOT = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
SERVICE_ROOT = Path(os.environ.get("REAUCTION_SERVICE_ROOT", "/services/real-estate-legal-audit"))
SEED_ROOT = Path(os.environ.get("REAUCTION_SEED_DIR", "/opt/real-estate-legal-audit/seed"))
DATA_HASH_PATH = Path(os.environ.get("REAUCTION_DATA_HASH", "/opt/real-estate-legal-data.sha256"))
SERVICE_HASH_PATH = Path(os.environ.get("REAUCTION_SERVICE_HASH", "/opt/real-estate-legal-service.sha256"))
SEED_HASH_PATH = Path(os.environ.get("REAUCTION_SEED_HASH", "/opt/real-estate-legal-seed.sha256"))
HEALTH_URL = os.environ.get("REAUCTION_HEALTH_URL", "http://127.0.0.1:8146/health")
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


def load_risk_rows() -> list[dict]:
    with (OUTPUT_ROOT / "risk_register.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_solver_used_local_authority_service_before_verifier() -> None:
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier service traffic was recorded"
    assert any(record["path"] == "/api/manifest" for record in records), "Solver did not query the manifest endpoint"
    assert any(record["path"] == "/api/asset/current" for record in records), "Solver did not query the current asset endpoint"
    assert any(record["path"] == "/api/cost-model/current" for record in records), "Solver did not query the current cost model endpoint"
    risk_calls = [record for record in records if record["path"] == "/api/risk-signals"]
    assert risk_calls, "Solver did not query the risk-signals endpoint"
    assert any(record.get("query", {}).get("cursor") for record in risk_calls), "Solver did not follow cursor pagination on the risk-signals endpoint"


def test_submission_contains_live_only_updates() -> None:
    notice = json.loads((OUTPUT_ROOT / "notice_extract.json").read_text(encoding="utf-8"))
    assert abs(float(notice["second_min_bid_brl"]) - 125400.0) <= 0.01, "Submission kept the stale second-auction bid"
    assert notice["fgts_allowed"] is True
    assert notice["financing_allowed"] is True

    rows = load_risk_rows()
    by_code = {row["risk_code"]: row for row in rows}
    assert by_code["document_regularization"]["risk_level"] == "high"
    assert by_code["municipal_tax_basis"]["risk_level"] == "medium"
    assert "greater of transaction value and municipal reference value" in by_code["municipal_tax_basis"]["summary"].lower()


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
    assert current_service == expected_service, "Hidden authority service files were modified"

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
    assert payload["service"] == "real-estate-legal-audit"
