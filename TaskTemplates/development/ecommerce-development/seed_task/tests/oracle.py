from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/app/data"))
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
WP_PATH = Path(os.environ.get("WP_PATH", "/var/www/html"))
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1")


REQUIRED_FEED_FIELDS = {
    "productId",
    "title",
    "slug",
    "artistName",
    "department",
    "collection",
    "sku",
    "price",
    "image",
    "availability",
}


@dataclass
class LaunchRow:
    object_id: int
    merchandising_title: str
    artist_name: str
    department_slug: str
    collection_key: str
    featured_rank: int
    small_stock: int
    large_stock: int
    collection_sort_order: int
    primary_image: str
    base_price: float


def load_seed_rows(data_root: Path = DATA_ROOT) -> list[dict]:
    with (data_root / "met_print_seed.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_object_details(data_root: Path = DATA_ROOT) -> dict[int, dict]:
    details: dict[int, dict] = {}
    with (data_root / "met_object_details.ndjson").open(encoding="utf-8") as fh:
        for line in fh:
            obj = json.loads(line)
            details[int(obj["objectID"])] = obj
    return details


def load_collection_plan(data_root: Path = DATA_ROOT) -> dict:
    return json.loads((data_root / "collection_plan.json").read_text(encoding="utf-8"))


def load_shipping_rules(data_root: Path = DATA_ROOT) -> dict:
    return json.loads((data_root / "shipping_rules.json").read_text(encoding="utf-8"))


def parse_checkout_policy(data_root: Path = DATA_ROOT) -> dict[str, str]:
    out: dict[str, str] = {}
    lines = (data_root / "checkout_policy.md").read_text(encoding="utf-8").splitlines()
    for line in lines:
        line = line.strip()
        if not line.startswith("- "):
            continue
        payload = line[2:]
        if ":" not in payload:
            continue
        key, value = payload.split(":", 1)
        out[key.strip()] = value.strip()
    return out


def expected_launch_rows(data_root: Path = DATA_ROOT) -> list[LaunchRow]:
    rows = load_seed_rows(data_root)
    details = load_object_details(data_root)
    plan = load_collection_plan(data_root)
    collection_order = {item["key"]: int(item["sort_order"]) for item in plan["collections"]}
    launch_state = plan["launch_feed"]["require_launch_state"]

    out: list[LaunchRow] = []
    for row in rows:
        object_id = int(row["objectID"])
        detail = details.get(object_id, {})
        image = (detail.get("primaryImageSmall") or "").strip()
        small_stock = int(row["smallStock"])
        large_stock = int(row["largeStock"])
        if row["launchState"] != launch_state:
            continue
        if row["publicDomainClearance"].strip().lower() != "true":
            continue
        if not image:
            continue
        if small_stock <= 0 and large_stock <= 0:
            continue
        out.append(
            LaunchRow(
                object_id=object_id,
                merchandising_title=row["merchandisingTitle"],
                artist_name=detail.get("artistDisplayName", ""),
                department_slug=row["departmentSlug"],
                collection_key=row["collectionKey"],
                featured_rank=int(row["featuredRank"]),
                small_stock=small_stock,
                large_stock=large_stock,
                collection_sort_order=collection_order[row["collectionKey"]],
                primary_image=image,
                base_price=float(row["basePrice"]),
            )
        )

    out.sort(key=lambda item: (item.collection_sort_order, item.featured_rank, item.object_id))
    return out


def expected_launch_items(data_root: Path = DATA_ROOT) -> list[dict[str, object]]:
    plan = load_collection_plan(data_root)
    size_options = plan["size_attribute"]["options"]
    if not size_options:
        return []
    primary_size = size_options[0]

    store_products = wp_eval_json(
        r"""
        $products = wc_get_products([
            'status' => ['publish'],
            'type' => ['variable'],
            'limit' => -1,
            'orderby' => 'date',
            'order' => 'ASC',
        ]);
        $out = [];
        foreach ($products as $product) {
            if (!$product instanceof WC_Product_Variable) {
                continue;
            }
            $out[] = [
                'productId' => $product->get_id(),
                'title' => (string) $product->get_name(),
                'slug' => (string) $product->get_slug(),
                'objectId' => (int) (
                    $product->get_meta('harbor_object_id', true)
                    ?: $product->get_meta('_harbor_object_id', true)
                ),
            ];
        }
        echo json_encode($out);
        """
    )
    if not isinstance(store_products, list):
        raise RuntimeError(f"unexpected store product payload: {store_products!r}")

    store_by_object_id: dict[int, dict] = {}
    store_by_slug: dict[str, dict] = {}
    for product in store_products:
        if not isinstance(product, dict):
            continue
        slug = str(product.get("slug") or "")
        if slug:
            store_by_slug[slug] = product
        object_id = int(product.get("objectId") or 0)
        if object_id <= 0:
            continue
        store_by_object_id[object_id] = product

    ordered_items: list[tuple[int, int, int, dict[str, object]]] = []
    for row in expected_launch_rows(data_root):
        expected_slug = f"{simple_slug(row.merchandising_title)}-{row.object_id}"
        product = store_by_slug.get(expected_slug)
        if product is None:
            product = store_by_object_id.get(row.object_id)
        if product is None:
            raise RuntimeError(f"missing published variable product for slug={expected_slug}")

        product_id = int(product["productId"])
        availability = "in_stock" if stock_for_size(row, str(primary_size["key"])) > 0 else "out_of_stock"
        ordered_items.append(
            (
                row.collection_sort_order,
                row.featured_rank,
                product_id,
                {
                    "productId": product_id,
                    "title": row.merchandising_title,
                    "slug": expected_slug,
                    "artistName": row.artist_name,
                    "department": row.department_slug,
                    "collection": row.collection_key,
                    "sku": f"MET-{row.object_id}-{primary_size['sku_suffix']}",
                    "price": f"{row.base_price + float(primary_size['price_delta']):.2f}",
                    "image": row.primary_image,
                    "availability": availability,
                },
            )
        )

    ordered_items.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in ordered_items]


def expected_summary(data_root: Path = DATA_ROOT) -> dict[str, int]:
    rows = load_seed_rows(data_root)
    shipping = load_shipping_rules(data_root)
    policy = parse_checkout_policy(data_root)
    launch_rows = expected_launch_rows(data_root)
    enabled = [x.strip() for x in policy.get("enable_gateways", "").split(",") if x.strip()]
    return {
        "products": len(rows),
        "variableProducts": len(rows),
        "variations": len(rows) * len(load_collection_plan(data_root)["size_attribute"]["options"]),
        "departments": len({row["departmentSlug"] for row in rows}),
        "collections": len({row["collectionKey"] for row in rows}),
        "shippingZones": len(shipping["zones"]),
        "paymentGateways": len(enabled),
        "launchFeedCount": len(launch_rows),
    }


def run_cmd(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    return proc


def wp_eval_json(php_code: str) -> dict | list:
    proc = run_cmd(
        ["wp", "eval", php_code, "--allow-root", f"--path={WP_PATH}"],
    )
    payload = proc.stdout.strip()
    if not payload:
        raise RuntimeError("wp eval returned empty output")
    return json.loads(payload)


def request_json(path: str) -> tuple[int, dict | list]:
    req = urllib.request.Request(BASE_URL + path, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        return exc.code, parsed


def extract_feed_items(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return items
    return []


def simple_slug(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = lowered.strip("-")
    return lowered


def stock_for_size(row: LaunchRow, size_key: str) -> int:
    if size_key == "small":
        return row.small_stock
    if size_key == "large":
        return row.large_stock
    return 0
