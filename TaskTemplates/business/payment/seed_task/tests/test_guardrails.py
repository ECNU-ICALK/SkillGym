from __future__ import annotations

import hashlib
import json
import os
import subprocess
import urllib.request
from pathlib import Path

from common import OUTPUT_ROOT, REGISTER_PATH, build_expected


ACCESS_LOG = Path(os.environ.get("AP_REVIEW_ACCESS_LOG", "/var/log/ap-review/access.log"))
DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
SERVICE_ROOT = Path(os.environ.get("TASK_SERVICE_ROOT", "/services/ap-review"))
DATA_HASH_PATH = Path(os.environ.get("TASK_DATA_HASH_PATH", "/opt/payment-data.sha256"))
SERVICE_HASH_PATH = Path(os.environ.get("TASK_SERVICE_HASH_PATH", "/opt/payment-service.sha256"))
SKILL_HASH_PATH = Path(os.environ.get("TASK_SKILL_HASH_PATH", "/opt/payment-skills.sha256"))
SKILL_ROOT = Path(os.environ.get("TASK_SKILL_ROOT", "/root/.codex/skills"))
HEALTH_URL = os.environ.get("TASK_HEALTH_URL", "http://127.0.0.1:8148/health")
PRE_VERIFIER_LOG = ACCESS_LOG.read_text(encoding="utf-8") if ACCESS_LOG.exists() else ""


def parse_pre_verifier_records() -> list[dict]:
    records = []
    for line in PRE_VERIFIER_LOG.splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        client = record.get("client", "")
        if client.startswith("verifier-") or client == "verifier-main":
            continue
        records.append(record)
    return records


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def test_solver_used_ap_review_service_before_verifier() -> None:
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier AP review traffic was recorded"
    assert any(record["path"] == "/api/manifest" for record in records), "Solver did not query the manifest endpoint"

    list_calls = [record for record in records if record["path"] == "/api/documents"]
    seen_pages = {int(record.get("query", {}).get("page", ["1"])[0]) for record in list_calls}
    assert {1, 2, 3}.issubset(seen_pages), f"Solver did not fetch all document pages: saw {seen_pages}"

    detail_ids = {
        record["path"].rsplit("/", 1)[-1]
        for record in records
        if record["path"].startswith("/api/documents/") and record["path"] != "/api/documents"
    }
    expected_ids = {f"DOC-10{i}" for i in range(0, 9)}
    assert expected_ids.issubset(detail_ids), "Solver did not fetch detail facts for every live document"


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
    assert current_service == SERVICE_HASH_PATH.read_text(encoding="utf-8"), "AP review service files were modified"

    if SKILL_HASH_PATH.exists() and SKILL_ROOT.exists():
        current_skill = subprocess.check_output(
            f"find {SKILL_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
            shell=True,
            text=True,
        )
        assert current_skill == SKILL_HASH_PATH.read_text(encoding="utf-8"), "Installed skill files were modified"


def test_organized_copies_exist_and_match_source_hashes() -> None:
    expected = build_expected()
    for row in expected["register_rows"]:
        source = DATA_ROOT / row["source_file"]
        organized = OUTPUT_ROOT / row["organized_relative_path"]
        assert organized.exists(), f"Missing organized copy for {row['source_file']}"
        assert sha256_file(source) == sha256_file(organized), f"Organized copy does not match source for {row['source_file']}"


def test_live_service_still_healthy() -> None:
    req = urllib.request.Request(HEALTH_URL, headers={"X-Client": "verifier-health"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "ap-review"


def test_live_only_documents_were_not_missed() -> None:
    text = REGISTER_PATH.read_text(encoding="utf-8")
    for source_file in build_expected()["live_only_source_files"]:
        assert source_file in text, f"Live-only document {source_file} is missing, suggesting stale snapshot dependence"
