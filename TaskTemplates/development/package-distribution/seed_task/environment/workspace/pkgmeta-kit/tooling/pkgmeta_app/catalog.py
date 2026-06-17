from __future__ import annotations

import json
import runpy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


def load_licenses() -> list[dict[str, Any]]:
    payload = json.loads((DATA_DIR / "licenses.json").read_text(encoding="utf-8"))
    return list(payload["licenses"])


def load_license_index() -> dict[str, dict[str, Any]]:
    return {item["licenseId"]: item for item in load_licenses()}


def load_classifiers() -> list[str]:
    namespace = runpy.run_path(str(DATA_DIR / "trove_classifiers.py"))
    return sorted(namespace["classifiers"])
