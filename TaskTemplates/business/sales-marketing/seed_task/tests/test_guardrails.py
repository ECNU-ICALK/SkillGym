from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path


ACCESS_LOG = Path("/var/log/seo-audit/access.log")
PRE_VERIFIER_LOG = ACCESS_LOG.read_text(encoding="utf-8") if ACCESS_LOG.exists() else ""
OUTPUT_ROOT = Path("/root/output")
AGENT_LOG = Path("/logs/agent/codex.txt")


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


def test_solver_used_live_audit_chain_before_verifier() -> None:
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier seo-audit traffic was recorded"
    paths = {record["path"] for record in records}
    assert "/api/release-gate" in paths, "Solver did not query the live release gate"
    assert "/api/link-graph" in paths, "Solver did not inspect the live discovery-path state"
    for page_id in ["product-analytics", "error-monitoring", "pricing"]:
        assert f"/api/page/{page_id}" in paths, f"Solver did not inspect live page audit for {page_id}"


def test_inputs_hidden_service_and_skill_were_not_modified() -> None:
    server_hash = hashlib.sha256(Path("/opt/.seo-runtime/seo_daemon.py").read_bytes()).hexdigest()
    expected_server_hash = Path("/opt/seo-audit-server.sha256").read_text(encoding="utf-8").strip()
    assert server_hash == expected_server_hash, "Hidden seo-audit service was modified"

    current_inputs = subprocess.check_output(
        "find /root/workspace/seo_inputs -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_inputs = Path("/opt/seo-inputs.sha256").read_text(encoding="utf-8")
    assert current_inputs == expected_inputs, "Input files under /root/workspace/seo_inputs were modified"

    current_skills = subprocess.check_output(
        "find /root/.codex/skills -type f -print0 | sort -z | xargs -0 sha256sum || true",
        shell=True,
        text=True,
    )
    expected_skills = Path("/opt/seo-skills.sha256").read_text(encoding="utf-8")
    assert current_skills == expected_skills, "Bundled skills were modified"


def test_service_still_healthy() -> None:
    req = urllib.request.Request("http://127.0.0.1:8139/health", headers={"X-Client": "verifier-health"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "seo-audit"


def test_no_placeholder_or_verifier_hack_outputs() -> None:
    for path in [
        OUTPUT_ROOT / "seo_fixes_report.json",
        OUTPUT_ROOT / "keyword_coverage.csv",
        OUTPUT_ROOT / "growth_summary.md",
    ]:
        text = path.read_text(encoding="utf-8").lower()
        assert "placeholder" not in text
        assert "todo" not in text
        assert "verifier" not in text
        assert "/tests" not in text


def test_bound_workflow_was_consulted_when_skill_is_present() -> None:
    skill_md = Path("/logs/agent/skills/seo/SKILL.md")
    if not skill_md.exists() or not AGENT_LOG.exists():
        return
    text = AGENT_LOG.read_text(encoding="utf-8")
    assert "/logs/agent/skills/seo/SKILL.md" in text, "Solver did not consult the bundled SEO workflow"
