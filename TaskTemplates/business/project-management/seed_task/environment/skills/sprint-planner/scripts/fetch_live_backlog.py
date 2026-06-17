from __future__ import annotations

import json
import urllib.request
from pathlib import Path


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "skill-fetch-live-backlog"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    manifest = json.loads(Path("/root/data/planning_manifest.json").read_text(encoding="utf-8"))
    base_url = manifest["service_urls"]["planning_api"].rstrip("/")
    page_size = int(manifest.get("page_size_hint", 5))

    summaries = []
    details = []
    page = 1
    while True:
        payload = get_json(f"{base_url}/items?page={page}&page_size={page_size}")
        summaries.extend(payload["items"])
        for item in payload["items"]:
            details.append(get_json(f"{base_url}/items/{item['item_id']}"))
        if payload["next_page"] is None:
            break
        page = int(payload["next_page"])

    print(json.dumps({"summaries": summaries, "details": details}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
