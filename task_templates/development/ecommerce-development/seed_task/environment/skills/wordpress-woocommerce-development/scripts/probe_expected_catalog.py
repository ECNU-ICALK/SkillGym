#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path


DATA_ROOT = Path("/app/data")


def load_details() -> dict[int, dict]:
    details = {}
    with (DATA_ROOT / "met_object_details.ndjson").open(encoding="utf-8") as fh:
        for line in fh:
            obj = json.loads(line)
            details[int(obj["objectID"])] = obj
    return details


def main() -> None:
    plan = json.loads((DATA_ROOT / "collection_plan.json").read_text(encoding="utf-8"))
    details = load_details()
    rows = list(csv.DictReader((DATA_ROOT / "met_print_seed.csv").open(encoding="utf-8")))

    collection_order = {item["key"]: item["sort_order"] for item in plan["collections"]}
    launch_rows = []
    for row in rows:
        detail = details[int(row["objectID"])]
        image = detail.get("primaryImageSmall") or ""
        if (
            row["launchState"] == plan["launch_feed"]["require_launch_state"]
            and row["publicDomainClearance"] == "true"
            and image
            and (int(row["smallStock"]) > 0 or int(row["largeStock"]) > 0)
        ):
            launch_rows.append(
                {
                    "objectID": int(row["objectID"]),
                    "collectionKey": row["collectionKey"],
                    "collectionOrder": collection_order[row["collectionKey"]],
                    "featuredRank": int(row["featuredRank"]),
                    "title": detail["title"],
                    "image": image,
                }
            )

    launch_rows.sort(key=lambda item: (item["collectionOrder"], item["featuredRank"], item["objectID"]))

    payload = {
        "product_count": len(rows),
        "variation_count": len(rows) * len(plan["size_attribute"]["options"]),
        "launch_feed_object_ids": [item["objectID"] for item in launch_rows],
        "launch_feed_count": len(launch_rows),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
