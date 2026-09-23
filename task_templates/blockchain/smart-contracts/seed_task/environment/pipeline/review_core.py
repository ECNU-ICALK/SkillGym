from __future__ import annotations

import json
from pathlib import Path


def load_policy(data_root: Path) -> dict:
    return json.loads((data_root / "listing_policy.json").read_text(encoding="utf-8"))


def load_token_profiles(data_root: Path) -> list[dict]:
    profiles = []
    for path in sorted((data_root / "token_profiles").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_path"] = path
        profiles.append(payload)
    return profiles


def collect_behavior_findings(*args, **kwargs):
    raise NotImplementedError("Implement token behavior finding extraction")


def scan_protocol_coverage(*args, **kwargs):
    raise NotImplementedError("Implement protocol measure coverage extraction from Solidity files")


def assign_token_decisions(*args, **kwargs):
    raise NotImplementedError("Implement policy-driven token decision assignment")


def build_evidence_index(*args, **kwargs):
    raise NotImplementedError("Implement evidence index generation")
