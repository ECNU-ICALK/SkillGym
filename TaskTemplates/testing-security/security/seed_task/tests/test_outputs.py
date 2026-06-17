from __future__ import annotations

from common import request_json, request_text, running_server, runtime_export_files


FULL_KEY = "pk_live_emerald"
READONLY_KEY = "pk_live_view_only"
VIEWER_EXPORT_KEY = "pk_live_viewer_export"
BURST_KEY = "pk_live_burst"


def _error_code(payload: dict) -> str:
    return payload["error"]["code"]


def _csv_header_columns(csv_text: str) -> list[str]:
    header = csv_text.splitlines()[0]
    return [column.strip() for column in header.split(",")]


def test_advisory_list_respects_scope_filters_and_stable_pagination() -> None:
    with running_server() as base_url:
        status1, headers1, payload1 = request_json(
            base_url,
            "GET",
            "/api/v1/advisories?page=1&page_size=3&severity=critical&sort=-epss",
            api_key=FULL_KEY,
        )
        status1b, _, payload1b = request_json(
            base_url,
            "GET",
            "/api/v1/advisories?page=1&page_size=3&severity=critical&sort=-epss",
            api_key=FULL_KEY,
        )
        status2, _, payload2 = request_json(
            base_url,
            "GET",
            "/api/v1/advisories?page=2&page_size=3&severity=critical&sort=-epss",
            api_key=FULL_KEY,
        )

        assert status1 == 200, payload1
        assert status1b == 200, payload1b
        assert status2 == 200, payload2
        assert headers1["X-RateLimit-Limit"] == "12"
        assert "X-RateLimit-Remaining" in headers1

        page1_ids = [row["cve_id"] for row in payload1["data"]]
        page1_again_ids = [row["cve_id"] for row in payload1b["data"]]
        page2_ids = [row["cve_id"] for row in payload2["data"]]

        assert page1_ids == ["CVE-2024-23897", "CVE-2021-44228", "CVE-2024-3400"], page1_ids
        assert page1_again_ids == page1_ids
        assert page2_ids == ["CVE-2023-34362", "CVE-2023-3519", "CVE-2024-27198"], page2_ids
        assert payload1["meta"]["total_items"] == 8
        assert payload1["meta"]["has_next"] is True

        readonly_status, _, readonly_payload = request_json(
            base_url,
            "GET",
            "/api/v1/advisories?page=1&page_size=10&sort=-published",
            api_key=READONLY_KEY,
        )
        assert readonly_status == 200, readonly_payload
        assert [row["cve_id"] for row in readonly_payload["data"]] == [
            "CVE-2023-3519",
            "CVE-2023-34362",
            "CVE-2021-44228",
        ]


def test_detail_hides_out_of_scope_rows_and_reports_missing_rows() -> None:
    with running_server() as base_url:
        status, _, payload = request_json(base_url, "GET", "/api/v1/advisories/CVE-2024-3400", api_key=FULL_KEY)
        assert status == 200, payload
        assert payload["data"]["cve_id"] == "CVE-2024-3400"
        assert payload["data"]["vendor"] == "paloaltonetworks"

        scoped_status, _, scoped_payload = request_json(
            base_url,
            "GET",
            "/api/v1/advisories/CVE-2024-3400",
            api_key=READONLY_KEY,
        )
        assert scoped_status in {403, 404}, scoped_payload
        assert "error" in scoped_payload

        missing_status, _, missing_payload = request_json(
            base_url,
            "GET",
            "/api/v1/advisories/CVE-1900-0001",
            api_key=FULL_KEY,
        )
        assert missing_status == 404, missing_payload
        assert _error_code(missing_payload) in {"advisory_not_found", "not_found"}


def test_bulk_lookup_validates_scope_limit_and_request_shape() -> None:
    with running_server() as base_url:
        status, _, payload = request_json(
            base_url,
            "POST",
            "/api/v1/bulk-lookups",
            api_key=FULL_KEY,
            payload={"cve_ids": ["CVE-2024-3094", "CVE-2024-23897"]},
        )
        assert status == 200, payload
        assert [row["cve_id"] for row in payload["data"]] == ["CVE-2024-3094", "CVE-2024-23897"]

        limit_status, _, limit_payload = request_json(
            base_url,
            "POST",
            "/api/v1/bulk-lookups",
            api_key=READONLY_KEY,
            payload={
                "cve_ids": [
                    "CVE-2021-44228",
                    "CVE-2024-3400",
                    "CVE-2024-27198",
                    "CVE-2023-3519",
                    "CVE-2023-34362",
                    "CVE-2024-3094"
                ]
            },
        )
        assert limit_status in {400, 422}, limit_payload
        assert _error_code(limit_payload) in {"bulk_limit_exceeded", "validation_error", "invalid_request"}

        scoped_status, _, scoped_payload = request_json(
            base_url,
            "POST",
            "/api/v1/bulk-lookups",
            api_key=READONLY_KEY,
            payload={"cve_ids": ["CVE-2024-3400"]},
        )
        assert scoped_status == 403, scoped_payload
        assert _error_code(scoped_payload) in {"tenant_scope_violation", "insufficient_scope", "forbidden"}

        forbidden_status, _, forbidden_payload = request_json(
            base_url,
            "POST",
            "/api/v1/bulk-lookups",
            api_key=BURST_KEY,
            payload={"cve_ids": ["CVE-2024-23897"]},
        )
        assert forbidden_status == 403, forbidden_payload
        assert _error_code(forbidden_payload) in {"insufficient_scope", "forbidden"}


