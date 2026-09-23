#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path


ORDERS_QUERY = """
query Orders($first: Int!, $after: String, $start: String, $end: String) {
  orders(first: $first, after: $after, start: $start, end: $end) {
    edges { cursor node { id name processedAt financialStatus cancelledAt lineItems } }
    pageInfo { hasNextPage endCursor }
  }
}
"""

VARIANTS_QUERY = """
query Variants($first: Int!, $after: String, $sku: String, $activeOnly: Boolean) {
  productVariants(first: $first, after: $after, sku: $sku, activeOnly: $activeOnly) {
    edges { cursor node { id sku active inventoryItemId fulfillmentService } }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def load_manifest(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def post_graphql(url: str, query: str, variables: dict) -> dict:
    data = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "X-Client": "skill-admin-probe"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def paginate(url: str, query: str, root: str, variables: dict) -> list[dict]:
    items = []
    after = None
    while True:
        page_vars = dict(variables)
        page_vars["after"] = after
        payload = post_graphql(url, query, page_vars)
        connection = payload["data"][root]
        items.extend(edge["node"] for edge in connection["edges"])
        if not connection["pageInfo"]["hasNextPage"]:
            return items
        after = connection["pageInfo"]["endCursor"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["orders", "variants"])
    parser.add_argument("--manifest", default="/root/data/merchant_manifest.json")
    parser.add_argument("--sku")
    parser.add_argument("--first", type=int, default=3)
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    graphql_url = manifest["service_urls"]["commerce_admin_graphql"]
    if args.kind == "orders":
        window = manifest["reconciliation_window"]
        items = paginate(
            graphql_url,
            ORDERS_QUERY,
            "orders",
            {"first": args.first, "start": window["start"], "end": window["end"]},
        )
    else:
        items = paginate(
            graphql_url,
            VARIANTS_QUERY,
            "productVariants",
            {"first": args.first, "sku": args.sku, "activeOnly": True},
        )
    print(json.dumps(items, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
