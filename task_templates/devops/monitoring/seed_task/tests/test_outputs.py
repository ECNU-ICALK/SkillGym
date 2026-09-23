#!/usr/bin/env python3
import hashlib
import json
import math
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.error import URLError

DATA_ROOT = Path("/app/data")
OUTPUT_PATH = Path("/app/output/monitoring_bundle_report.json")
INPUT_HASH_PATH = Path("/opt/monitoring-input.sha256")
PROFILES_PATH = Path("/services/metrics/service_profiles.json")
INVENTORY_DIR = Path("/app/workspace/prometheus/inventory")
RUNTIME_RELEASE_INVENTORY = Path("/app/runtime/inventory/release-bundle.json")

BUCKETS = [50.0, 100.0, 200.0, 350.0, 500.0, 750.0, 1000.0, 2000.0, math.inf]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def compute_hash_listing(root: Path) -> str:
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rel = path.relative_to(root).as_posix()
        lines.append(f"{digest}  {rel}")
    return "\n".join(lines) + "\n"


def api_query(expr: str) -> dict:
    params = urllib.parse.urlencode({"query": expr})
    with urllib.request.urlopen(f"http://127.0.0.1:9090/api/v1/query?{params}", timeout=5) as response:
        return json.load(response)


def query_vector(expr: str) -> dict[str, float]:
    payload = api_query(expr)
    assert payload["status"] == "success", expr
    values = {}
    for item in payload["data"]["result"]:
        service = item["metric"].get("service")
        if service:
            values[service] = float(item["value"][1])
    return values


def query_scalar(expr: str) -> float:
    payload = api_query(expr)
    assert payload["status"] == "success", expr
    rows = payload["data"]["result"]
    if not rows:
        return 0.0
    return float(rows[0]["value"][1])


def firing_alerts(severity: str) -> list[str]:
    payload = api_query(f'ALERTS{{alertstate="firing",severity="{severity}",bundle="release-2026-05-monitoring"}}')
    assert payload["status"] == "success"
    return sorted({row["metric"].get("service") for row in payload["data"]["result"] if row["metric"].get("service")})


def rules_payload() -> dict:
    with urllib.request.urlopen("http://127.0.0.1:9090/api/v1/rules", timeout=5) as response:
        return json.load(response)


def targets_payload() -> dict:
    with urllib.request.urlopen("http://127.0.0.1:9090/api/v1/targets", timeout=5) as response:
        return json.load(response)


def expected_latency_ms(fractions: list[float], quantile: float = 0.95) -> float:
    previous_fraction = 0.0
    previous_bucket = 0.0
    for bucket, fraction in zip(BUCKETS, fractions):
        if fraction >= quantile:
            if math.isinf(bucket):
                return previous_bucket
            if fraction == previous_fraction:
                return bucket
            ratio = (quantile - previous_fraction) / (fraction - previous_fraction)
            return previous_bucket + ratio * (bucket - previous_bucket)
        previous_fraction = fraction
        previous_bucket = bucket
    raise AssertionError("quantile not reached")


def wait_for_smoke_target():
    for _ in range(60):
        value = query_scalar('count(up{service="smoke-probe",bundle="release-2026-05-monitoring",lane="primary"} == 1)')
        if value >= 1:
            return
        time.sleep(0.5)
    raise AssertionError("smoke-probe was not discovered from new inventory file")


def wait_for_auxiliary_targets_to_settle():
    for _ in range(60):
        targets = targets_payload()
        assert targets["status"] == "success"
        active_targets = targets["data"]["activeTargets"]
        by_component = {
            row["labels"].get("component"): row
            for row in active_targets
        }
        smoke_ready = "smoke" in by_component
        canary_seen = "canary-smoke" in by_component
        orphan_seen = "orphan-smoke" in by_component
        if smoke_ready and not canary_seen and not orphan_seen:
            return
        time.sleep(0.5)
    raise AssertionError("auxiliary inventory targets were scraped or smoke target never settled")


def assert_close(actual: float, expected: float, tolerance: float, label: str) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")


def distinct_service_count(bundle_id: str) -> float:
    return query_scalar(f'count(count by (service) (up{{bundle="{bundle_id}",lane="primary"}} == 1))')


def matching_rule_names(rules: list[dict], keywords: tuple[str, ...]) -> list[str]:
    matches = []
    for rule in rules:
        name = (rule.get("name") or "").lower()
        if all(keyword in name for keyword in keywords):
            matches.append(rule["name"])
    return matches


