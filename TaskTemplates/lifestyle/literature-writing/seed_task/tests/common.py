from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path


OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/root/final_launch_copy_package.json"))
WORK_ORDER_PATH = Path(os.environ.get("WORK_ORDER_PATH", "/workspace/work_order.json"))
REJECTED_COPY_PATH = Path(os.environ.get("REJECTED_COPY_PATH", "/workspace/drafts/rejected_copy.json"))
EDITORIAL_CONSTRAINTS_PATH = Path(os.environ.get("EDITORIAL_CONSTRAINTS_PATH", "/workspace/notes/editorial_constraints.json"))
SOURCE_INDEX_PATH = Path(os.environ.get("SOURCE_INDEX_PATH", "/opt/launch-copy-data/source_index.json"))
BANNED_PHRASES_PATH = Path(os.environ.get("BANNED_PHRASES_PATH", "/opt/launch-copy-data/banned_phrases.json"))
DATA_ROOT = Path(os.environ.get("LAUNCH_COPY_DATA_ROOT", "/opt/launch-copy-data"))
SERVICE_BASE_URL = os.environ.get("SERVICE_BASE_URL", "http://127.0.0.1:8080")

DELIVERABLE_FIELDS = {
    "homepage_hero": ["headline", "subheadline", "body"],
    "feature_page_section": ["title", "body"],
    "docs_intro": ["title", "body"],
    "release_note": ["title", "what_changed", "how_it_works", "why_it_matters"],
    "short_update": ["body"],
}

USED_IN_FIELDS = {
    "homepage_hero.headline",
    "homepage_hero.subheadline",
    "homepage_hero.body",
    "feature_page_section.title",
    "feature_page_section.body",
    "docs_intro.title",
    "docs_intro.body",
    "release_note.title",
    "release_note.what_changed",
    "release_note.how_it_works",
    "release_note.why_it_matters",
    "short_update.body",
}


def load_json(path: Path) -> dict:
    assert path.exists(), f"Missing {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_json(path: str) -> dict:
    req = urllib.request.Request(
        SERVICE_BASE_URL.rstrip("/") + path,
        headers={"X-Client": "verifier-fetch"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SERVICE_BASE_URL.rstrip("/") + path,
        data=data,
        headers={"Content-Type": "application/json", "X-Client": "verifier-post"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", text))


def package_text(payload: dict) -> str:
    parts = []
    for value in payload["deliverables"].values():
        if isinstance(value, dict):
            parts.extend(str(field_value) for field_value in value.values())
    return "\n".join(parts)


def allowed_source_refs() -> set[str]:
    refs = {
        "/workspace/work_order.json",
        "/workspace/work_order.json#campaign_id",
        "/workspace/service_manifest.json",
        "/workspace/drafts/rejected_copy.json",
        "/workspace/notes/editorial_constraints.json",
        "/workspace/examples/approved_copy/example_01.md",
        "/workspace/examples/approved_copy/example_02.md",
        "/api/source-index",
        "/api/tone-examples",
        "/api/banned-phrases",
        "/api/editorial-constraints",
        "/api/rejected-draft",
        f"{SERVICE_BASE_URL}/api/tone-examples",
        f"{SERVICE_BASE_URL}/api/banned-phrases",
        f"{SERVICE_BASE_URL}/api/editorial-constraints",
        f"{SERVICE_BASE_URL}/api/rejected-draft",
    }
    source_index = load_json(SOURCE_INDEX_PATH)
    for entry in source_index["docs"]:
        refs.add(f"/api/document/{entry['doc_id']}")
        refs.add(f"{SERVICE_BASE_URL}/api/document/{entry['doc_id']}")
        packet = load_json(DATA_ROOT / entry["path"])
        for fact in packet["facts"]:
            refs.add(f"/api/document/{entry['doc_id']}#{fact['fact_id']}")
            refs.add(f"{SERVICE_BASE_URL}/api/document/{entry['doc_id']}#{fact['fact_id']}")
    return refs
