from __future__ import annotations

import shutil
from pathlib import Path

from conftest import DATA_ROOT, TASK_ROOT, WORKSPACE_ROOT, build_alternate_fixture, provider_request_count, request_json, running_stack, service_request_count, static_data_hash


AGENT_LOG = Path("/logs/agent/codex.txt")


def test_static_input_data_unchanged() -> None:
    assert static_data_hash() == "071856608e0134af9b254e9c950d5bac88675db193c97debb99dd2ba1b3768e5"


def test_behavior_generalizes_on_alternate_fixture() -> None:
    alt_data_dir, alt_state_dir = build_alternate_fixture()
    try:
        with running_stack(data_dir=alt_data_dir, state_dir=alt_state_dir) as base_url:
            triage_status, _, triage_payload = request_json(base_url, "POST", "/api/v1/triage", payload={"mode": "sandbox", "ticket_id": "bank_099"})
            assert triage_status == 200, triage_payload
            assert triage_payload["data"] == {
                "ticket_id": "bank_099",
                "status": "success",
                "queue": "card-ops",
                "intent": "cash_withdrawal_reverted",
                "recommended_action": "explain_reverted_card_payment",
                "evidence": [
                    {
                        "source_id": "kb:card-reverted-payment",
                        "snippet": "Reverted card payments are usually released automatically if the merchant did not capture the authorization."
                    }
                ],
                "escalation": {"required": False, "reason": None},
                "source": "sandbox"
            }
            batch_status, _, batch_payload = request_json(base_url, "POST", "/api/v1/triage/batch", payload={"mode": "live", "ticket_ids": ["bank_099", "clinc_001", "bank_005"]})
            assert batch_status == 200, batch_payload
            assert batch_payload["summary"] == {"total": 3, "processed": 3, "success_count": 1, "escalated_count": 1, "failed_count": 1}
            assert [row["ticket_id"] for row in batch_payload["results"]] == ["bank_099", "clinc_001", "bank_005"]
    finally:
        shutil.rmtree(alt_data_dir.parent)


def test_live_mode_hits_provider_sim_but_sandbox_does_not() -> None:
    with running_stack() as base_url:
        assert provider_request_count() == 0
        assert service_request_count() == 0
        sandbox_status, _, sandbox_payload = request_json(base_url, "POST", "/api/v1/triage", payload={"mode": "sandbox", "ticket_id": "bank_001"})
        assert sandbox_status == 200, sandbox_payload
        assert provider_request_count() == 0
        live_status, _, live_payload = request_json(base_url, "POST", "/api/v1/triage", payload={"mode": "live", "ticket_id": "bank_001"})
        assert live_status == 200, live_payload
        assert provider_request_count() == 1
        assert service_request_count() == 2


def test_bound_skill_workflow_can_be_consulted_if_present() -> None:
    skill_md = Path("/logs/agent/skills/ai-regression-testing/SKILL.md")
    if not skill_md.exists():
        return
    assert skill_md.read_text(encoding="utf-8")


def test_agent_trace_reflects_bound_regression_workflow() -> None:
    if not AGENT_LOG.exists():
        return
    log_text = AGENT_LOG.read_text(encoding="utf-8")
    skill_marker = "/logs/agent/skills/ai-regression-testing/SKILL.md"
    test_marker = "\"command\":\"/bin/bash -lc 'npm test'\""
    file_change_marker = "\"type\":\"file_change\""

    skill_pos = log_text.find(skill_marker)
    test_pos = log_text.find(test_marker)
    file_change_pos = log_text.find(file_change_marker)

    assert skill_pos != -1, "agent trace did not consult the bound ai-regression-testing skill"
    assert test_pos != -1, "agent trace did not run npm test"
    if file_change_pos != -1:
        assert skill_pos < file_change_pos, "agent edited files before consulting the bound skill"
        assert test_pos < file_change_pos, "agent edited files before running npm test"


def test_task_kept_expected_structure() -> None:
    assert Path("/app/workspace/server.js").exists() or (TASK_ROOT / "workspace" / "server.js").exists()
    assert Path("/services/provider-sim/src/server.js").exists() or (TASK_ROOT / "provider-sim" / "src" / "server.js").exists()
    assert Path("/tests/test.sh").exists() or (TASK_ROOT.parent / "tests" / "test.sh").exists()
    assert (DATA_ROOT / "contracts" / "structured_output_schema.json").exists()