def wait_for_recording_rule_services(rule_name: str, expected_services: list[str]) -> list[str]:
    for _ in range(30):
        payload = api_query(rule_name)
        assert payload["status"] == "success"
        services = sorted(
            {
                row["metric"].get("service")
                for row in payload["data"]["result"]
                if row["metric"].get("service")
            }
        )
        if services == sorted(expected_services):
            return services
        time.sleep(1)
    raise AssertionError((rule_name, services))


def ensure_bundle_running(
    bundle_id: str,
    summary_window: str,
    expected_services: list[str],
    expected_target_count: int,
    expected_rates: dict[str, float],
) -> None:
    try:
        ready_targets = query_scalar(f'count(up{{bundle="{bundle_id}"}} == 1)')
        request_rate = query_vector(
            f'sum by (service) (rate(harbor_http_requests_total{{bundle="{bundle_id}"}}[{summary_window}]))'
        )
        error_rate = query_vector(
            "100 * "
            f'sum by (service) (rate(harbor_http_requests_total{{bundle="{bundle_id}",code=~"5.."}}[{summary_window}])) '
            "/ "
            f'clamp_min(sum by (service) (rate(harbor_http_requests_total{{bundle="{bundle_id}"}}[{summary_window}])), 0.0001)'
        )
        latency = query_vector(
            f'1000 * histogram_quantile(0.95, '
            f'sum by (service, le) (rate(harbor_http_request_duration_seconds_bucket{{bundle="{bundle_id}"}}[{summary_window}])))'
        )
        if (
            ready_targets >= expected_target_count
            and all(service in request_rate for service in expected_services)
            and all(service in error_rate for service in expected_services)
            and all(service in latency for service in expected_services)
            and all(abs(request_rate[service] - expected_rates[service]) <= 0.5 for service in expected_services)
        ):
            return
    except URLError:
        pass

    subprocess.run(
        ["/bin/bash", "-lc", "/app/bin/start_bundle.sh"],
        check=True,
        capture_output=True,
        text=True,
    )
    for _ in range(40):
        try:
            ready_targets = query_scalar(f'count(up{{bundle="{bundle_id}"}} == 1)')
            request_rate = query_vector(
                f'sum by (service) (rate(harbor_http_requests_total{{bundle="{bundle_id}"}}[{summary_window}]))'
            )
            error_rate = query_vector(
                "100 * "
                f'sum by (service) (rate(harbor_http_requests_total{{bundle="{bundle_id}",code=~"5.."}}[{summary_window}])) '
                "/ "
                f'clamp_min(sum by (service) (rate(harbor_http_requests_total{{bundle="{bundle_id}"}}[{summary_window}])), 0.0001)'
            )
            latency = query_vector(
                f'1000 * histogram_quantile(0.95, '
                f'sum by (service, le) (rate(harbor_http_request_duration_seconds_bucket{{bundle="{bundle_id}"}}[{summary_window}])))'
            )
            if (
                ready_targets >= expected_target_count
                and all(service in request_rate for service in expected_services)
                and all(service in error_rate for service in expected_services)
                and all(service in latency for service in expected_services)
                and all(abs(request_rate[service] - expected_rates[service]) <= 0.5 for service in expected_services)
            ):
                return
        except URLError:
            pass
        time.sleep(1)
    raise AssertionError("bundle did not become query-ready during verifier bootstrap")


