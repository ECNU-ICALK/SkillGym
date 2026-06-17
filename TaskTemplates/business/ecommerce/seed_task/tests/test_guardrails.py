from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path


ACCESS_LOG = Path("/var/log/ecommerce-recon/access.log")
PRE_VERIFIER_LOG = ACCESS_LOG.read_text(encoding="utf-8") if ACCESS_LOG.exists() else ""
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


def parse_graphql_body(record: dict) -> dict | None:
    body = record.get("body", "")
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def test_solver_used_live_service_chain_before_verifier() -> None:
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier service traffic was recorded"
    graphql = [r for r in records if r["method"] == "POST" and r["path"] == "/admin/graphql"]
    parsed_graphql = [(record, parse_graphql_body(record)) for record in graphql]
    order_calls = [
        payload for _, payload in parsed_graphql
        if payload and "orders" in payload.get("query", "")
    ]
    variant_calls = [
        payload for _, payload in parsed_graphql
        if payload and "productVariants" in payload.get("query", "")
    ]
    assert order_calls, "Solver did not query live orders"
    assert variant_calls, "Solver did not query live variants"
    paginated_orders = any(call.get("variables", {}).get("after") not in {None, ""} for call in order_calls)
    paginated_variants = any(call.get("variables", {}).get("after") not in {None, ""} for call in variant_calls)
    assert len(order_calls) >= 2 or paginated_orders, "Solver did not follow GraphQL pagination for orders"
    assert len(variant_calls) >= 2 or paginated_variants, "Solver did not follow GraphQL pagination for variants"
    assert any(r["path"].startswith("/warehouse/stock") for r in records), "Solver did not query warehouse stock"
    assert any(r["path"].startswith("/warehouse/reservations") for r in records), "Solver did not query warehouse reservations"
    assert any(r["path"].startswith("/carrier/track/") for r in records), "Solver did not query carrier tracking"


def test_inputs_and_hidden_service_were_not_modified() -> None:
    server_hash = hashlib.sha256(Path("/services/ecommerce-recon/server.py").read_bytes()).hexdigest()
    expected_server_hash = Path("/opt/ecommerce-recon-server.sha256").read_text(encoding="utf-8").strip()
    assert server_hash == expected_server_hash, "Hidden live service was modified"

    current = subprocess.check_output("find /root/data -type f -print0 | sort -z | xargs -0 sha256sum", shell=True, text=True)
    expected = Path("/opt/ecommerce-recon-data.sha256").read_text(encoding="utf-8")
    assert current == expected, "Input data under /root/data was modified"


def test_live_services_still_healthy() -> None:
    with urllib.request.urlopen("http://127.0.0.1:8123/health", timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "ecommerce-recon"


def test_stale_snapshot_was_not_used_as_sole_source() -> None:
    rows_path = Path("/root/output/fulfillment_exceptions.csv")
    text = rows_path.read_text(encoding="utf-8")
    assert "#H1008" in text, "The live-only order #H1008 is missing, suggesting stale snapshot dependence"
    assert "gid://shopify/LineItem/9009" in text, "The live-only HAT-CANVAS line item is missing"


def test_bound_reconciliation_workflow_was_consulted() -> None:
    skill_md = Path("/logs/agent/skills/commerce-fulfillment-recon/SKILL.md")
    if not skill_md.exists():
        return
    if not AGENT_LOG.exists():
        return
    text = AGENT_LOG.read_text(encoding="utf-8")
    assert "/logs/agent/skills/commerce-fulfillment-recon/SKILL.md" in text, (
        "Solver did not consult the bundled reconciliation workflow"
    )
