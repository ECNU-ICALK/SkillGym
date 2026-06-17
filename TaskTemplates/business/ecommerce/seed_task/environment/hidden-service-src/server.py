#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PORT = int(os.environ.get("ECOMMERCE_RECON_PORT", "8123"))
ACCESS_LOG = Path("/var/log/ecommerce-recon/access.log")

ORDERS = [
    {
        "id": "gid://shopify/Order/7001",
        "name": "#H1001",
        "processedAt": "2026-04-20T09:15:00-04:00",
        "financialStatus": "PAID",
        "cancelledAt": None,
        "lineItems": [
            {
                "id": "gid://shopify/LineItem/9001",
                "sku": "THERMO-BLK-20",
                "variantId": "gid://shopify/ProductVariant/1001",
                "quantity": 3,
                "unfulfilledQuantity": 3,
                "requiresShipping": True,
                "fulfillmentStatus": "UNFULFILLED",
                "trackingNumber": None,
            },
            {
                "id": "gid://shopify/LineItem/9002",
                "sku": "MUG-STONE-12",
                "variantId": "gid://shopify/ProductVariant/1003",
                "quantity": 1,
                "unfulfilledQuantity": 0,
                "requiresShipping": True,
                "fulfillmentStatus": "IN_TRANSIT",
                "trackingNumber": "HHG1001MUG",
            },
        ],
    },
    {
        "id": "gid://shopify/Order/7002",
        "name": "#H1002",
        "processedAt": "2026-04-20T13:42:00-04:00",
        "financialStatus": "PAID",
        "cancelledAt": None,
        "lineItems": [
            {
                "id": "gid://shopify/LineItem/9003",
                "sku": "TEE-LINEN-M",
                "variantId": "gid://shopify/ProductVariant/1004",
                "quantity": 2,
                "unfulfilledQuantity": 2,
                "requiresShipping": True,
                "fulfillmentStatus": "UNFULFILLED",
                "trackingNumber": None,
            }
        ],
    },
    {
        "id": "gid://shopify/Order/7003",
        "name": "#H1003",
        "processedAt": "2026-04-21T08:10:00-04:00",
        "financialStatus": "PAID",
        "cancelledAt": None,
        "lineItems": [
            {
                "id": "gid://shopify/LineItem/9004",
                "sku": "POSTER-A2",
                "variantId": "gid://shopify/ProductVariant/1008",
                "quantity": 1,
                "unfulfilledQuantity": 1,
                "requiresShipping": True,
                "fulfillmentStatus": "UNFULFILLED",
                "trackingNumber": None,
            }
        ],
    },
    {
        "id": "gid://shopify/Order/7004",
        "name": "#H1004",
        "processedAt": "2026-04-21T16:22:00-04:00",
        "financialStatus": "PAID",
        "cancelledAt": None,
        "lineItems": [
            {
                "id": "gid://shopify/LineItem/9005",
                "sku": "BOTTLE-BLU-32",
                "variantId": "gid://shopify/ProductVariant/1002",
                "quantity": 1,
                "unfulfilledQuantity": 0,
                "requiresShipping": True,
                "fulfillmentStatus": "FULFILLED",
                "trackingNumber": "HHG-MISSING-7004",
            }
        ],
    },
    {
        "id": "gid://shopify/Order/7005",
        "name": "#H1005",
        "processedAt": "2026-04-21T18:00:00-04:00",
        "financialStatus": "PAID",
        "cancelledAt": "2026-04-21T19:30:00-04:00",
        "lineItems": [
            {
                "id": "gid://shopify/LineItem/9006",
                "sku": "CANDLE-CITRUS",
                "variantId": "gid://shopify/ProductVariant/1005",
                "quantity": 1,
                "unfulfilledQuantity": 1,
                "requiresShipping": True,
                "fulfillmentStatus": "UNFULFILLED",
                "trackingNumber": None,
            }
        ],
    },
    {
        "id": "gid://shopify/Order/7006",
        "name": "#H1006",
        "processedAt": "2026-04-22T09:05:00-04:00",
        "financialStatus": "PENDING",
        "cancelledAt": None,
        "lineItems": [
            {
                "id": "gid://shopify/LineItem/9007",
                "sku": "TOTE-CLAY",
                "variantId": "gid://shopify/ProductVariant/1006",
                "quantity": 1,
                "unfulfilledQuantity": 1,
                "requiresShipping": True,
                "fulfillmentStatus": "UNFULFILLED",
                "trackingNumber": None,
            }
        ],
    },
    {
        "id": "gid://shopify/Order/7007",
        "name": "#H1007",
        "processedAt": "2026-04-22T10:40:00-04:00",
        "financialStatus": "PAID",
        "cancelledAt": None,
        "lineItems": [
            {
                "id": "gid://shopify/LineItem/9008",
                "sku": "DIGITAL-GUIDE",
                "variantId": "gid://shopify/ProductVariant/1010",
                "quantity": 1,
                "unfulfilledQuantity": 0,
                "requiresShipping": False,
                "fulfillmentStatus": "FULFILLED",
                "trackingNumber": None,
            }
        ],
    },
    {
        "id": "gid://shopify/Order/7008",
        "name": "#H1008",
        "processedAt": "2026-04-22T14:12:00-04:00",
        "financialStatus": "PAID",
        "cancelledAt": None,
        "lineItems": [
            {
                "id": "gid://shopify/LineItem/9009",
                "sku": "HAT-CANVAS",
                "variantId": "gid://shopify/ProductVariant/9999",
                "quantity": 1,
                "unfulfilledQuantity": 1,
                "requiresShipping": True,
                "fulfillmentStatus": "UNFULFILLED",
                "trackingNumber": None,
            }
        ],
    },
    {
        "id": "gid://shopify/Order/7009",
        "name": "#H1009",
        "processedAt": "2026-04-22T19:45:00-04:00",
        "financialStatus": "PAID",
        "cancelledAt": None,
        "lineItems": [
            {
                "id": "gid://shopify/LineItem/9010",
                "sku": "TOTE-CLAY",
                "variantId": "gid://shopify/ProductVariant/1006",
                "quantity": 4,
                "unfulfilledQuantity": 4,
                "requiresShipping": True,
                "fulfillmentStatus": "UNFULFILLED",
                "trackingNumber": None,
            }
        ],
    },
]