def main():
    assert OUTPUT_PATH.exists(), "missing report output"
    report = read_json(OUTPUT_PATH)
    contract = read_json(DATA_ROOT / "contracts" / "service_contract.json")
    alert_policy = read_json(DATA_ROOT / "contracts" / "alert_policy.json")
    summary_contract = read_json(DATA_ROOT / "contracts" / "summary_contract.json")
    profiles = read_json(PROFILES_PATH)
    expected_services = contract["services"]
    bundle_id = summary_contract["target_bundle_label"]
    target_lane = summary_contract["target_lane_label"]
    summary_window = summary_contract["summary_window"]
    latency_quantile = summary_contract["histogram_quantile"]
    expected_target_count = len(read_json(RUNTIME_RELEASE_INVENTORY))
    expected_rates = {service: float(profiles[service]["request_rate_rps"]) for service in expected_services}
    ensure_bundle_running(bundle_id, summary_window, expected_services, expected_target_count, expected_rates)

    assert report["bundle_id"] == "release-2026-05-monitoring"
    assert report["monitoring_ready"] is True
    assert sorted(report["services"].keys()) == sorted(expected_services)
    assert report["healthy_target_count"] == 4

    current_hash_listing = compute_hash_listing(DATA_ROOT)
    baseline_hash_listing = INPUT_HASH_PATH.read_text(encoding="utf-8")
    assert current_hash_listing == baseline_hash_listing, "input data changed"

    request_rate = query_vector(
        f'sum by (service) (rate(harbor_http_requests_total{{bundle="{bundle_id}",lane="{target_lane}"}}[{summary_window}]))'
    )
    error_rate = query_vector(
        "100 * "
        f'sum by (service) (rate(harbor_http_requests_total{{bundle="{bundle_id}",lane="{target_lane}",code=~"5.."}}[{summary_window}])) '
        "/ "
        f'clamp_min(sum by (service) (rate(harbor_http_requests_total{{bundle="{bundle_id}",lane="{target_lane}"}}[{summary_window}])), 0.0001)'
    )
    latency = query_vector(
        f'1000 * histogram_quantile({latency_quantile}, '
        f'sum by (service, le) (rate(harbor_http_request_duration_seconds_bucket{{bundle="{bundle_id}",lane="{target_lane}"}}[{summary_window}])))'
    )

    assert "shadow-target" not in request_rate, "shadow target should not be included"
    assert distinct_service_count(bundle_id) == 4
    assert query_scalar(f'count(up{{bundle="{bundle_id}",lane="{target_lane}"}} == 1)') == 5
    assert query_scalar(f'count(up{{bundle="{bundle_id}",lane="{target_lane}",service="shadow-target"}} == 1)') == 0

    targets = targets_payload()
    assert targets["status"] == "success"
    active_targets = targets["data"]["activeTargets"]
    expected_scrape_urls = {}
    for entry in read_json(RUNTIME_RELEASE_INVENTORY):
        labels = entry["labels"]
        expected_scrape_urls[labels["component"]] = (
            f"http://127.0.0.1:{labels['metrics_port']}{labels['metrics_path']}"
        )
    observed_scrape_urls = {
        row["labels"].get("component"): row["scrapeUrl"]
        for row in active_targets
        if row["labels"].get("bundle") == bundle_id and row["labels"].get("lane") == target_lane
    }
    assert observed_scrape_urls == expected_scrape_urls

    for service in expected_services:
        service_profile = profiles[service]
        expected_rps = service_profile["request_rate_rps"]
        expected_error = service_profile["error_rate_pct"]
        expected_p95 = expected_latency_ms(service_profile["latency_fractions"])
        assert service in request_rate, f"missing request rate for {service}"
        assert service in error_rate, f"missing error rate for {service}"
        assert service in latency, f"missing latency for {service}"
        assert_close(request_rate[service], expected_rps, 0.5, f"{service} request rate")
        assert_close(error_rate[service], expected_error, 0.35, f"{service} error rate")
        assert_close(latency[service], expected_p95, 75.0, f"{service} p95 latency")

        row = report["services"][service]
        assert_close(row["request_rate_rps"], expected_rps, 0.5, f"{service} report rps")
        assert_close(row["error_rate_pct"], expected_error, 0.35, f"{service} report error")
        assert_close(row["p95_latency_ms"], expected_p95, 75.0, f"{service} report p95")

    expected_page = []
    expected_ticket = []
    for service in expected_services:
        service_profile = profiles[service]
        expected_p95 = expected_latency_ms(service_profile["latency_fractions"])
        if (
            service_profile["error_rate_pct"] > alert_policy["error_rate_pct"]["page"]
            or expected_p95 > alert_policy["p95_latency_ms"]["page"]
        ):
            expected_page.append(service)
        elif (
            service_profile["error_rate_pct"] > alert_policy["error_rate_pct"]["ticket"]
            or expected_p95 > alert_policy["p95_latency_ms"]["ticket"]
        ):
            expected_ticket.append(service)

    assert sorted(expected_page) == ["harbor-jobservice"]
    assert sorted(expected_ticket) == ["harbor-registry"]
    assert report["page_alerts"] == sorted(expected_page)
    assert report["ticket_alerts"] == sorted(expected_ticket)
    assert report["services"]["harbor-jobservice"]["slo_state"] == "page"
    assert report["services"]["harbor-registry"]["slo_state"] == "ticket"
    assert report["services"]["harbor-core"]["slo_state"] == "healthy"
    assert report["services"]["harbor-exporter"]["slo_state"] == "healthy"

    promtool_config = subprocess.run(
        ["promtool", "check", "config", "/app/workspace/prometheus/bundle/prometheus.yml"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "SUCCESS" in promtool_config.stdout.upper()
    subprocess.run(
        ["promtool", "check", "rules", "/app/workspace/prometheus/rules/recording_rules.yml"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["promtool", "check", "rules", "/app/workspace/prometheus/rules/alert_rules.yml"],
        check=True,
        capture_output=True,
        text=True,
    )

    for rule_name in [
        "harbor:up:sum",
        "harbor:service_request_rate_rps",
        "harbor:service_error_rate_pct",
        "harbor:service_p95_latency_ms"
    ]:
        payload = api_query(rule_name)
        assert payload["status"] == "success"

    rules = rules_payload()
    assert rules["status"] == "success"
    groups = rules["data"]["groups"]
    recording_rule_names = []
    alert_rules = []
    for group in groups:
        for rule in group.get("rules", []):
            labels = rule.get("labels") or {}
            if rule.get("type") == "recording" and rule.get("name"):
                recording_rule_names.append(rule["name"])
            alert_rules.append(
                {
                    "name": (rule.get("name") or rule.get("alert") or "").lower(),
                    "query": (rule.get("query") or "").lower(),
                    "severity": (labels.get("severity") or "").lower(),
                }
            )

    def has_alert_rule(severity: str, keyword: str) -> bool:
        for rule in alert_rules:
            if rule["severity"] != severity:
                continue
            if keyword in rule["name"] or keyword in rule["query"]:
                return True
        return False

    assert has_alert_rule("page", "error"), "missing page-level error alert"
    assert has_alert_rule("page", "latency"), "missing page-level latency alert"
    assert has_alert_rule("ticket", "error"), "missing ticket-level error alert"
    assert has_alert_rule("ticket", "latency"), "missing ticket-level latency alert"

    for keywords in [
        ("request", "rate"),
        ("error", "rate"),
        ("latency",),
    ]:
        candidate_names = matching_rule_names(
            [{"name": name} for name in recording_rule_names],
            keywords,
        )
        assert candidate_names, f"missing recording rule for {keywords}"
        wait_for_recording_rule_services(candidate_names[0], expected_services)

    original_report = read_json(OUTPUT_PATH)
    subprocess.run(["python3", "/app/bin/render_report.py"], check=True)
    rerendered_report = read_json(OUTPUT_PATH)
    assert original_report["bundle_id"] == rerendered_report["bundle_id"]
    assert original_report["monitoring_ready"] == rerendered_report["monitoring_ready"]
    assert original_report["page_alerts"] == rerendered_report["page_alerts"]
    assert original_report["ticket_alerts"] == rerendered_report["ticket_alerts"]
    assert sorted(original_report["services"].keys()) == sorted(rerendered_report["services"].keys())
    for service in original_report["services"]:
        before = original_report["services"][service]
        after = rerendered_report["services"][service]
        assert before["slo_state"] == after["slo_state"]
        assert_close(after["request_rate_rps"], before["request_rate_rps"], 0.5, f"{service} rerender rps")
        assert_close(after["error_rate_pct"], before["error_rate_pct"], 0.35, f"{service} rerender error")
        assert_close(after["p95_latency_ms"], before["p95_latency_ms"], 75.0, f"{service} rerender p95")

    smoke_manifest = """- targets:
  - 127.0.0.1:18086
  labels:
    service_name: smoke-probe
    component: smoke
    team: observability
    metrics_port: "18086"
    metrics_path: /probe/metrics
    lane: primary
    bundle: release-2026-05-monitoring
"""
    (INVENTORY_DIR / "smoke-bundle.yml").write_text(smoke_manifest, encoding="utf-8")
    canary_manifest = json.dumps(
        [
            {
                "targets": ["127.0.0.1:18086"],
                "labels": {
                    "service_name": "canary-probe",
                    "component": "canary-smoke",
                    "team": "observability",
                    "metrics_port": "18086",
                    "metrics_path": "/probe/metrics",
                    "lane": "canary",
                    "bundle": "release-2026-05-monitoring",
                },
            }
        ],
        indent=2,
    )
    (INVENTORY_DIR / "canary-bundle.json").write_text(canary_manifest, encoding="utf-8")
    orphan_manifest = json.dumps(
        [
            {
                "targets": ["127.0.0.1:18086"],
                "labels": {
                    "component": "orphan-smoke",
                    "team": "observability",
                    "metrics_port": "18086",
                    "metrics_path": "/probe/metrics",
                    "lane": "primary",
                    "bundle": "release-2026-05-monitoring",
                },
            }
        ],
        indent=2,
    )
    (INVENTORY_DIR / "orphan-bundle.json").write_text(orphan_manifest, encoding="utf-8")
    wait_for_smoke_target()
    wait_for_auxiliary_targets_to_settle()
    assert query_scalar(f'count(up{{bundle="{bundle_id}",lane="canary"}} == 1)') == 0
    assert query_scalar(f'count(up{{bundle="{bundle_id}",lane="{target_lane}",component="orphan-smoke"}} == 1)') == 0


if __name__ == "__main__":
    main()
