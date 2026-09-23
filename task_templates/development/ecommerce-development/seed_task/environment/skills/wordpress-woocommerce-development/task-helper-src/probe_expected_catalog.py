#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path


DATA_ROOT = Path("/app/data")


def load_seed_rows() -> list[dict[str, str]]:
    with (DATA_ROOT / "met_print_seed.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_object_details() -> dict[int, dict]:
    details: dict[int, dict] = {}
    with (DATA_ROOT / "met_object_details.ndjson").open(encoding="utf-8") as fh:
        for line in fh:
            item = json.loads(line)
            details[int(item["objectID"])] = item
    return details


def load_collection_plan() -> dict:
    return json.loads((DATA_ROOT / "collection_plan.json").read_text(encoding="utf-8"))


def main() -> None:
    rows = load_seed_rows()
    details = load_object_details()
    plan = load_collection_plan()
    launch_rules = plan["launch_feed"]

    launch_rows = []
    expected_feed_items = []
    size_options = plan["size_attribute"]["options"]
    primary_size = size_options[0]
    primary_key = primary_size["key"]
    for row in rows:
        detail = details[int(row["objectID"])]
        if row["launchState"] != launch_rules["require_launch_state"]:
            continue
        if row["publicDomainClearance"].strip().lower() != "true":
            continue
        if launch_rules["require_primary_image"] and not (detail.get("primaryImageSmall") or "").strip():
            continue
        if launch_rules["require_in_stock_variation"] and int(row["smallStock"]) <= 0 and int(row["largeStock"]) <= 0:
            continue
        launch_rows.append(
            {
                "objectID": int(row["objectID"]),
                "title": row["merchandisingTitle"],
                "departmentSlug": row["departmentSlug"],
                "collectionKey": row["collectionKey"],
            }
        )
        expected_feed_items.append(
            {
                "seedObjectId": int(row["objectID"]),
                "title": row["merchandisingTitle"],
                "slug": row["merchandisingTitle"].lower().replace(" ", "-") + f"-{int(row['objectID'])}",
                "artistName": detail.get("artistDisplayName", ""),
                "department": row["departmentSlug"],
                "collection": row["collectionKey"],
                "sku": f"MET-{int(row['objectID'])}-{primary_size['sku_suffix']}",
                "price": f"{float(row['basePrice']) + float(primary_size['price_delta']):.2f}",
                "image": detail.get("primaryImageSmall", ""),
                "availability": "in_stock" if int(row[f"{primary_key}Stock"]) > 0 else "out_of_stock",
            }
        )

    summary = {
        "products": len(rows),
        "variableProducts": len(rows),
        "variations": len(rows) * len(plan["size_attribute"]["options"]),
        "departments": len({row["departmentSlug"] for row in rows}),
        "collections": len({row["collectionKey"] for row in rows}),
        "launchFeedCount": len(launch_rows),
    }

    print(
        json.dumps(
            {"summary": summary, "launchRows": launch_rows, "expectedFeedItems": expected_feed_items},
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
