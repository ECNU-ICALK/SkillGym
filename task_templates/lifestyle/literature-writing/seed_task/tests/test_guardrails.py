from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path


ACCESS_LOG = Path(os.environ.get("LAUNCH_COPY_ACCESS_LOG", "/var/log/launch-copy/access.log"))
PRE_VERIFIER_LOG = ACCESS_LOG.read_text(encoding="utf-8") if ACCESS_LOG.exists() else ""
AGENT_LOG = Path(os.environ.get("AGENT_LOG_PATH", "/logs/agent/codex.txt"))
WORKSPACE_ROOT = Path(os.environ.get("LAUNCH_COPY_WORKSPACE_ROOT", "/workspace"))
DATA_ROOT = Path(os.environ.get("LAUNCH_COPY_DATA_ROOT", "/opt/launch-copy-data"))
SERVICE_ROOT = Path(os.environ.get("LAUNCH_COPY_SERVICE_ROOT", "/services/launch-copy-service"))
SKILL_ROOT = Path(os.environ.get("CODEX_SKILLS_ROOT", "/root/.codex/skills"))
WORKSPACE_HASH_PATH = Path(os.environ.get("WORKSPACE_HASH_PATH", "/opt/workspace-inputs.sha256"))
DATA_HASH_PATH = Path(os.environ.get("DATA_HASH_PATH", "/opt/launch-copy-data.sha256"))
SERVICE_HASH_PATH = Path(os.environ.get("SERVICE_HASH_PATH", "/opt/launch-copy-service.sha256"))
BOUND_SKILL_MD_PATH = Path(os.environ.get("BOUND_SKILL_MD_PATH", "/logs/agent/skills/brand-writer/SKILL.md"))
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/root/final_launch_copy_package.json"))


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
        if client.startswith("verifier-"):
            continue
        records.append(record)
    return records


def test_solver_used_required_content_service_endpoints() -> None:
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier content-service traffic was recorded"
    paths = {record["path"] for record in records}
    required_paths = {
        "/api/source-index",
        "/api/tone-examples",
        "/api/banned-phrases",
        "/api/editorial-constraints",
        "/api/rejected-draft",
        "/api/quality-gate",
    }
    for path in required_paths:
        assert path in paths, f"Solver did not call required endpoint {path}"

    source_index = json.loads((DATA_ROOT / "source_index.json").read_text(encoding="utf-8"))
    for doc in source_index["docs"]:
        path = f"/api/document/{doc['doc_id']}"
        assert path in paths, f"Solver did not inspect document {doc['doc_id']}"


def test_workspace_data_and_hidden_service_were_not_modified() -> None:
    approved_copy_dir = WORKSPACE_ROOT / "examples" / "approved_copy"
    current_workspace = subprocess.check_output(
        f"find {WORKSPACE_ROOT / 'work_order.json'} {WORKSPACE_ROOT / 'service_manifest.json'} {WORKSPACE_ROOT / 'notes'} {WORKSPACE_ROOT / 'drafts'} {approved_copy_dir} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    assert current_workspace == WORKSPACE_HASH_PATH.read_text(encoding="utf-8"), "Workspace inputs were modified"

    current_data = subprocess.check_output(
        f"find {DATA_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    assert current_data == DATA_HASH_PATH.read_text(encoding="utf-8"), "Source data bundle was modified"

    current_service = subprocess.check_output(
        f"find {SERVICE_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    assert current_service == SERVICE_HASH_PATH.read_text(encoding="utf-8"), "Hidden content service files were modified"


def test_content_service_still_healthy() -> None:
    req = urllib.request.Request(os.environ.get("SERVICE_HEALTH_URL", "http://127.0.0.1:8080/health"), headers={"X-Client": "verifier-health"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "launch-copy-service"


def test_outputs_do_not_reference_internal_paths() -> None:
    text = OUTPUT_PATH.read_text(encoding="utf-8").lower()
    assert "/services/launch-copy-service" not in text
    assert "/opt/launch-copy-data" not in text
    assert "/logs/verifier" not in text


def test_bound_skill_was_consulted_when_present() -> None:
    if not BOUND_SKILL_MD_PATH.exists() or not AGENT_LOG.exists():
        return
    text = AGENT_LOG.read_text(encoding="utf-8")
    assert str(BOUND_SKILL_MD_PATH) in text, "Solver did not consult the bundled brand-writer workflow"


def test_hidden_service_implementation_was_not_inspected() -> None:
    if not AGENT_LOG.exists():
        return
    text = AGENT_LOG.read_text(encoding="utf-8")
    forbidden_patterns = [
        "cat /services/launch-copy-service/server.py",
        "sed -n '1,200p' /services/launch-copy-service/server.py",
        "sed -n \"1,200p\" /services/launch-copy-service/server.py",
        "rg server.py /services/launch-copy-service",
        "find /services/launch-copy-service",
        "cat /opt/literature-writing-environment/hidden-service-src/server.py",
        "find environment/hidden-service-src",
    ]
    lowered = text.lower()
    for pattern in forbidden_patterns:
        assert pattern.lower() not in lowered, f"Solver inspected hidden content-service implementation via pattern: {pattern}"
