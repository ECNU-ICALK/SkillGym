#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


ISSUES = [
    "SKU_VARIANT_DRIFT",
    "FULFILLMENT_SERVICE_MISMATCH",
    "INSUFFICIENT_AVAILABLE_STOCK",
    "STALE_OR_CONFLICTING_TRACKING",
    "MISSING_TRACKING_FOR_SHIPPED_ITEM",
]

ORDERS_QUERY = "query Orders($first: Int!, $after: String, $start: String, $end: String) { orders(first: $first, after: $after, start: $start, end: $end) { edges { cursor node { id name processedAt financialStatus cancelledAt lineItems } } pageInfo { hasNextPage endCursor } } }"
VARIANTS_QUERY = "query Variants($first: Int!, $after: String, $sku: String, $activeOnly: Boolean) { productVariants(first: $first, after: $after, sku: $sku, activeOnly: $activeOnly) { edges { cursor node { id sku active inventoryItemId fulfillmentService } } pageInfo { hasNextPage endCursor } } }"


def post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Client": "skill-reconcile-candidates"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"X-Client": "skill-reconcile-candidates"})
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


def read_catalog(path: str) -> dict[str, dict]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return {row["sku"]: row for row in csv.DictReader(fh)}


def add_row(rows: list[dict], order: dict, item: dict, code: str, severity: str, action: str, evidence: dict) -> None:
    rows.append({
        "order_id": order["id"],
        "order_name": order["name"],
        "line_item_id": item["id"],
        "sku": item["sku"],
        "variant_id": item["variantId"],
        "issue_code": code,
        "severity": severity,
        "expected_action": action,
        "evidence": evidence,
    })


def reconcile(manifest_path: str, catalog_path: str) -> dict:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    catalog = read_catalog(catalog_path)
    graphql_url = manifest["service_urls"]["commerce_admin_graphql"]
    warehouse_url = manifest["service_urls"]["warehouse"]
    carrier_url = manifest["service_urls"]["carrier_tracking"]
    window = manifest["reconciliation_window"]

    orders = paginate_graphql(
        graphql_url,
        ORDERS_QUERY,
        "orders",
        {"first": 3, "start": window["start"], "end": window["end"]},
    )

    variant_cache: dict[str, list[dict]] = {}
    rows: list[dict] = []
    orders_checked = 0
    line_items_checked = 0

    for order in orders:
        shippable = [li for li in order["lineItems"] if li.get("requiresShipping")]
        if order["financialStatus"] != "PAID" or order.get("cancelledAt") or not shippable:
            continue
        orders_checked += 1
        for item in shippable:
            line_items_checked += 1
            sku = item["sku"]
            variants = variant_cache.setdefault(
                sku,
                paginate_graphql(graphql_url, VARIANTS_QUERY, "productVariants", {"first": 20, "sku": sku, "activeOnly": True}),
            )
            resolved = variants[0] if len(variants) == 1 else None
            if len(variants) != 1 or (resolved and resolved["id"] != item["variantId"]):
                add_row(rows, order, item, "SKU_VARIANT_DRIFT", "critical", "correct_sku_mapping", {
                    "admin_order_id": order["id"],
                    "line_item_id": item["id"],
                    "sku": sku,
                    "line_item_variant_id": item["variantId"],
                    "active_variant_ids": [v["id"] for v in variants],
                    "checked_sources": ["commerce_admin"],
                })
                continue

            expected_service = catalog.get(sku, {}).get("expected_fulfillment_service")
            if expected_service and resolved["fulfillmentService"] != expected_service:
                add_row(rows, order, item, "FULFILLMENT_SERVICE_MISMATCH", "high", "reroute_fulfillment", {
                    "admin_order_id": order["id"],
                    "line_item_id": item["id"],
                    "sku": sku,
                    "variant_id": resolved["id"],
                    "expected_fulfillment_service": expected_service,
                    "actual_fulfillment_service": resolved["fulfillmentService"],
                    "checked_sources": ["commerce_admin", "catalog_export"],
                })

            unfulfilled = int(item.get("unfulfilledQuantity") or 0)
            inv = resolved["inventoryItemId"]
            if unfulfilled > 0:
                stock = get_json(f"{warehouse_url}/stock?{urllib.parse.urlencode({'inventory_item_id': inv})}") or {}
                reservations = get_json(f"{warehouse_url}/reservations?{urllib.parse.urlencode({'inventory_item_id': inv})}") or {"reservations": []}
                open_res = [r for r in reservations.get("reservations", []) if r.get("status") == "open"]
                reserved_qty = sum(int(r["quantity"]) for r in open_res)
                available = int(stock.get("on_hand", 0)) - reserved_qty
                if available < unfulfilled:
                    add_row(rows, order, item, "INSUFFICIENT_AVAILABLE_STOCK", "critical", "hold_order", {
                        "admin_order_id": order["id"],
                        "line_item_id": item["id"],
                        "sku": sku,
                        "inventory_item_id": inv,
                        "warehouse_location_id": stock.get("warehouse_location_id"),
                        "on_hand": stock.get("on_hand"),
                        "reserved_quantity": reserved_qty,
                        "available_quantity": available,
                        "needed_quantity": unfulfilled,
                        "reservation_ids": [r["reservation_id"] for r in open_res],
                        "checked_sources": ["commerce_admin", "warehouse_reservations"],
                    })

            status = item.get("fulfillmentStatus")
            tracking = item.get("trackingNumber")
            if status in {"FULFILLED", "SHIPPED", "IN_TRANSIT"}:
                carrier = get_json(f"{carrier_url}/track/{urllib.parse.quote(str(tracking or ''))}") if tracking else None
                if not carrier:
                    add_row(rows, order, item, "MISSING_TRACKING_FOR_SHIPPED_ITEM", "medium", "refresh_tracking", {
                        "admin_order_id": order["id"],
                        "line_item_id": item["id"],
                        "sku": sku,
                        "variant_id": resolved["id"],
                        "tracking_number": tracking,
                        "admin_fulfillment_status": status,
                        "checked_sources": ["commerce_admin", "carrier_tracking"],
                    })
                elif status in {"UNFULFILLED", "PARTIAL", "IN_TRANSIT"} and carrier.get("latest_status") in {"delivered", "cancelled", "exception"}:
                    add_row(rows, order, item, "STALE_OR_CONFLICTING_TRACKING", "high", "manual_review", {
                        "admin_order_id": order["id"],
                        "line_item_id": item["id"],
                        "sku": sku,
                        "variant_id": resolved["id"],
                        "tracking_number": tracking,
                        "carrier_status": carrier.get("latest_status"),
                        "admin_fulfillment_status": status,
                        "checked_sources": ["commerce_admin", "carrier_tracking"],
                    })

    issue_counts = Counter(row["issue_code"] for row in rows)
    summary = {
        "window": {"start": window["start"], "end": window["end"]},
        "totals": {
            "orders_checked": orders_checked,
            "line_items_checked": line_items_checked,
            "orders_with_exceptions": len({row["order_id"] for row in rows}),
            "exception_rows": len(rows),
        },
        "issue_counts": {issue: issue_counts.get(issue, 0) for issue in ISSUES},
        "source_checks": {
            "commerce_admin": True,
            "warehouse_reservations": True,
            "carrier_tracking": True,
        },
        "notes": [],
    }
    return {"rows": rows, "summary": summary}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="/root/data/merchant_manifest.json")
    parser.add_argument("--catalog", default="/root/data/catalog_export.csv")
    args = parser.parse_args()
    print(json.dumps(reconcile(args.manifest, args.catalog), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