VARIANTS = [
    {"id": "gid://shopify/ProductVariant/1001", "sku": "THERMO-BLK-20", "active": True, "inventoryItemId": "gid://shopify/InventoryItem/5001", "fulfillmentService": "east-3pl"},
    {"id": "gid://shopify/ProductVariant/1002", "sku": "BOTTLE-BLU-32", "active": True, "inventoryItemId": "gid://shopify/InventoryItem/5002", "fulfillmentService": "east-3pl"},
    {"id": "gid://shopify/ProductVariant/1003", "sku": "MUG-STONE-12", "active": True, "inventoryItemId": "gid://shopify/InventoryItem/5003", "fulfillmentService": "inhouse-west"},
    {"id": "gid://shopify/ProductVariant/1004", "sku": "TEE-LINEN-M", "active": True, "inventoryItemId": "gid://shopify/InventoryItem/5004", "fulfillmentService": "inhouse-west"},
    {"id": "gid://shopify/ProductVariant/1005", "sku": "CANDLE-CITRUS", "active": True, "inventoryItemId": "gid://shopify/InventoryItem/5005", "fulfillmentService": "inhouse-west"},
    {"id": "gid://shopify/ProductVariant/1006", "sku": "TOTE-CLAY", "active": True, "inventoryItemId": "gid://shopify/InventoryItem/5006", "fulfillmentService": "east-3pl"},
    {"id": "gid://shopify/ProductVariant/1007", "sku": "HAT-CANVAS", "active": True, "inventoryItemId": "gid://shopify/InventoryItem/5007", "fulfillmentService": "east-3pl"},
    {"id": "gid://shopify/ProductVariant/1008", "sku": "POSTER-A2", "active": True, "inventoryItemId": "gid://shopify/InventoryItem/5008", "fulfillmentService": "print-partner"},
    {"id": "gid://shopify/ProductVariant/2008", "sku": "POSTER-A2", "active": True, "inventoryItemId": "gid://shopify/InventoryItem/7008", "fulfillmentService": "print-partner"},
    {"id": "gid://shopify/ProductVariant/1010", "sku": "DIGITAL-GUIDE", "active": True, "inventoryItemId": "gid://shopify/InventoryItem/5010", "fulfillmentService": "digital"},
]

STOCK = {
    "gid://shopify/InventoryItem/5001": {"warehouse_location_id": "wh-east-01", "on_hand": 5},
    "gid://shopify/InventoryItem/5002": {"warehouse_location_id": "wh-east-01", "on_hand": 8},
    "gid://shopify/InventoryItem/5003": {"warehouse_location_id": "wh-west-02", "on_hand": 12},
    "gid://shopify/InventoryItem/5004": {"warehouse_location_id": "wh-west-02", "on_hand": 9},
    "gid://shopify/InventoryItem/5005": {"warehouse_location_id": "wh-west-02", "on_hand": 3},
    "gid://shopify/InventoryItem/5006": {"warehouse_location_id": "wh-east-01", "on_hand": 10},
    "gid://shopify/InventoryItem/5007": {"warehouse_location_id": "wh-east-01", "on_hand": 5},
    "gid://shopify/InventoryItem/5008": {"warehouse_location_id": "print-hub-01", "on_hand": 20},
    "gid://shopify/InventoryItem/7008": {"warehouse_location_id": "print-hub-02", "on_hand": 15},
}

