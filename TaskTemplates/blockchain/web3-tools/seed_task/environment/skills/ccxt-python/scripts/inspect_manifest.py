from __future__ import annotations

import json
import urllib.request
from pathlib import Path


TASK_MANIFEST = Path("/app/data/task_manifest.json")
CONTRACT = Path("/app/data/contracts/surveillance_contract.json")


def main() -> None:
    task_manifest = json.loads(TASK_MANIFEST.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    req = urllib.request.Request(task_manifest["manifest_endpoint"], headers={"X-Client": "skill-inspect-manifest"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        live_manifest = json.loads(resp.read().decode("utf-8"))
    print(json.dumps({"task_manifest": task_manifest, "contract": contract, "live_manifest": live_manifest}, indent=2))


if __name__ == "__main__":
    main()

