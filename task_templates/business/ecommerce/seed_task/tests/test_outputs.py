from __future__ import annotations

import csv
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


OUTPUT_DIR = Path("/root/output")
CSV_PATH = OUTPUT_DIR / "fulfillment_exceptions.csv"
SUMMARY_PATH = OUTPUT_DIR / "order_reconciliation_summary.json"
MANIFEST_PATH = Path("/root/data/merchant_manifest.json")
CATALOG_PATH = Path("/root/data/catalog_export.csv")

REQUIRED_FIELDS = [
    "order_id",
    "order_name",
    "line_item_id",
    "sku",
    "variant_id",
    "issue_code",
    "severity",
    "expected_action",
    "evidence",
]

ISSUES = [
    "SKU_VARIANT_DRIFT",
    "FULFILLMENT_SERVICE_MISMATCH",
    "INSUFFICIENT_AVAILABLE_STOCK",
    "STALE_OR_CONFLICTING_TRACKING",
    "MISSING_TRACKING_FOR_SHIPPED_ITEM",
]

ALLOWED_SEVERITY = {"critical", "high", "medium"}
ALLOWED_ACTIONS = {"hold_order", "correct_sku_mapping", "reroute_fulfillment", "refresh_tracking", "manual_review"}

ORDERS_QUERY = "query Orders($first: Int!, $after: String, $start: String, $end: String) { orders(first: $first, after: $after, start: $start, end: $end) { edges { cursor node { id name processedAt financialStatus cancelledAt lineItems } } pageInfo { hasNextPage endCursor } } }"
VARIANTS_QUERY = "query Variants($first: Int!, $after: String, $sku: String, $activeOnly: Boolean) { productVariants(first: $first, after: $after, sku: $sku, activeOnly: $activeOnly) { edges { cursor node { id sku active inventoryItemId fulfillmentService } } pageInfo { hasNextPage endCursor } } }"


def post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Client": "verifier-main"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"X-Client": "verifier-main"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def paginate_graphql(url: str, query: str, root: str, variables: dict) -> list[dict]:
    out = []
    after = None
    while True:
        merged = dict(variables)
        merged["after"] = after
        payload = post_json(url, {"query": query, "variables": merged})
        connection = payload["data"][root]
        out.extend(edge["node"] for edge in connection["edges"])
        if not connection["pageInfo"]["hasNextPage"]:
            return out
        after = connection["pageInfo"]["endCursor"]


def read_catalog() -> dict[str, dict]:
    with CATALOG_PATH.open(newline="", encoding="utf-8") as fh:
        return {row["sku"]: row for row in csv.DictReader(fh)}