RESERVATIONS = {
    "gid://shopify/InventoryItem/5001": [
        {"reservation_id": "res-1001-a", "order_id": "gid://shopify/Order/6990", "quantity": 2, "status": "open"},
        {"reservation_id": "res-1001-b", "order_id": "gid://shopify/Order/6994", "quantity": 2, "status": "open"},
    ],
    "gid://shopify/InventoryItem/5004": [
        {"reservation_id": "res-1004-a", "order_id": "gid://shopify/Order/7002", "quantity": 1, "status": "open"}
    ],
    "gid://shopify/InventoryItem/5006": [
        {"reservation_id": "res-1006-a", "order_id": "gid://shopify/Order/7012", "quantity": 2, "status": "open"}
    ],
}

CARRIER = {
    "HHG1001MUG": {
        "tracking_number": "HHG1001MUG",
        "carrier": "ParcelNorth",
        "latest_status": "delivered",
        "updated_at": "2026-04-22T20:11:00-04:00",
        "events": [
            {"status": "in_transit", "timestamp": "2026-04-21T14:00:00-04:00"},
            {"status": "delivered", "timestamp": "2026-04-22T20:11:00-04:00"},
        ],
    },
    "HHG-OK-7009": {
        "tracking_number": "HHG-OK-7009",
        "carrier": "ParcelNorth",
        "latest_status": "in_transit",
        "updated_at": "2026-04-22T22:00:00-04:00",
        "events": [{"status": "in_transit", "timestamp": "2026-04-22T22:00:00-04:00"}],
    },
}


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def in_window(order: dict, start: str | None, end: str | None) -> bool:
    processed = parse_dt(order["processedAt"])
    if start and processed < parse_dt(start):
        return False
    if end and processed > parse_dt(end):
        return False
    return True


def page_items(items: list[dict], first: int, after: str | None) -> dict:
    start = int(after) + 1 if after else 0
    page = items[start:start + first]
    edges = [{"cursor": str(start + idx), "node": item} for idx, item in enumerate(page)]
    end_cursor = edges[-1]["cursor"] if edges else after
    return {
        "edges": edges,
        "pageInfo": {
            "hasNextPage": start + first < len(items),
            "endCursor": end_cursor,
        },
    }


def append_log(handler: BaseHTTPRequestHandler, body: bytes = b"") -> None:
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = body.decode("utf-8", errors="replace")
    except Exception:
        payload = ""
    record = {
        "ts": time.time(),
        "method": handler.command,
        "path": handler.path,
        "user_agent": handler.headers.get("User-Agent", ""),
        "client": handler.headers.get("X-Client", ""),
        "body": payload[:1000],
    }
    with ACCESS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "HarborEcommerceRecon/1.0"

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        append_log(self)
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/health":
            self._send(200, {"ok": True, "service": "ecommerce-recon", "version": "1.0"})
            return
        if parsed.path == "/warehouse/stock":
            inventory_item_id = query.get("inventory_item_id", [""])[0]
            stock = STOCK.get(inventory_item_id)
            if not stock:
                self._send(404, {"error": "inventory item not found"})
                return
            self._send(200, {"inventory_item_id": inventory_item_id, **stock})
            return
        if parsed.path == "/warehouse/reservations":
            inventory_item_id = query.get("inventory_item_id", [""])[0]
            reservations = RESERVATIONS.get(inventory_item_id, [])
            self._send(200, {"inventory_item_id": inventory_item_id, "reservations": reservations})
            return
        if parsed.path.startswith("/carrier/track/"):
            tracking_number = parsed.path.rsplit("/", 1)[-1]
            tracking = CARRIER.get(tracking_number)
            if not tracking:
                self._send(404, {"error": "tracking number not found", "tracking_number": tracking_number})
                return
            self._send(200, tracking)
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        append_log(self, body)
        parsed = urlparse(self.path)
        if parsed.path != "/admin/graphql":
            self._send(404, {"error": "not found"})
            return

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send(400, {"errors": [{"message": "invalid json"}]})
            return

        query = payload.get("query", "")
        variables = payload.get("variables", {}) or {}

        if "__schema" in query:
            self._send(200, {"data": {"__schema": {"queryType": {"name": "Query"}, "types": [{"name": "Order"}, {"name": "ProductVariant"}]}}})
            return

        if "orders" in query:
            first = min(int(variables.get("first") or 3), 3)
            after = variables.get("after")
            start = variables.get("start")
            end = variables.get("end")
            filtered = [order for order in ORDERS if in_window(order, start, end)]
            self._send(200, {"data": {"orders": page_items(filtered, first, after)}})
            return

        if "productVariants" in query or "variants" in query:
            first = int(variables.get("first") or 50)
            after = variables.get("after")
            sku = variables.get("sku")
            active_only = variables.get("activeOnly", True)
            filtered = VARIANTS
            if sku:
                filtered = [variant for variant in filtered if variant["sku"] == sku]
            if active_only:
                filtered = [variant for variant in filtered if variant["active"]]
            self._send(200, {"data": {"productVariants": page_items(filtered, first, after)}})
            return

        self._send(400, {"errors": [{"message": "unsupported query"}]})


if __name__ == "__main__":
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    ACCESS_LOG.touch(exist_ok=True)
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    httpd.serve_forever()
