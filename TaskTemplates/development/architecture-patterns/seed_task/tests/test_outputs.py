import json

import requests

from conftest import (
    ALT_FIXTURE_ROOT,
    VISIBLE_DATA_ROOT,
    build_alternate_data_root,
    build_gtfs_reference,
    reference_departures,
    reference_search,
    reference_service_window,
    run_audit,
    run_compare,
    run_export,
    running_server,
)


def call_http(base_url: str, provider_id: str, query: dict) -> dict:
    if query["kind"] == "stop_search":
        response = requests.get(
            f"{base_url}/v1/providers/{provider_id}/stops/search",
            params={"q": query["query"], "limit": query["limit"]},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()

    if query["kind"] == "departures":
        response = requests.get(
            f"{base_url}/v1/providers/{provider_id}/stops/{query['stop_id']}/departures",
            params={"date": query["date"], "time": query["time"], "limit": query["limit"]},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()

    if query["kind"] == "service_window":
        response = requests.get(
            f"{base_url}/v1/providers/{provider_id}/routes/{query['route_id']}/service-window",
            params={"date": query["date"]},
            timeout=5,
        )
        response.raise_for_status()
        return response.json()

    raise AssertionError(f"unknown query kind: {query['kind']}")


def expected_result(reference: dict, provider_id: str, query: dict) -> dict:
    if query["kind"] == "stop_search":
        return {
            "provider_id": provider_id,
            "query": query["query"],
            "limit": query["limit"],
            "matches": reference_search(reference, query["query"], query["limit"]),
        }

    if query["kind"] == "departures":
        result = reference_departures(reference, query["stop_id"], query["date"], query["time"], query["limit"])
        return {
            "provider_id": provider_id,
            "stop": result["stop"],
            "service_date": query["date"],
            "query_time": query["time"],
            "departures": result["departures"],
        }

    if query["kind"] == "service_window":
        result = reference_service_window(reference, query["route_id"], query["date"])
        return {
            "provider_id": provider_id,
            "route": result["route"],
            "service_date": query["date"],
            "service_window": result["service_window"],
        }

    raise AssertionError(f"unknown query kind: {query['kind']}")


def test_provider_catalog_and_visible_http_queries(visible_reference, visible_seed):
    provider_id = visible_seed["provider_id"]
    with running_server(VISIBLE_DATA_ROOT) as base_url:
        providers_response = requests.get(f"{base_url}/v1/providers", timeout=5)
        providers_response.raise_for_status()
        providers = providers_response.json()["providers"]
        provider_ids = {provider["id"] for provider in providers}
        assert {"demo_static", "city_reference", "mta_static"} <= provider_ids

        mismatches = []
        for query in visible_seed["queries"]:
            actual = call_http(base_url, provider_id, query)
            expected = expected_result(visible_reference, provider_id, query)
            if actual != expected:
                mismatches.append({"query": query, "actual": actual, "expected": expected})
        assert not mismatches, json.dumps(mismatches, indent=2)


def test_visible_export_matches_reference_and_http(visible_reference, visible_seed):
    provider_id = visible_seed["provider_id"]
    export_payload = run_export(VISIBLE_DATA_ROOT)
    assert export_payload["provider_id"] == provider_id
    assert export_payload["query_count"] == len(visible_seed["queries"])
    assert len(export_payload["results"]) == len(visible_seed["queries"])

    mismatches = []
    for item in export_payload["results"]:
        expected = expected_result(visible_reference, provider_id, item["query"])
        if item["result"] != expected:
            mismatches.append({"query": item["query"], "actual": item["result"], "expected": expected})
    assert not mismatches, json.dumps(mismatches, indent=2)


def test_alternate_fixture_generalizes(tmp_path):
    alt_data_root = build_alternate_data_root(tmp_path)
    alt_reference = build_gtfs_reference(alt_data_root)
    alt_seed = json.loads((alt_data_root / "seed_queries.json").read_text(encoding="utf-8"))
    provider_id = alt_seed["provider_id"]

    with running_server(alt_data_root) as base_url:
        http_mismatches = []
        for query in alt_seed["queries"]:
            actual = call_http(base_url, provider_id, query)
            expected = expected_result(alt_reference, provider_id, query)
            if actual != expected:
                http_mismatches.append({"query": query, "actual": actual, "expected": expected})
        assert not http_mismatches, json.dumps(http_mismatches, indent=2)

    export_payload = run_export(alt_data_root)
    assert export_payload["provider_id"] == provider_id
    assert export_payload["query_count"] == len(alt_seed["queries"])
    export_mismatches = []
    for item in export_payload["results"]:
        expected = expected_result(alt_reference, provider_id, item["query"])
        if item["result"] != expected:
            export_mismatches.append({"query": item["query"], "actual": item["result"], "expected": expected})
    assert not export_mismatches, json.dumps(export_mismatches, indent=2)


def test_provider_audit_matches_reference_and_compare_root(tmp_path, visible_reference, visible_seed):
    alt_data_root = build_alternate_data_root(tmp_path)
    alt_reference = build_gtfs_reference(alt_data_root)
    alt_seed = json.loads((alt_data_root / "seed_queries.json").read_text(encoding="utf-8"))

    audit_payload = run_audit(VISIBLE_DATA_ROOT, compare_root=alt_data_root)
    assert audit_payload["baseline"]["provider"]["id"] == visible_seed["provider_id"]
    assert audit_payload["baseline"]["query_count"] == len(visible_seed["queries"])
    assert audit_payload["comparison"]["provider"]["id"] == alt_seed["provider_id"]
    assert audit_payload["comparison"]["query_count"] == len(alt_seed["queries"])

    baseline_mismatches = []
    for item in audit_payload["baseline"]["results"]:
        expected = expected_result(visible_reference, visible_seed["provider_id"], item["query"])
        if item["result"] != expected:
            baseline_mismatches.append({"query": item["query"], "actual": item["result"], "expected": expected})
    assert not baseline_mismatches, json.dumps(baseline_mismatches, indent=2)

    comparison_mismatches = []
    for item in audit_payload["comparison"]["results"]:
        expected = expected_result(alt_reference, alt_seed["provider_id"], item["query"])
        if item["result"] != expected:
            comparison_mismatches.append({"query": item["query"], "actual": item["result"], "expected": expected})
    assert not comparison_mismatches, json.dumps(comparison_mismatches, indent=2)


def test_provider_compare_matches_both_roots_in_one_process(tmp_path, visible_reference, visible_seed):
    alt_data_root = build_alternate_data_root(tmp_path)
    alt_reference = build_gtfs_reference(alt_data_root)
    alt_seed = json.loads((alt_data_root / "seed_queries.json").read_text(encoding="utf-8"))

    compare_payload = run_compare(VISIBLE_DATA_ROOT, alt_data_root)
    baseline_ids = [provider["id"] for provider in compare_payload["baseline"]["providers"]]
    comparison_ids = [provider["id"] for provider in compare_payload["comparison"]["providers"]]
    assert {"demo_static", "city_reference", "mta_static"} <= set(baseline_ids)
    assert {"demo_static", "city_reference", "mta_static"} <= set(comparison_ids)

    baseline_mismatches = []
    for item in compare_payload["baseline"]["results"]:
        expected = expected_result(visible_reference, visible_seed["provider_id"], item["query"])
        if item["result"] != expected:
            baseline_mismatches.append({"query": item["query"], "actual": item["result"], "expected": expected})
    assert not baseline_mismatches, json.dumps(baseline_mismatches, indent=2)

    comparison_mismatches = []
    for item in compare_payload["comparison"]["results"]:
        expected = expected_result(alt_reference, alt_seed["provider_id"], item["query"])
        if item["result"] != expected:
            comparison_mismatches.append({"query": item["query"], "actual": item["result"], "expected": expected})
    assert not comparison_mismatches, json.dumps(comparison_mismatches, indent=2)