def test_export_jobs_create_csv_and_enforce_limits() -> None:
    with running_server() as base_url:
        before = runtime_export_files()

        too_wide_status, _, too_wide_payload = request_json(
            base_url,
            "POST",
            "/api/v1/export-jobs",
            api_key=FULL_KEY,
            payload={"filters": {"severity": "critical"}, "format": "csv"},
        )
        assert too_wide_status in {400, 403, 422}, too_wide_payload
        assert _error_code(too_wide_payload) in {
            "export_row_limit_exceeded",
            "export_limit_exceeded",
            "validation_error",
            "invalid_request",
            "forbidden",
        }

        create_status, _, create_payload = request_json(
            base_url,
            "POST",
            "/api/v1/export-jobs",
            api_key=FULL_KEY,
            payload={"filters": {"vendor": "jenkins", "kev_only": True}, "format": "csv"},
        )
        assert create_status == 201, create_payload
        job = create_payload["data"]
        assert job["row_count"] == 1
        assert job["tenant_id"] == "tenant_gold"
        assert len(runtime_export_files()) == len(before) + 1

        get_status, _, get_payload = request_json(
            base_url,
            "GET",
            f"/api/v1/export-jobs/{job['id']}",
            api_key=FULL_KEY,
        )
        assert get_status == 200, get_payload
        assert get_payload["data"]["id"] == job["id"]

        download_status, download_headers, csv_text = request_text(
            base_url,
            "GET",
            f"/api/v1/export-jobs/{job['id']}/download",
            api_key=FULL_KEY,
        )
        assert download_status == 200, csv_text
        assert "text/csv" in download_headers["Content-Type"]
        assert "CVE-2024-23897" in csv_text
        expected_columns = {
            "cve_id",
            "vendor",
            "product",
            "severity",
            "cvss_v3_base_score",
            "epss",
            "kev",
            "published",
            "description",
        }
        assert expected_columns.issubset(set(_csv_header_columns(csv_text)))

        readonly_status, _, readonly_payload = request_json(
            base_url,
            "POST",
            "/api/v1/export-jobs",
            api_key=READONLY_KEY,
            payload={"filters": {"vendor": "apache"}, "format": "csv"},
        )
        assert readonly_status == 403, readonly_payload
        assert _error_code(readonly_payload) in {"insufficient_scope", "forbidden"}

        viewer_status, _, viewer_payload = request_json(
            base_url,
            "POST",
            "/api/v1/export-jobs",
            api_key=VIEWER_EXPORT_KEY,
            payload={"filters": {"vendor": "apache"}, "format": "csv"},
        )
        assert viewer_status == 403, viewer_payload
        assert _error_code(viewer_payload) in {"insufficient_role", "analyst_role_required", "forbidden"}


def test_authentication_and_rate_limit_semantics() -> None:
    with running_server() as base_url:
        missing_status, _, missing_payload = request_json(
            base_url,
            "GET",
            "/api/v1/advisories?page=1&page_size=1",
            api_key=None,
        )
        assert missing_status == 401, missing_payload
        assert "error" in missing_payload

        invalid_status, _, invalid_payload = request_json(
            base_url,
            "GET",
            "/api/v1/advisories?page=1&page_size=1",
            api_key="pk_invalid",
        )
        assert invalid_status == 401, invalid_payload
        assert _error_code(invalid_payload) in {"invalid_api_key", "unauthorized"}

        seen = []
        final_headers = {}
        final_payload = None
        for _ in range(4):
            status, headers, payload = request_json(
                base_url,
                "GET",
                "/api/v1/advisories?page=1&page_size=1",
                api_key=BURST_KEY,
            )
            seen.append(status)
            final_headers = headers
            final_payload = payload

        assert seen[:3] == [200, 200, 200], seen
        assert seen[3] == 429, seen
        assert final_headers["X-RateLimit-Limit"] == "3"
        assert final_headers["X-RateLimit-Remaining"] == "0"
        assert _error_code(final_payload) in {"rate_limited", "quota_exceeded", "rate_limit_exceeded"}
