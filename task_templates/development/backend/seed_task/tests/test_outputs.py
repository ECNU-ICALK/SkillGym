from __future__ import annotations

from conftest import request_json, running_server, runtime_refund_count


FULL_KEY = "pk_live_gold_partner"
READONLY_KEY = "pk_live_readonly_partner"
BURST_KEY = "pk_live_bronze_partner"


def _error_code(payload: dict) -> str:
    return payload["error"]["code"]


def test_orders_list_is_stable_and_filters_before_paginating() -> None:
    with running_server() as base_url:
        status1, headers1, payload1 = request_json(
            base_url,
            "GET",
            "/api/v1/orders?page=1&page_size=2&status=paid&sort=-created_at",
            api_key=FULL_KEY,
        )
        status1b, _, payload1b = request_json(
            base_url,
            "GET",
            "/api/v1/orders?page=1&page_size=2&status=paid&sort=-created_at",
            api_key=FULL_KEY,
        )
        status2, _, payload2 = request_json(
            base_url,
            "GET",
            "/api/v1/orders?page=2&page_size=2&status=paid&sort=-created_at",
            api_key=FULL_KEY,
        )

        assert status1 == 200, payload1
        assert status1b == 200, payload1b
        assert status2 == 200, payload2
        assert headers1["X-RateLimit-Limit"] == "8"
        assert "X-RateLimit-Remaining" in headers1

        page1_ids = [row["id"] for row in payload1["data"]]
        page1_again_ids = [row["id"] for row in payload1b["data"]]
        page2_ids = [row["id"] for row in payload2["data"]]

        assert page1_ids == ["ord_1008", "ord_1006"], page1_ids
        assert page1_again_ids == page1_ids, "same query should return identical first page"
        assert page2_ids == ["ord_1004", "ord_1001"], page2_ids
        assert not set(page1_ids) & set(page2_ids)
        pagination = payload1["meta"].get("pagination", payload1["meta"])
        total_items = pagination.get("total_items", pagination.get("total_count"))
        if total_items is not None:
            assert total_items == 4
        assert pagination.get("has_next", pagination.get("has_next_page")) is True

        filtered_status, _, filtered_payload = request_json(
            base_url,
            "GET",
            "/api/v1/orders?page=1&page_size=5&customer_country=AU&sort=-created_at",
            api_key=FULL_KEY,
        )
        assert filtered_status == 200, filtered_payload
        assert [row["id"] for row in filtered_payload["data"]] == ["ord_1006"]


def test_order_detail_has_machine_readable_not_found() -> None:
    with running_server() as base_url:
        status, _, payload = request_json(base_url, "GET", "/api/v1/orders/ord_1002", api_key=FULL_KEY)
        assert status == 200, payload
        assert payload["data"]["id"] == "ord_1002"
        assert payload["data"]["customer"]["id"] == "cust_002"

        missing_status, _, missing_payload = request_json(base_url, "GET", "/api/v1/orders/ord_missing", api_key=FULL_KEY)
        assert missing_status == 404, missing_payload
        assert _error_code(missing_payload) in {"order_not_found", "not_found"}


def test_refund_create_is_replay_safe_and_visible_from_get() -> None:
    with running_server() as base_url:
        before = runtime_refund_count()
        payload = {
            "order_id": "ord_1004",
            "amount": 10.0,
            "reason": "customer_request",
        }
        first_status, _, first_body = request_json(
            base_url,
            "POST",
            "/api/v1/refunds",
            api_key=FULL_KEY,
            headers={"Idempotency-Key": "idem-ord-1004-1"},
            payload=payload,
        )
        assert first_status == 201, first_body
        created = first_body["data"]
        assert created["order_id"] == "ord_1004"
        assert runtime_refund_count() == before + 1

        get_status, _, get_body = request_json(base_url, "GET", f"/api/v1/refunds/{created['id']}", api_key=FULL_KEY)
        assert get_status == 200, get_body
        assert get_body["data"]["id"] == created["id"]

        replay_status, _, replay_body = request_json(
            base_url,
            "POST",
            "/api/v1/refunds",
            api_key=FULL_KEY,
            headers={"Idempotency-Key": "idem-ord-1004-1"},
            payload=payload,
        )
        assert replay_status in {200, 201}, replay_body
        assert replay_body["data"]["id"] == created["id"]
        assert runtime_refund_count() == before + 1


