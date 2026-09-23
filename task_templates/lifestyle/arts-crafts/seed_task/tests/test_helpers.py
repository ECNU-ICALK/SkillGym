from __future__ import annotations

import hashlib
import json
import urllib.request
import os
from pathlib import Path


ROOT = Path(os.environ.get("ARTS_CRAFTS_TASK_ROOT", "/root"))
OUTPUT_DIR = ROOT / "answer"
DATA_DIR = ROOT / "environment" / "data"
MODELS_DIR = OUTPUT_DIR / "models"
BUNDLE_PATH = OUTPUT_DIR / "bundle_manifest.json"
AUDIT_PATH = OUTPUT_DIR / "selection_audit.json"
REPORT_PATH = OUTPUT_DIR / "selection_report.md"
BRIEF_PATH = DATA_DIR / "brief" / "workshop_bundle.json"
POLICY_PATH = DATA_DIR / "policy" / "bundle_rules.json"
SHORTLIST_PATH = DATA_DIR / "catalog" / "candidate_shortlist.json"
SEED_PATH = Path(os.environ.get("ARTS_CRAFTS_SEED_PATH", "/services/model-source/catalog_seed.json"))
ACCESS_LOG = Path(os.environ.get("ARTS_CRAFTS_ACCESS_LOG", "/var/log/model-source/access.log"))
MIRROR_ROOT = Path(os.environ.get("ARTS_CRAFTS_MIRROR_ROOT", "/srv/model-source/files"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_models() -> dict[str, dict]:
    seed = load_json(SEED_PATH)
    return {str(model["id"]): model for model in seed["models"]}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_models_from_policy() -> dict[str, dict]:
    brief = load_json(BRIEF_PATH)
    policy = load_json(POLICY_PATH)
    models = seed_models()
    selected: dict[str, dict] = {}
    for slot in brief["slot_order"]:
        chosen = None
        for model in models.values():
            if not license_allowed(model, policy):
                continue
            if not popularity_ok(model, policy):
                continue
            if not slot_match(model, policy, slot):
                continue
            if chosen is None or rank_tuple(model) > rank_tuple(chosen):
                chosen = model
        assert chosen is not None, f"No model satisfied slot {slot}"
        selected[slot] = chosen
    return selected


def rank_tuple(model: dict) -> tuple[int, int, int]:
    return (int(model["downloadCount"]), int(model["likesCount"]), int(model["filesCount"]))


def license_allowed(model: dict, policy: dict) -> bool:
    return (
        model["license"]["id"] in policy["allowed_license_ids"]
        and not model["license"]["disallowRemixing"]
        and not model["excludeCommercialUsage"]
    )


def popularity_ok(model: dict, policy: dict) -> bool:
    return int(model["downloadCount"]) >= int(policy["minimum_download_count"])


def slot_match(model: dict, policy: dict, slot_id: str) -> bool:
    rule = policy["slot_rules"][slot_id]
    text = " ".join(
        [
            model.get("name", ""),
            model.get("summary", ""),
            model.get("description", ""),
        ]
    ).lower()
    required = [term.lower() for term in rule.get("required_terms", [])]
    if slot_id == "tool-storage":
        if not all(term in text for term in required):
            return False
        if int(model["filesCount"]) < int(rule.get("minimum_files_count", 1)):
            return False
    else:
        if not all(term in text for term in required):
            return False
    forbidden = [term.lower() for term in rule.get("forbidden_terms", [])]
    if any(term in text for term in forbidden):
        return False
    preferred = [term.lower() for term in rule.get("preferred_terms", [])]
    if preferred and slot_id != "tool-storage" and not all(term in text for term in preferred):
        return False
    return True


def pre_verifier_records() -> list[dict]:
    if not ACCESS_LOG.exists():
        return []
    records = []
    for line in ACCESS_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if str(record.get("client", "")).startswith("verifier-"):
            continue
        records.append(record)
    return records


def source_health() -> dict:
    health_url = os.environ.get("ARTS_CRAFTS_HEALTH_URL", "https://api.printables.com/healthz")
    req = urllib.request.Request(health_url, headers={"X-Client": "verifier-health"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))
