from __future__ import annotations

import json
import urllib.request
from pathlib import Path


DATA_ROOT = Path("/root/data")


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "skill-fetch-cohort"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    manifest = json.loads((DATA_ROOT / "ops_manifest.json").read_text(encoding="utf-8"))
    live_manifest = get_json(manifest["manifest_endpoint"])
    cohort_url = live_manifest["service_urls"]["cohort"]
    cursor = None
    items = []
    while True:
      url = cohort_url if cursor is None else f"{cohort_url}?cursor={cursor}"
      payload = get_json(url)
      items.extend(payload["items"])
      if not payload["has_next_page"]:
          break
      cursor = payload["next_cursor"]
    print(json.dumps(items, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
