from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path


ACCESS_LOG = Path(os.environ.get("REVOPS_ACCESS_LOG", "/var/log/revops/access.log"))
DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/root/output"))
SERVICE_ROOT = Path(os.environ.get("TASK_SERVICE_ROOT", "/services/revops"))
DATA_HASH_PATH = Path(os.environ.get("TASK_DATA_HASH_PATH", "/opt/revops-data.sha256"))
SERVICE_HASH_PATH = Path(os.environ.get("TASK_SERVICE_HASH_PATH", "/opt/revops-service.sha256"))
SKILL_HASH_PATH = Path(os.environ.get("TASK_SKILL_HASH_PATH", "/opt/revops-skills.sha256"))
SKILL_ROOT = Path(os.environ.get("TASK_SKILL_ROOT", "/root/.codex/skills"))
HEALTH_URL = os.environ.get("TASK_HEALTH_URL", "http://127.0.0.1:8144/health")
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
        client = record.get("client", "")
        if client.startswith("verifier-") or client == "verifier-main":
            continue
        records.append(record)
    return records


def test_solver_used_live_revops_service_before_verifier() -> None:
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier revops traffic was recorded"
    assert any(record["path"] == "/api/manifest" for record in records), "Solver did not query the manifest endpoint"

    cohort_calls = [record for record in records if record["path"] == "/api/cohort"]
    assert len(cohort_calls) >= 3, "Solver did not fetch all cohort pages"
    seen_cursors = {tuple(record.get("query", {}).get("cursor", [])) for record in cohort_calls}
    assert tuple() in seen_cursors, "Solver did not fetch the first cohort page"
    assert ("cursor-2",) in seen_cursors and ("cursor-3",) in seen_cursors, "Solver did not follow cohort cursor pagination"

    detail_ids = set()
    preview_ids = set()
    dunning_ids = set()
    for record in records:
        path = record["path"]
        if path.startswith("/api/accounts/") and path.endswith("/renewal-preview"):
            preview_ids.add(path.split("/")[3])
        elif path.startswith("/api/accounts/") and path.endswith("/dunning-events"):
            dunning_ids.add(path.split("/")[3])
        elif path.startswith("/api/accounts/"):
            detail_ids.add(path.rsplit("/", 1)[-1])
    expected_ids = {"ACC-101", "ACC-102", "ACC-103", "ACC-104", "ACC-105", "ACC-106", "ACC-107", "ACC-108"}
    assert expected_ids.issubset(detail_ids), "Solver did not fetch account details for every live account"
    assert expected_ids.issubset(preview_ids), "Solver did not fetch renewal previews for every live account"
    assert expected_ids.issubset(dunning_ids), "Solver did not fetch dunning events for every live account"


def test_inputs_hidden_service_and_skill_were_not_modified() -> None:
    current_data = subprocess.check_output(
        f"find {DATA_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    assert current_data == DATA_HASH_PATH.read_text(encoding="utf-8"), "Input data under /root/data was modified"

    current_service = subprocess.check_output(
        f"find {SERVICE_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    assert current_service == SERVICE_HASH_PATH.read_text(encoding="utf-8"), "Hidden revops service files were modified"

    if SKILL_HASH_PATH.exists() and SKILL_ROOT.exists():
        current_skill = subprocess.check_output(
            f"find {SKILL_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
            shell=True,
            text=True,
        )
        assert current_skill == SKILL_HASH_PATH.read_text(encoding="utf-8"), "Installed skill files were modified"


def test_live_service_still_healthy() -> None:
    with urllib.request.urlopen(HEALTH_URL, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "revops"


def test_live_only_accounts_were_not_missed() -> None:
    text = (OUTPUT_ROOT / "renewal_worklist.csv").read_text(encoding="utf-8")
    assert "ACC-107" in text, "Live-only account ACC-107 is missing, suggesting stale export dependence"
    assert "ACC-108" in text, "Live-only account ACC-108 is missing, suggesting stale export dependence"
