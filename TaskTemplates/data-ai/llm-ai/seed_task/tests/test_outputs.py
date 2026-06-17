from __future__ import annotations

import shutil

from conftest import build_alternate_fixture, request_json, running_stack


EXPECTED_TRIAGE_KEYS = {"ticket_id", "status", "queue", "intent", "recommended_action", "evidence", "escalation", "source"}
EXPECTED_REVIEW_KEYS = {"ticket_id", "disposition", "review_note", "evidence", "escalation_reason", "source"}


def test_single_triage_contract_is_stable_across_modes() -> None:
    with running_stack() as base_url:
        sandbox_status, _, sandbox_payload = request_json(base_url, "POST", "/api/v1/triage", payload={"mode": "sandbox", "ticket_id": "bank_002"})
        live_status, _, live_payload = request_json(base_url, "POST", "/api/v1/triage", payload={"mode": "live", "ticket_id": "bank_002"})
        assert sandbox_status == 200, sandbox_payload
        assert live_status == 200, live_payload
        assert set(sandbox_payload.keys()) == {"request_id", "mode", "data"}
        assert set(live_payload.keys()) == {"request_id", "mode", "data"}
        assert set(sandbox_payload["data"].keys()) == EXPECTED_TRIAGE_KEYS
        assert set(live_payload["data"].keys()) == EXPECTED_TRIAGE_KEYS


def test_batch_returns_result_for_every_ticket() -> None:
    with running_stack() as base_url:
        status, _, payload = request_json(base_url, "POST", "/api/v1/triage/batch", payload={"mode": "live", "ticket_ids": ["bank_002", "clinc_001", "bank_005"]})
        assert status == 200, payload
        assert payload["summary"] == {"total": 3, "processed": 3, "success_count": 1, "escalated_count": 1, "failed_count": 1}
        assert len(payload["results"]) == 3, payload["results"]
        failed_rows = [row for row in payload["results"] if row["status"] == "failed"]
        assert len(failed_rows) == 1, payload["results"]
        assert failed_rows[0]["error"]["ticket_id"] == "bank_005"


def test_batch_keeps_missing_tickets_as_failed_rows_instead_of_aborting() -> None:
    with running_stack() as base_url:
        status, _, payload = request_json(base_url, "POST", "/api/v1/triage/batch", payload={"mode": "live", "ticket_ids": ["missing_ticket", "bank_001", "bank_005"]})
        assert status == 200, payload
        assert payload["summary"] == {"total": 3, "processed": 3, "success_count": 1, "escalated_count": 0, "failed_count": 2}
        assert [row["ticket_id"] for row in payload["results"]] == ["missing_ticket", "bank_001", "bank_005"]
        assert payload["results"][0]["status"] == "failed"
        assert payload["results"][0]["error"] == {
            "code": "ticket_not_found",
            "message": "ticket missing_ticket was not found",
            "retryable": False,
            "ticket_id": "missing_ticket"
        }
        assert payload["results"][2]["status"] == "failed"
        assert payload["results"][2]["error"]["code"] == "provider_temporarily_unavailable"


def test_batch_keeps_failed_fallback_rows_when_malformed_live_ticket_maps_to_failed_sandbox_case() -> None:
    with running_stack() as base_url:
        status, _, payload = request_json(base_url, "POST", "/api/v1/triage/batch", payload={"mode": "live", "ticket_ids": ["bank_008", "bank_001"]})
        assert status == 200, payload
        assert payload["summary"] == {"total": 2, "processed": 2, "success_count": 1, "escalated_count": 0, "failed_count": 1}
        assert [(row["ticket_id"], row["status"]) for row in payload["results"]] == [("bank_008", "failed"), ("bank_001", "success")]


