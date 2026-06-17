from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path

from common import TRIAGE_PATH, build_expected


ACCESS_LOG = Path(os.environ.get("PLANNING_ACCESS_LOG", "/var/log/project-planning/access.log"))
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


def test_solver_used_live_planning_service_before_verifier() -> None:
    expected = build_expected()
    expected_ids = {item["item_id"] for item in expected["items"]}
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier planning service traffic was recorded"

    list_calls = [r for r in records if r["path"] == "/api/items"]
    detail_calls = [r for r in records if r["path"].startswith("/api/items/") and r["path"] != "/api/items"]

    seen_pages = {int(r.get("query", {}).get("page", ["1"])[0]) for r in list_calls}
    assert {1, 2, 3}.issubset(seen_pages), f"Solver did not traverse all backlog pages: saw {seen_pages}"

    seen_detail_ids = {record["path"].rsplit("/", 1)[-1] for record in detail_calls}
    assert expected_ids.issubset(seen_detail_ids), "Solver did not fetch detail facts for every backlog item"


def test_inputs_and_hidden_service_were_not_modified() -> None:
    data_root = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
    service_root = Path(os.environ.get("TASK_SERVICE_ROOT", "/services/project-planning"))
    expected_data_hash_path = Path(os.environ.get("TASK_DATA_HASH_PATH", "/opt/project-planning-data.sha256"))
    expected_service_hash_path = Path(os.environ.get("TASK_SERVICE_HASH_PATH", "/opt/project-planning-service.sha256"))

    current_data = subprocess.check_output(
        f"find {data_root} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_data = expected_data_hash_path.read_text(encoding="utf-8")
    assert current_data == expected_data, "Input data under /root/data was modified"

    current_service = subprocess.check_output(
        f"find {service_root} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_service = expected_service_hash_path.read_text(encoding="utf-8")
    assert current_service == expected_service, "Hidden planning service files were modified"


def test_live_service_still_healthy() -> None:
    health_url = os.environ.get("TASK_HEALTH_URL", "http://127.0.0.1:8137/health")
    with urllib.request.urlopen(health_url, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "project-planning"


def test_live_only_items_were_not_missed() -> None:
    text = TRIAGE_PATH.read_text(encoding="utf-8")
    assert "SV-204" in text, "Live-only item SV-204 is missing, suggesting stale export dependence"
    assert "SV-331" in text, "Live-only item SV-331 is missing, suggesting stale export dependence"
    assert "SV-172" in text, "Live-only item SV-172 is missing, suggesting stale export dependence"
