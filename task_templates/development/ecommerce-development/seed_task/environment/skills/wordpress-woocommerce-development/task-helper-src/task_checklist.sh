#!/bin/bash
set -euo pipefail

python3 /root/.codex/skills/wordpress-woocommerce-development/scripts/probe_expected_catalog.py

python3 - <<'PY'
from __future__ import annotations

import json
from pathlib import Path


DATA_ROOT = Path("/app/data")


def parse_policy() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (DATA_ROOT / "checkout_policy.md").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("- ") or ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        out[key.strip()] = value.strip()
    return out


shipping = json.loads((DATA_ROOT / "shipping_rules.json").read_text(encoding="utf-8"))
plan = json.loads((DATA_ROOT / "collection_plan.json").read_text(encoding="utf-8"))
policy = parse_policy()

contract = {
    "shippingClasses": [item["slug"] for item in shipping["shipping_classes"]],
    "shippingZones": [
        {
            "name": zone["name"],
            "locations": zone["locations"],
            "method": {
                "id": zone["method"]["id"],
                "title": zone["method"]["title"],
                "base_cost": zone["method"]["base_cost"],
                "class_costs": zone["method"]["class_costs"],
            },
        }
        for zone in shipping["zones"]
    ],
    "checkoutPolicy": policy,
    "gatewayScenarios": {
        "us_standard_120": ["bacs", "cod"],
        "us_oversized_120": ["bacs"],
        "us_standard_200": ["bacs"],
        "ca_standard_120": ["bacs"],
    },
    "feedContract": {
        "departmentField": "departmentSlug",
        "collectionField": "collectionKey",
        "primarySizeKey": plan["size_attribute"]["options"][0]["key"],
        "slugUsesTaskTitle": True,
    },
}

print(json.dumps(contract, indent=2, ensure_ascii=False))
PY
