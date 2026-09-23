#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    manifest_path = Path("/root/.codex/skills/intake_probe_manifest.json")
    if not manifest_path.exists():
        raise SystemExit("Bound exploratory-data-analysis skill is not available in this runtime.")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
