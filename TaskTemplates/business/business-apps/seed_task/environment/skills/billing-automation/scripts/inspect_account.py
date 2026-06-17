from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path


DATA_ROOT = Path("/root/data")


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "skill-inspect-account"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: inspect_account.py ACC-101")
    account_id = sys.argv[1]
    manifest = json.loads((DATA_ROOT / "ops_manifest.json").read_text(encoding="utf-8"))
    live_manifest = get_json(manifest["manifest_endpoint"])
    base = live_manifest["service_urls"]["accounts_base"].rstrip("/")
    payload = {
        "account": get_json(f"{base}/{account_id}"),
        "renewal_preview": get_json(f"{base}/{account_id}/renewal-preview"),
        "dunning_events": get_json(f"{base}/{account_id}/dunning-events")
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