def test_refund_scope_validation_and_conflicts() -> None:
    with running_server() as base_url:
        readonly_status, _, readonly_body = request_json(
            base_url,
            "POST",
            "/api/v1/refunds",
            api_key=READONLY_KEY,
            headers={"Idempotency-Key": "readonly-refund-attempt"},
            payload={"order_id": "ord_1004", "amount": 10.0, "reason": "customer_request"},
        )
        assert readonly_status == 403, readonly_body
        assert "error" in readonly_body, readonly_body

        invalid_state_status, _, invalid_state_body = request_json(
            base_url,
            "POST",
            "/api/v1/refunds",
            api_key=FULL_KEY,
            headers={"Idempotency-Key": "pending-order-refund"},
            payload={"order_id": "ord_1003", "amount": 10.0, "reason": "customer_request"},
        )
        assert invalid_state_status == 409, invalid_state_body
        assert _error_code(invalid_state_body) in {"refund_not_allowed", "order_not_refundable", "refund_pending"}

        missing_key_status, _, missing_key_body = request_json(
            base_url,
            "POST",
            "/api/v1/refunds",
            api_key=FULL_KEY,
            payload={"order_id": "ord_1004", "amount": 10.0, "reason": "customer_request"},
        )
        assert missing_key_status in {400, 422}, missing_key_body
        assert _error_code(missing_key_body) in {
            "missing_idempotency_key",
            "idempotency_key_required",
            "validation_error",
            "invalid_request",
        }

        validation_status, _, validation_body = request_json(
            base_url,
            "POST",
            "/api/v1/refunds",
            api_key=FULL_KEY,
            headers={"Idempotency-Key": "validation-refund-request"},
            payload={"order_id": "ord_1004", "amount": "oops", "reason": "customer_request"},
        )
        assert validation_status in {400, 422}, validation_body
        assert _error_code(validation_body) in {"validation_error", "invalid_request", "invalid_request_body"}

        first_status, _, first_body = request_json(
            base_url,
            "POST",
            "/api/v1/refunds",
            api_key=FULL_KEY,
            headers={"Idempotency-Key": "idem-conflict-ord-1001"},
            payload={"order_id": "ord_1001", "amount": 12.0, "reason": "damaged"},
        )
        assert first_status == 201, first_body

        conflict_status, _, conflict_body = request_json(
            base_url,
            "POST",
            "/api/v1/refunds",
            api_key=FULL_KEY,
            headers={"Idempotency-Key": "idem-conflict-ord-1001"},
            payload={"order_id": "ord_1001", "amount": 14.0, "reason": "damaged"},
        )
        assert conflict_status == 409, conflict_body
        assert _error_code(conflict_body) in {"idempotency_conflict", "idempotency_key_reused"}


def test_authentication_and_rate_limit_semantics() -> None:
    with running_server() as base_url:
        missing_status, _, missing_body = request_json(base_url, "GET", "/api/v1/orders?page=1&page_size=1", api_key=None)
        assert missing_status == 401, missing_body
        assert "error" in missing_body, missing_body

        invalid_status, _, invalid_body = request_json(base_url, "GET", "/api/v1/orders?page=1&page_size=1", api_key="pk_invalid")
        assert invalid_status == 401, invalid_body
        assert _error_code(invalid_body) == "invalid_api_key"

        seen = []
        final_headers = {}
        final_payload = None
        for _ in range(4):
            status, headers, payload = request_json(base_url, "GET", "/api/v1/orders?page=1&page_size=1", api_key=BURST_KEY)
            seen.append(status)
            final_headers = headers
            final_payload = payload

        assert seen[:3] == [200, 200, 200], seen
        assert seen[3] == 429, seen
        assert final_headers["X-RateLimit-Limit"] == "3"
        assert final_headers["X-RateLimit-Remaining"] == "0"
        retry_after = int(final_headers["Retry-After"])
        assert 1 <= retry_after <= 60
        assert _error_code(final_payload) in {"rate_limited", "rate_limit_exceeded"}
