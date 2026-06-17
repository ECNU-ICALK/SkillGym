#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path


def load_manifest(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "skill-downstream-probe"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["stock", "reservations", "tracking"])
    parser.add_argument("--manifest", default="/root/data/merchant_manifest.json")
    parser.add_argument("--inventory-item-id")
    parser.add_argument("--tracking-number")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    if args.kind in {"stock", "reservations"}:
        if not args.inventory_item_id:
            raise SystemExit("--inventory-item-id is required")
        base = manifest["service_urls"]["warehouse"]
        encoded = urllib.parse.urlencode({"inventory_item_id": args.inventory_item_id})
        url = f"{base}/{args.kind}?{encoded}"
    else:
        if not args.tracking_number:
            raise SystemExit("--tracking-number is required")
        base = manifest["service_urls"]["carrier_tracking"]
        url = f"{base}/track/{urllib.parse.quote(args.tracking_number)}"
    print(json.dumps(get_json(url), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
