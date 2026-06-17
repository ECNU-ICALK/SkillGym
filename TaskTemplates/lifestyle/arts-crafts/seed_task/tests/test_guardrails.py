from __future__ import annotations

import subprocess
import os
from pathlib import Path

from test_helpers import ACCESS_LOG, AUDIT_PATH, pre_verifier_records, source_health


AGENT_LOG = Path("/logs/agent/codex.txt")
TASK_ROOT = Path(os.environ.get("ARTS_CRAFTS_TASK_ROOT", "/root"))
SERVICE_ROOT = Path(os.environ.get("ARTS_CRAFTS_SERVICE_ROOT", "/services/model-source"))
MIRROR_ROOT = Path(os.environ.get("ARTS_CRAFTS_MIRROR_ROOT", "/srv/model-source/files"))
DATA_HASH_PATH = Path(os.environ.get("ARTS_CRAFTS_DATA_HASH_PATH", "/opt/model-bundle-data.sha256"))
SERVICE_HASH_PATH = Path(os.environ.get("ARTS_CRAFTS_SERVICE_HASH_PATH", "/opt/model-source-service.sha256"))
FILES_HASH_PATH = Path(os.environ.get("ARTS_CRAFTS_FILES_HASH_PATH", "/opt/model-source-files.sha256"))
def test_solver_used_source_service_chain_before_verifier() -> None:
    records = pre_verifier_records()
    assert records, "No pre-verifier service traffic was recorded"
    graphql = [record for record in records if record["method"] == "POST" and record["path"] == "/graphql/"]
    assert graphql, "Solver did not query the source GraphQL endpoint"
    for record in graphql:
        assert record.get("host") == "api.printables.com", "Solver did not use the canonical source host"
        assert record.get("origin") == "https://www.printables.com", "Solver did not use the canonical source origin"
        assert record.get("referer") == "https://www.printables.com/", "Solver did not use the canonical source referer"
    search_calls = [record for record in graphql if "searchPrints2" in record.get("body", "")]
    detail_calls = [record for record in graphql if "print(id:$id)" in record.get("body", "") or "print(id: $id)" in record.get("body", "")]
    download_calls = [record for record in graphql if "getDownloadLink" in record.get("body", "")]
    assert len(search_calls) >= 3, "Solver did not perform the expected search calls"
    assert len(detail_calls) >= 3, "Solver did not inspect model details for the bundle"
    assert len(download_calls) >= 3, "Solver did not request downloadable files"
    for record in download_calls:
        body = record.get("body", "")
        assert "source:model_detail" in body, "Solver did not use the canonical getDownloadLink mutation"
        assert "files:[{fileType:$ft, ids:$ids}]" in body, "Solver did not use the canonical file selector shape"
    pack_gets = [record for record in records if record["method"] == "GET" and record["path"].startswith("/files/pack/")]
    assert len(pack_gets) >= 3, "Solver did not preserve the source packs through the download chain"
    file_gets = [
        record
        for record in records
        if record["method"] == "GET" and (record["path"].startswith("/files/pack/") or record["path"].startswith("/files/stl/"))
    ]
    assert len(file_gets) >= 3, "Solver did not download the mirrored model files"


def test_inputs_and_hidden_payloads_were_not_modified() -> None:
    current_data = subprocess.check_output(f"find {TASK_ROOT / 'environment' / 'data'} -type f -print0 | sort -z | xargs -0 sha256sum", shell=True, text=True)
    expected_data = DATA_HASH_PATH.read_text(encoding="utf-8")
    assert current_data == expected_data, "Input data under /root/environment/data was modified"

    current_service = subprocess.check_output(f"find {SERVICE_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum", shell=True, text=True)
    expected_service = SERVICE_HASH_PATH.read_text(encoding="utf-8")
    assert current_service == expected_service, "Model source service files were modified"

    current_files = subprocess.check_output(f"find {MIRROR_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum", shell=True, text=True)
    expected_files = FILES_HASH_PATH.read_text(encoding="utf-8")
    assert current_files == expected_files, "Mirrored model files were modified"


def test_source_service_still_healthy() -> None:
    payload = source_health()
    assert payload["ok"] is True
    assert payload["service"] == "model-source"


def test_outputs_are_not_shortcuts() -> None:
    audit = AUDIT_PATH.read_text(encoding="utf-8")
    assert "graphql" in audit.lower()
    assert ACCESS_LOG.exists() and ACCESS_LOG.read_text(encoding="utf-8").strip(), "Access log is empty"


def test_solver_did_not_bypass_tls_or_localhost_source_aliases() -> None:
    if not AGENT_LOG.exists():
        return
    text = AGENT_LOG.read_text(encoding="utf-8")
    forbidden_snippets = [
        "curl -k ",
        "curl -sk ",
        "curl --insecure ",
        "https://127.0.0.1/",
        "https://localhost/",
        "/services/model-source/catalog_seed.json",
    ]
    for snippet in forbidden_snippets:
        assert snippet not in text, f"Solver used insecure or localhost-only source access: {snippet}"


def test_bound_skill_workflow_was_consulted_if_present() -> None:
    skill_md = Path("/logs/agent/skills/find-stl/SKILL.md")
    if not skill_md.exists():
        return
    if not AGENT_LOG.exists():
        return
    text = AGENT_LOG.read_text(encoding="utf-8")
    assert "/logs/agent/skills/find-stl/SKILL.md" in text, "Solver did not consult the bundled find-stl workflow"
