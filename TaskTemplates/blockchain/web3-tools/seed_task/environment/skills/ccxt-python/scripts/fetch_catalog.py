from __future__ import annotations

import json
import urllib.request
from pathlib import Path


TASK_MANIFEST = Path("/app/data/task_manifest.json")


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "skill-fetch-catalog"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    task_manifest = json.loads(TASK_MANIFEST.read_text(encoding="utf-8"))
    live_manifest = fetch_json(task_manifest["manifest_endpoint"])
    discovered = []
    for exchange, url in live_manifest["service_urls"]["catalog"].items():
        cursor = None
        while True:
            page_url = url if cursor is None else f"{url}?cursor={cursor}"
            page = fetch_json(page_url)
            for item in page["items"]:
                item["exchange"] = exchange
                discovered.append(item)
            if not page["has_next_page"]:
                break
            cursor = page["next_cursor"]
    print(json.dumps(discovered, indent=2))


if __name__ == "__main__":
    main()