def test_review_suggestion_keeps_empty_evidence_and_nullable_reason() -> None:
    with running_stack() as base_url:
        sandbox_status, _, sandbox_payload = request_json(base_url, "POST", "/api/v1/review-suggestion", payload={"mode": "sandbox", "ticket_id": "bank_004"})
        live_status, _, live_payload = request_json(base_url, "POST", "/api/v1/review-suggestion", payload={"mode": "live", "ticket_id": "bank_004"})
        assert sandbox_status == 200, sandbox_payload
        assert live_status == 200, live_payload
        assert set(sandbox_payload["data"].keys()) == EXPECTED_REVIEW_KEYS
        assert set(live_payload["data"].keys()) == EXPECTED_REVIEW_KEYS
        assert sandbox_payload["data"]["evidence"] == []
        assert live_payload["data"]["evidence"] == []
        assert sandbox_payload["data"]["escalation_reason"] is None
        assert live_payload["data"]["escalation_reason"] is None


def test_missing_ticket_keeps_machine_readable_error() -> None:
    with running_stack() as base_url:
        status, _, payload = request_json(base_url, "POST", "/api/v1/triage", payload={"mode": "sandbox", "ticket_id": "missing_ticket"})
        assert status == 404, payload
        assert payload["error"]["code"] == "ticket_not_found"
        assert payload["error"]["retryable"] is False
        assert payload["error"]["ticket_id"] == "missing_ticket"


def test_live_triage_falls_back_when_provider_returns_invalid_json() -> None:
    with running_stack() as base_url:
        status, _, payload = request_json(base_url, "POST", "/api/v1/triage", payload={"mode": "live", "ticket_id": "bank_006"})
        assert status == 200, payload
        assert payload["data"] == {
            "ticket_id": "bank_006",
            "status": "success",
            "queue": "profile-maintenance",
            "intent": "beneficiary_not_defined",
            "recommended_action": "guide_beneficiary_update_steps",
            "evidence": [],
            "escalation": {"required": False, "reason": None},
            "source": "live"
        }


def test_live_triage_falls_back_when_provider_returns_invalid_payload() -> None:
    with running_stack() as base_url:
        status, _, payload = request_json(base_url, "POST", "/api/v1/triage", payload={"mode": "live", "ticket_id": "bank_007"})
        assert status == 200, payload
        assert set(payload["data"].keys()) == EXPECTED_TRIAGE_KEYS
        assert payload["data"]["ticket_id"] == "bank_007"
        assert payload["data"]["status"] == "success"
        assert isinstance(payload["data"]["queue"], str)
        assert isinstance(payload["data"]["intent"], str)
        assert isinstance(payload["data"]["recommended_action"], str)
        assert isinstance(payload["data"]["evidence"], list)
        assert payload["data"]["escalation"] == {"required": False, "reason": None}
        assert payload["data"]["source"] == "live"


def test_live_review_remains_available_when_provider_review_fails() -> None:
    with running_stack() as base_url:
        status, _, payload = request_json(base_url, "POST", "/api/v1/review-suggestion", payload={"mode": "live", "ticket_id": "bank_005"})
        assert status == 200, payload
        assert set(payload["data"].keys()) == EXPECTED_REVIEW_KEYS
        assert payload["data"]["ticket_id"] == "bank_005"
        assert payload["data"]["disposition"] == "manual_review"
        assert payload["data"]["evidence"] == []
        assert payload["data"]["escalation_reason"] == "provider_temporarily_unavailable"
        assert payload["data"]["source"] == "live"
        assert payload["data"]["review_note"]


def test_live_review_falls_back_to_stable_review_when_provider_output_is_invalid() -> None:
    with running_stack() as base_url:
        status, _, payload = request_json(base_url, "POST", "/api/v1/review-suggestion", payload={"mode": "live", "ticket_id": "bank_006"})
        assert status == 200, payload
        assert payload["data"] == {
            "ticket_id": "bank_006",
            "disposition": "send_knowledge_reply",
            "review_note": "Provide the beneficiary maintenance checklist and confirm the supported identity verification path.",
            "evidence": [],
            "escalation_reason": None,
            "source": "live"
        }


