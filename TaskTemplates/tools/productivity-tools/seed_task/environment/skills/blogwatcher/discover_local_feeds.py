#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path


LINK_PATTERN = re.compile(
    r'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']application/(?P<fmt>rss|atom)\+xml["\'][^>]+href=["\'](?P<href>[^"\']+)["\']',
    re.I,
)


def main() -> int:
    bundle_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app/release-watch")
    mirror_root = bundle_root / "data"
    rows: list[dict[str, str]] = []
    with (mirror_root / "watch_targets.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    payload = []
    for row in rows:
        if row["feed_override_snapshot"]:
            payload.append(
                {
                    "source_id": row["source_id"],
                    "mode": "override",
                    "feed_snapshot": row["feed_override_snapshot"],
                    "feed_url": row["feed_override_url"],
                    "format": "atom" if row["feed_override_snapshot"].endswith(".atom") else "rss",
                }
            )
            continue

        homepage_path = mirror_root / row["homepage_snapshot"]
        html = homepage_path.read_text(encoding="utf-8")
        match = LINK_PATTERN.search(html)
        payload.append(
            {
                "source_id": row["source_id"],
                "mode": "discovered",
                "feed_snapshot": match.group("href").lstrip("/") if match else "",
                "feed_url": match.group("href") if match else "",
                "format": match.group("fmt") if match else "",
            }
        )

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