def normalize_action(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    aliases = {
        "hold_order": "hold_order",
        "place_hold": "hold_order",
        "hold_and_rebalance_inventory_before_release": "hold_order",
        "hold_and_rebalance_inventory": "hold_order",
        "hold_until_stock_is_reallocated_or_replenished": "hold_order",
        "hold_until_stock_is_freed_or_replenished": "hold_order",
        "hold_for_stock_review": "hold_order",
        "hold_until_inventory_is_reallocated": "hold_order",
        "hold_until_inventory_is_resolved": "hold_order",
        "hold_until_inventory_resolved": "hold_order",
        "hold_for_inventory_review": "hold_order",
        "hold_for_restock_or_reallocation": "hold_order",
        "correct_sku_mapping": "correct_sku_mapping",
        "resolve_catalog_variant": "correct_sku_mapping",
        "resolve_variant": "correct_sku_mapping",
        "resolve_active_variant_mapping": "correct_sku_mapping",
        "correct_variant_mapping": "correct_sku_mapping",
        "confirm_the_correct_active_variant_before_release": "correct_sku_mapping",
        "confirm_variant_before_release": "correct_sku_mapping",
        "confirm_variant_mapping_before_release": "correct_sku_mapping",
        "correct_variant_before_release": "correct_sku_mapping",
        "correct_sku_variant_mapping_before_release": "correct_sku_mapping",
        "hold_and_correct_the_sku_to_variant_mapping": "correct_sku_mapping",
        "review_variant_mapping_before_release": "correct_sku_mapping",
        "resolve_variant_mapping": "correct_sku_mapping",
        "verify_variant_mapping_before_release": "correct_sku_mapping",
        "reroute_fulfillment": "reroute_fulfillment",
        "reroute_to_expected_service": "reroute_fulfillment",
        "reroute_to_expected_fulfillment_service": "reroute_fulfillment",
        "reroute_the_sku_to_the_expected_fulfillment_service": "reroute_fulfillment",
        "fix_fulfillment_routing_before_release": "reroute_fulfillment",
        "hold_and_reroute_to_the_expected_fulfillment_service": "reroute_fulfillment",
        "correct_fulfillment_routing_before_release": "reroute_fulfillment",
        "correct_fulfillment_routing": "reroute_fulfillment",
        "correct_fulfillment_route": "reroute_fulfillment",
        "refresh_tracking": "refresh_tracking",
        "rebuild_tracking_record": "refresh_tracking",
        "attach_a_valid_tracking_record_or_correct_the_fulfillment_state": "refresh_tracking",
        "add_or_correct_tracking_before_release": "refresh_tracking",
        "refresh_fulfillment_tracking_and_confirm_the_carrier_record": "refresh_tracking",
        "audit_shipment_and_add_valid_tracking": "refresh_tracking",
        "add_valid_tracking": "refresh_tracking",
        "obtain_valid_tracking": "refresh_tracking",
        "recover_valid_tracking_record": "refresh_tracking",
        "recover_or_recreate_tracking_record": "refresh_tracking",
        "refresh_tracking_record": "refresh_tracking",
        "refresh_or_attach_valid_tracking": "refresh_tracking",
        "restore_carrier_tracking_before_release": "refresh_tracking",
        "manual_review": "manual_review",
        "reconcile_shipment_status": "manual_review",
        "reconcile_admin_delivery_state": "manual_review",
        "reconcile_admin_and_carrier_status": "manual_review",
        "reconcile_the_admin_fulfillment_status_with_the_carrier_event": "manual_review",
        "reconcile_admin_fulfillment_and_carrier_status": "manual_review",
        "review_fulfillment_state_and_reconcile_the_admin_timeline": "manual_review",
        "review_tracking_admin_status_mismatch": "manual_review",
        "reconcile_fulfillment_status": "manual_review",
        "reconcile_admin_with_carrier": "manual_review",
        "reconcile_admin_fulfillment_with_carrier_status": "manual_review",
        "reconcile_admin_fulfillment_state": "manual_review",
    }
    if normalized in aliases:
        return aliases[normalized]

    terms = set(normalized.split("_"))
    if "hold" in terms and {"stock", "inventory", "restock", "reallocation"} & terms:
        return "hold_order"
    if "reroute" in terms and {"service", "fulfillment"} & terms:
        return "reroute_fulfillment"
    if {"variant", "sku", "catalog"} & terms and {"mapping", "correct", "resolve", "confirm"} & terms:
        return "correct_sku_mapping"
    if "tracking" in terms and {"refresh", "recover", "recreate", "obtain", "record", "valid"} & terms:
        return "refresh_tracking"
    if {"reconcile", "review"} & terms and {"admin", "carrier", "delivery", "fulfillment", "status"} & terms:
        return "manual_review"
    return normalized


def canonical_summary_window(summary: dict) -> dict:
    window = summary["window"]
    return {
        "start": window["start"],
        "end": window["end"],
    }


def canonical_summary_totals(summary: dict, rows: list[dict]) -> dict:
    totals = summary["totals"]

    def first_present(*keys: str, default: int | None = None) -> int:
        for key in keys:
            if key in totals:
                return int(totals[key])
        if default is not None:
            return default
        raise AssertionError(f"Summary totals missing all aliases for {keys}")

    return {
        "orders_checked": first_present(
            "orders_checked",
            "paid_shippable_orders_reviewed",
            "paid_shippable_orders_checked",
            "paid_active_orders_reviewed",
        ),
        "line_items_checked": first_present(
            "line_items_checked",
            "paid_shippable_line_items_reviewed",
            "shippable_line_items_checked",
            "paid_shippable_line_items_checked",
        ),
        "orders_with_exceptions": first_present(
            "orders_with_exceptions",
            default=len({row["order_id"] for row in rows}),
        ),
        "exception_rows": first_present("exception_rows"),
    }


def summary_has_required_source_checks(summary: dict) -> None:
    source_checks = summary["source_checks"]
    assert isinstance(source_checks, dict), "source_checks must be an object"

    commerce = source_checks.get("commerce_admin")
    if commerce is None:
        commerce = source_checks.get("commerce_admin_graphql")
    warehouse = source_checks.get("warehouse_reservations")
    if warehouse is None:
        warehouse = source_checks.get("warehouse")
    carrier = source_checks.get("carrier_tracking")

    def is_present(value: object) -> bool:
        if value is None or value is False:
            return False
        return True

    assert is_present(commerce), "summary must record commerce admin checks"
    assert is_present(warehouse), "summary must record warehouse checks"
    assert is_present(carrier), "summary must record carrier tracking checks"


def normalize_sources(values: list[str]) -> set[str]:
    aliases = {
        "commerce_admin": "commerce_admin",
        "commerce_admin_graphql": "commerce_admin",
        "catalog_export": "catalog_export",
        "catalog_live": "commerce_admin",
        "order_snapshot_reference_only": "order_snapshot_reference_only",
        "warehouse_reservations": "warehouse_reservations",
        "warehouse_stock": "warehouse_reservations",
        "carrier_tracking": "carrier_tracking",
        "carrier_status_codes": "carrier_tracking",
        "carrier_status_reference": "carrier_tracking",
    }
    normalized = set()
    for value in values:
        normalized.add(aliases.get(value.strip().lower(), value.strip().lower()))
    return normalized


def expected_rows_and_summary() -> tuple[list[dict], dict]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    catalog = read_catalog()
    window = manifest["reconciliation_window"]
    graphql_url = manifest["service_urls"]["commerce_admin_graphql"]
    warehouse_url = manifest["service_urls"]["warehouse"]
    carrier_url = manifest["service_urls"]["carrier_tracking"]

    orders = paginate_graphql(
        graphql_url,
        ORDERS_QUERY,
        "orders",
        {"first": 3, "start": window["start"], "end": window["end"]},
    )
    variant_cache: dict[str, list[dict]] = {}
    expected: list[dict] = []
    orders_checked = 0
    line_items_checked = 0

    def add(order: dict, item: dict, code: str, severity: str, action: str) -> None:
        expected.append({
            "order_id": order["id"],
            "order_name": order["name"],
            "line_item_id": item["id"],
            "sku": item["sku"],
            "variant_id": item["variantId"],
            "issue_code": code,
            "severity": severity,
            "expected_action": action,
        })

    for order in orders:
        shippable = [li for li in order["lineItems"] if li.get("requiresShipping")]
        if order["financialStatus"] != "PAID" or order.get("cancelledAt") or not shippable:
            continue
        orders_checked += 1
        for item in shippable:
            line_items_checked += 1
            sku = item["sku"]
            variant_cache.setdefault(
                sku,
                paginate_graphql(graphql_url, VARIANTS_QUERY, "productVariants", {"first": 20, "sku": sku, "activeOnly": True}),
            )
            variants = variant_cache[sku]
            resolved = variants[0] if len(variants) == 1 else None
            if len(variants) != 1 or (resolved and resolved["id"] != item["variantId"]):
                add(order, item, "SKU_VARIANT_DRIFT", "critical", "correct_sku_mapping")
                continue

            expected_service = catalog.get(sku, {}).get("expected_fulfillment_service")
            if expected_service and resolved["fulfillmentService"] != expected_service:
                add(order, item, "FULFILLMENT_SERVICE_MISMATCH", "high", "reroute_fulfillment")

            unfulfilled = int(item.get("unfulfilledQuantity") or 0)
            inv = resolved["inventoryItemId"]
            if unfulfilled > 0:
                encoded = urllib.parse.urlencode({"inventory_item_id": inv})
                stock = get_json(f"{warehouse_url}/stock?{encoded}") or {}
                reservations = get_json(f"{warehouse_url}/reservations?{encoded}") or {"reservations": []}
                reserved_qty = sum(int(r["quantity"]) for r in reservations.get("reservations", []) if r.get("status") == "open")
                available = int(stock.get("on_hand", 0)) - reserved_qty
                if available < unfulfilled:
                    add(order, item, "INSUFFICIENT_AVAILABLE_STOCK", "critical", "hold_order")

            status = item.get("fulfillmentStatus")
            tracking = item.get("trackingNumber")
            if status in {"FULFILLED", "SHIPPED", "IN_TRANSIT"}:
                carrier = get_json(f"{carrier_url}/track/{urllib.parse.quote(str(tracking or ''))}") if tracking else None
                if not carrier:
                    add(order, item, "MISSING_TRACKING_FOR_SHIPPED_ITEM", "medium", "refresh_tracking")
                elif status in {"UNFULFILLED", "PARTIAL", "IN_TRANSIT"} and carrier.get("latest_status") in {"delivered", "cancelled", "exception"}:
                    add(order, item, "STALE_OR_CONFLICTING_TRACKING", "high", "manual_review")

    counts = Counter(row["issue_code"] for row in expected)
    summary = {
        "window": {"start": window["start"], "end": window["end"]},
        "totals": {
            "orders_checked": orders_checked,
            "line_items_checked": line_items_checked,
            "orders_with_exceptions": len({row["order_id"] for row in expected}),
            "exception_rows": len(expected),
        },
        "issue_counts": {issue: counts.get(issue, 0) for issue in ISSUES},
        "source_checks": {
            "commerce_admin": True,
            "warehouse_reservations": True,
            "carrier_tracking": True,
        },
    }
    return sorted(expected, key=lambda r: (r["order_id"], r["line_item_id"], r["issue_code"])), summary


def read_submission() -> tuple[list[dict], dict]:
    assert CSV_PATH.exists(), "Missing /root/output/fulfillment_exceptions.csv"
    assert SUMMARY_PATH.exists(), "Missing /root/output/order_reconciliation_summary.json"
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames is not None, "CSV must include a header row"
        missing = [field for field in REQUIRED_FIELDS if field not in reader.fieldnames]
        assert not missing, f"CSV is missing required columns: {missing}"
        rows = list(reader)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    return rows, summary


def test_output_files_exist_and_parse() -> None:
    rows, summary = read_submission()
    assert isinstance(rows, list)
    assert isinstance(summary, dict)
    assert "totals" in summary
    assert "issue_counts" in summary


def test_exception_rows_match_live_recomputation() -> None:
    rows, _ = read_submission()
    expected, _ = expected_rows_and_summary()
    comparison_fields = [
        "order_id",
        "order_name",
        "line_item_id",
        "sku",
        "variant_id",
        "issue_code",
    ]
    comparable = sorted(
        [
            {
                **{key: row[key] for key in comparison_fields},
            }
            for row in rows
        ],
        key=lambda r: (r["order_id"], r["line_item_id"], r["issue_code"]),
    )
    expected_comparable = sorted(
        [
            {
                **{key: row[key] for key in comparison_fields},
            }
            for row in expected
        ],
        key=lambda r: (r["order_id"], r["line_item_id"], r["issue_code"]),
    )
    assert comparable == expected_comparable


def test_summary_matches_csv_and_live_recomputation() -> None:
    rows, summary = read_submission()
    _, expected_summary = expected_rows_and_summary()
    assert canonical_summary_window(summary) == expected_summary["window"]
    assert canonical_summary_totals(summary, rows) == expected_summary["totals"]
    assert summary["issue_counts"] == expected_summary["issue_counts"]
    summary_has_required_source_checks(summary)
    totals = canonical_summary_totals(summary, rows)
    assert totals["exception_rows"] == len(rows)
    assert totals["orders_with_exceptions"] == len({row["order_id"] for row in rows})


def test_schema_values_and_evidence_quality() -> None:
    rows, summary = read_submission()
    assert set(summary["issue_counts"]) == set(ISSUES)
    assert rows, "Expected at least one exception row"
    for row in rows:
        assert row["issue_code"] in ISSUES
        assert row["severity"] in ALLOWED_SEVERITY
        assert normalize_action(row["expected_action"]) in ALLOWED_ACTIONS
        evidence = json.loads(row["evidence"])
        assert isinstance(evidence, dict), "evidence must decode to a JSON object"
        checked_sources = evidence.get("checked_sources")
        if checked_sources is None:
            checked_sources = evidence.get("checked_systems")
        assert isinstance(checked_sources, list) and checked_sources, "evidence must record checked_sources"
        allowed_sources = {
            "commerce_admin",
            "commerce_admin_graphql",
            "catalog_export",
            "order_snapshot_reference_only",
            "warehouse_reservations",
            "warehouse_stock",
            "carrier_tracking",
            "carrier_status_codes",
            "carrier_status_reference",
        }
        assert set(checked_sources).issubset(allowed_sources)
        linked_ids = {
            str(value)
            for key, value in evidence.items()
            if key.endswith("_id") or "tracking" in key.lower() or key == "sku"
        }
        assert linked_ids, "evidence must retain at least one source identifier"
        normalized_sources = normalize_sources(checked_sources)
        if row["issue_code"] == "SKU_VARIANT_DRIFT":
            variant_keys = {key for key in evidence if "variant" in key.lower()}
            assert variant_keys, "variant drift rows must include variant evidence"
            assert "commerce_admin" in normalized_sources
        elif row["issue_code"] == "FULFILLMENT_SERVICE_MISMATCH":
            routing_keys = {key for key in evidence if "fulfillment" in key.lower() or "service" in key.lower()}
            assert routing_keys, "fulfillment mismatch rows must include routing evidence"
            assert "catalog_export" in normalized_sources
            assert "commerce_admin" in normalized_sources
        elif row["issue_code"] == "INSUFFICIENT_AVAILABLE_STOCK":
            stock_keys = {key for key in evidence if "stock" in key.lower() or "quantity" in key.lower() or "reservation" in key.lower()}
            assert stock_keys, "stock issue rows must include stock or reservation evidence"
            assert "warehouse_reservations" in normalized_sources
        elif row["issue_code"] == "STALE_OR_CONFLICTING_TRACKING":
            tracking_keys = {key for key in evidence if "tracking" in key.lower() or "carrier" in key.lower() or "status" in key.lower()}
            assert tracking_keys, "tracking conflict rows must include shipment evidence"
            assert "carrier_tracking" in normalized_sources
        elif row["issue_code"] == "MISSING_TRACKING_FOR_SHIPPED_ITEM":
            tracking_keys = {key for key in evidence if "tracking" in key.lower() or "status" in key.lower()}
            assert tracking_keys, "missing tracking rows must include shipment evidence"
            assert "carrier_tracking" in normalized_sources
