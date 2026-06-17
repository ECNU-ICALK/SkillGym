from __future__ import annotations

import json
import runpy
from importlib.resources import files
from typing import Any


def _resource_text(name: str) -> str:
    return files("pkgmeta_kit").joinpath("data", name).read_text(encoding="utf-8")


def load_licenses() -> list[dict[str, Any]]:
    payload = json.loads(_resource_text("licenses.json"))
    return list(payload["licenses"])


def load_license_index() -> dict[str, dict[str, Any]]:
    return {item["licenseId"]: item for item in load_licenses()}


def load_classifiers() -> list[str]:
    data_file = files("pkgmeta_kit").joinpath("data", "trove_classifiers.py")
    namespace = runpy.run_path(str(data_file))
    return sorted(namespace["classifiers"])
