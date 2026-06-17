#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path


APP_ROOT = Path(os.environ.get("APP_ROOT", "/root/environment"))
DATA_DIR = APP_ROOT / "data" / "environment_blueprints"
LIVE_DIR = APP_ROOT / "workspace" / "live"


def main() -> None:
    for blueprint in DATA_DIR.glob("*.json"):
        payload = json.loads(blueprint.read_text(encoding="utf-8"))
        target_dir = LIVE_DIR / payload["environment"]
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "terraform.tfvars.json"
        tfvars_payload = {
            key: value
            for key, value in payload.items()
            if key not in {"environment", "region"}
        }
        target_file.write_text(json.dumps(tfvars_payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