def test_live_review_falls_back_when_provider_payload_shape_is_invalid() -> None:
    with running_stack() as base_url:
        status, _, payload = request_json(base_url, "POST", "/api/v1/review-suggestion", payload={"mode": "live", "ticket_id": "bank_007"})
        assert status == 200, payload
        assert set(payload["data"].keys()) == EXPECTED_REVIEW_KEYS
        assert payload["data"]["ticket_id"] == "bank_007"
        assert isinstance(payload["data"]["disposition"], str)
        assert isinstance(payload["data"]["review_note"], str)
        assert isinstance(payload["data"]["evidence"], list)
        assert payload["data"]["escalation_reason"] is None
        assert payload["data"]["source"] == "live"


def test_live_triage_does_not_leak_prior_escalation_state_between_requests() -> None:
    with running_stack() as base_url:
        first_status, _, first_payload = request_json(base_url, "POST", "/api/v1/triage", payload={"mode": "live", "ticket_id": "bank_001"})
        second_status, _, second_payload = request_json(base_url, "POST", "/api/v1/triage", payload={"mode": "live", "ticket_id": "bank_004"})
        assert first_status == 200, first_payload
        assert second_status == 200, second_payload
        assert second_payload["data"]["ticket_id"] == "bank_004"
        assert second_payload["data"]["evidence"] == []
        assert second_payload["data"]["escalation"] == {"required": False, "reason": None}


def test_live_review_does_not_leak_prior_manual_review_state_between_requests() -> None:
    with running_stack() as base_url:
        first_status, _, first_payload = request_json(base_url, "POST", "/api/v1/review-suggestion", payload={"mode": "live", "ticket_id": "bank_005"})
        second_status, _, second_payload = request_json(base_url, "POST", "/api/v1/review-suggestion", payload={"mode": "live", "ticket_id": "bank_004"})
        assert first_status == 200, first_payload
        assert second_status == 200, second_payload
        assert second_payload["data"]["ticket_id"] == "bank_004"
        assert second_payload["data"]["evidence"] == []
        assert second_payload["data"]["escalation_reason"] is None


def test_live_triage_uses_existing_case_facts_for_unseen_invalid_provider_cases() -> None:
    alt_data_dir, alt_state_dir = build_alternate_fixture()
    try:
        with running_stack(data_dir=alt_data_dir, state_dir=alt_state_dir) as base_url:
            status, _, payload = request_json(base_url, "POST", "/api/v1/triage", payload={"mode": "live", "ticket_id": "bank_109"})
            assert status == 200, payload
            assert payload["data"] == {
                "ticket_id": "bank_109",
                "status": "success",
                "queue": "profile-maintenance",
                "intent": "beneficiary_not_defined",
                "recommended_action": "guide_joint_beneficiary_update_steps",
                "evidence": [],
                "escalation": {"required": False, "reason": None},
                "source": "live"
            }
    finally:
        shutil.rmtree(alt_data_dir.parent)


def test_live_review_uses_existing_case_facts_for_unseen_invalid_provider_cases() -> None:
    alt_data_dir, alt_state_dir = build_alternate_fixture()
    try:
        with running_stack(data_dir=alt_data_dir, state_dir=alt_state_dir) as base_url:
            status, _, payload = request_json(base_url, "POST", "/api/v1/review-suggestion", payload={"mode": "live", "ticket_id": "bank_110"})
            assert status == 200, payload
            assert payload["data"] == {
                "ticket_id": "bank_110",
                "disposition": "send_knowledge_reply",
                "review_note": "Share the joint beneficiary maintenance checklist and confirm the supported fallback verification path.",
                "evidence": [],
                "escalation_reason": None,
                "source": "live"
            }
    finally:
        shutil.rmtree(alt_data_dir.parent)

