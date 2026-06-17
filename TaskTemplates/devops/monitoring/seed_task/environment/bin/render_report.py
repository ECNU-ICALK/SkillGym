#!/usr/bin/env python3
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:9090"
OUTPUT_PATH = Path("/app/output/monitoring_bundle_report.json")
SERVICE_CONTRACT = Path("/app/data/contracts/service_contract.json")
SUMMARY_CONTRACT = Path("/app/data/contracts/summary_contract.json")
ALERT_POLICY = Path("/app/data/contracts/alert_policy.json")
DEBUG_PATH = Path("/app/runtime/logs/render-report-debug.json")
RELEASE_INVENTORY = Path("/app/runtime/inventory/release-bundle.json")
SERVICE_PROFILES = Path("/services/metrics/service_profiles.json")


def api_query(expr: str) -> dict:
    params = urllib.parse.urlencode({"query": expr})
    with urllib.request.urlopen(f"{BASE_URL}/api/v1/query?{params}", timeout=5) as response:
        return json.load(response)


def api_get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=5) as response:
        return json.load(response)


def query_vector(expr: str) -> dict:
    payload = api_query(expr)
    if payload["status"] != "success":
        raise RuntimeError(f"query failed: {expr}")
    results = {}
    for item in payload["data"]["result"]:
        service = item["metric"].get("service")
        if service:
            results[service] = float(item["value"][1])
    return results


def expr_request_rate(bundle: str, lane: str, window: str) -> str:
    return (
        f'sum by (service, lane) '
        f'(rate(harbor_http_requests_total{{bundle="{bundle}",lane="{lane}"}}[{window}]))'
    )


def expr_error_rate(bundle: str, lane: str, window: str) -> str:
    return (
        f'100 * sum by (service, lane) '
        f'(rate(harbor_http_requests_total{{bundle="{bundle}",lane="{lane}",code=~"5.."}}[{window}])) '
        f'/ clamp_min(sum by (service, lane) '
        f'(rate(harbor_http_requests_total{{bundle="{bundle}",lane="{lane}"}}[{window}])), 0.0001)'
    )


def expr_p95_latency(bundle: str, lane: str, window: str) -> str:
    return (
        f'1000 * histogram_quantile(0.95, '
        f'sum by (service, lane, le) '
        f'(rate(harbor_http_request_duration_seconds_bucket{{bundle="{bundle}",lane="{lane}"}}[{window}])))'
    )


def query_scalar(expr: str) -> float:
    payload = api_query(expr)
    if payload["status"] != "success":
        raise RuntimeError(f"scalar query failed: {expr}")
    result = payload["data"]["result"]
    if not result:
        return 0.0
    return float(result[0]["value"][1])


def healthy_service_count(bundle: str, lane: str) -> int:
    return int(query_scalar(f'count(count by (service) (up{{bundle="{bundle}",lane="{lane}"}} == 1))'))


def within_tolerance(actual: float, expected: float, tolerance: float) -> bool:
    return abs(actual - expected) <= tolerance


def wait_for_values(
    bundle: str,
    lane: str,
    window: str,
    expected_services: list[str],
    expected_target_count: int,
    expected_rates: dict[str, float],
) -> None:
    for _ in range(120):
        healthy = query_scalar(f'count(up{{bundle="{bundle}",lane="{lane}"}} == 1)')
        request_rate = query_vector(expr_request_rate(bundle, lane, window))
        error_rate = query_vector(expr_error_rate(bundle, lane, window))
        latency = query_vector(expr_p95_latency(bundle, lane, window))
        if (
            healthy >= expected_target_count
            and all(name in request_rate for name in expected_services)
            and all(name in error_rate for name in expected_services)
            and all(name in latency for name in expected_services)
            and all(within_tolerance(request_rate[name], expected_rates[name], 0.5) for name in expected_services)
        ):
            return
        time.sleep(1.0)
    DEBUG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEBUG_PATH.write_text(
        json.dumps(
            {
                "bundle": bundle,
                "lane": lane,
                "window": window,
                "expected_services": expected_services,
                "targets": api_get("/api/v1/targets"),
                "query_up": api_query(f'up{{bundle="{bundle}",lane="{lane}"}}'),
                "query_request_rate": api_query(expr_request_rate(bundle, lane, window)),
                "query_error_rate": api_query(expr_error_rate(bundle, lane, window)),
                "query_latency": api_query(expr_p95_latency(bundle, lane, window))
            },
            indent=2,
            sort_keys=True
        ) + "\n",
        encoding="utf-8",
    )
    raise RuntimeError("bundle values did not become ready in time")


def main() -> None:
    contract = json.loads(SERVICE_CONTRACT.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY_CONTRACT.read_text(encoding="utf-8"))
    alert_policy = json.loads(ALERT_POLICY.read_text(encoding="utf-8"))
    bundle = summary["target_bundle_label"]
    lane = summary["target_lane_label"]
    window = summary["summary_window"]
    services = contract["services"]
    expected_target_count = len(json.loads(RELEASE_INVENTORY.read_text(encoding="utf-8")))
    profiles = json.loads(SERVICE_PROFILES.read_text(encoding="utf-8"))
    expected_rates = {service: float(profiles[service]["request_rate_rps"]) for service in services}
    wait_for_values(bundle, lane, window, services, expected_target_count, expected_rates)
    request_rate = query_vector(expr_request_rate(bundle, lane, window))
    error_rate = query_vector(expr_error_rate(bundle, lane, window))
    latency = query_vector(expr_p95_latency(bundle, lane, window))
    page_alerts = []
    ticket_alerts = []
    report = {
        "bundle_id": summary["bundle_id"],
        "monitoring_ready": True,
        "healthy_target_count": healthy_service_count(bundle, lane),
        "services": {},
        "page_alerts": page_alerts,
        "ticket_alerts": ticket_alerts
    }
    for service in services:
        rps = request_rate.get(service)
        err = error_rate.get(service)
        p95 = latency.get(service)
        if any(v is None or not math.isfinite(v) for v in (rps, err, p95)):
            DEBUG_PATH.parent.mkdir(parents=True, exist_ok=True)
            DEBUG_PATH.write_text(
                json.dumps(
                    {
                        "bundle": bundle,
                        "window": window,
                        "service": service,
                        "request_rate": request_rate,
                        "error_rate": error_rate,
                        "latency": latency
                    },
                    indent=2,
                    sort_keys=True
                ) + "\n",
                encoding="utf-8",
            )
            raise RuntimeError(f"missing summary values for {service}")
        if (
            err > alert_policy["error_rate_pct"]["page"]
            or p95 > alert_policy["p95_latency_ms"]["page"]
        ):
            page_alerts.append(service)
            state = "page"
        elif (
            err > alert_policy["error_rate_pct"]["ticket"]
            or p95 > alert_policy["p95_latency_ms"]["ticket"]
        ):
            ticket_alerts.append(service)
            state = "ticket"
        else:
            state = "healthy"
        report["services"][service] = {
            "request_rate_rps": round(rps, 3),
            "error_rate_pct": round(err, 3),
            "p95_latency_ms": round(p95, 3),
            "slo_state": state
        }
    report["page_alerts"] = sorted(page_alerts)
    report["ticket_alerts"] = sorted(ticket_alerts)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
