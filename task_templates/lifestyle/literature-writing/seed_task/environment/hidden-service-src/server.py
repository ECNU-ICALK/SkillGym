#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


DATA_ROOT = Path(os.environ.get("LAUNCH_COPY_DATA_ROOT", "/opt/launch-copy-data"))
WORKSPACE_ROOT = Path(os.environ.get("LAUNCH_COPY_WORKSPACE_ROOT", "/workspace"))
LOG_PATH = Path(os.environ.get("LAUNCH_COPY_ACCESS_LOG", "/var/log/launch-copy/access.log"))
PORT = int(os.environ.get("CONTENT_PACK_PORT", "8080"))

SCORE_KEYS = [
    "Technical Grounding",
    "Natural Syntax",
    "Quiet Confidence",
    "Developer Respect",
    "Information Priority",
    "Specificity",
    "Voice Consistency",
    "Earned Claims",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_source_index() -> dict:
    return load_json(DATA_ROOT / "source_index.json")


def load_doc(doc_id: str) -> dict:
    index = load_source_index()
    for entry in index["docs"]:
        if entry["doc_id"] == doc_id:
            return load_json(DATA_ROOT / entry["path"])
    raise KeyError(doc_id)


def load_banned_phrases() -> list[str]:
    return load_json(DATA_ROOT / "banned_phrases.json")["phrases"]


def package_text(package: dict) -> str:
    deliverables = package.get("deliverables", {})
    parts = []
    for key, value in deliverables.items():
        if isinstance(value, dict):
            for field_value in value.values():
                parts.append(str(field_value))
    return "\n".join(parts)


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", text))


def scan_banned_phrases(text: str) -> list[dict]:
    hits = []
    lower = text.lower()
    for phrase in load_banned_phrases():
        if phrase.lower() in lower:
            hits.append(
                {
                    "phrase": phrase,
                    "status": "remove",
                }
            )
    return hits


def compute_scorecard(package: dict, gate_failures: list[str], taboo_scan: list[dict]) -> dict:
    scores = {key: 5 for key in SCORE_KEYS}
    text = package_text(package).lower()

    if taboo_scan:
        scores["Quiet Confidence"] = 2
        scores["Voice Consistency"] = 3
        scores["Earned Claims"] = 3

    if "threads sidebar" not in text or "parallel agents" not in text:
        scores["Information Priority"] = min(scores["Information Priority"], 3)
        scores["Technical Grounding"] = min(scores["Technical Grounding"], 3)

    if "codex" not in text and "agent client protocol" not in text and "acp" not in text:
        scores["Specificity"] = min(scores["Specificity"], 3)
        scores["Technical Grounding"] = min(scores["Technical Grounding"], 3)

    if "rust" not in text and "gpu-accelerated" not in text and "open source" not in text:
        scores["Developer Respect"] = min(scores["Developer Respect"], 3)
        scores["Specificity"] = min(scores["Specificity"], 3)

    if gate_failures:
        scores["Natural Syntax"] = min(scores["Natural Syntax"], 3)

    return scores


def validate_package(package: dict) -> dict:
    work_order = load_json(WORKSPACE_ROOT / "work_order.json")
    failures = []

    if package.get("campaign_id") != work_order["campaign_id"]:
        failures.append("campaign_id mismatch")

    source_trace = package.get("source_trace")
    if not isinstance(source_trace, list) or len(source_trace) < 6:
        failures.append("source_trace incomplete")

    deliverables = package.get("deliverables", {})
    required_deliverables = ["homepage_hero", "feature_page_section", "docs_intro", "release_note", "short_update"]
    for key in required_deliverables:
        if key not in deliverables:
            failures.append(f"missing deliverable: {key}")

    if "homepage_hero" in deliverables:
        hero = deliverables["homepage_hero"]
        headline_words = word_count(hero.get("headline", ""))
        subheadline_words = word_count(hero.get("subheadline", ""))
        body_words = word_count(hero.get("body", ""))
        limits = work_order["word_limits"]["homepage_hero"]
        if headline_words > limits["headline_max_words"]:
            failures.append("homepage headline too long")
        if not (limits["subheadline_min_words"] <= subheadline_words <= limits["subheadline_max_words"]):
            failures.append("homepage subheadline out of range")
        if not (limits["body_min_words"] <= body_words <= limits["body_max_words"]):
            failures.append("homepage body out of range")

    if "feature_page_section" in deliverables:
        body_words = word_count(deliverables["feature_page_section"].get("body", ""))
        limits = work_order["word_limits"]["feature_page_section"]
        if not (limits["body_min_words"] <= body_words <= limits["body_max_words"]):
            failures.append("feature page body out of range")

    if "docs_intro" in deliverables:
        body_words = word_count(deliverables["docs_intro"].get("body", ""))
        limits = work_order["word_limits"]["docs_intro"]
        if not (limits["body_min_words"] <= body_words <= limits["body_max_words"]):
            failures.append("docs intro body out of range")

    if "release_note" in deliverables:
        limits = work_order["word_limits"]["release_note"]
        for field in ["what_changed", "how_it_works", "why_it_matters"]:
            field_words = word_count(deliverables["release_note"].get(field, ""))
            if not (limits["section_min_words"] <= field_words <= limits["section_max_words"]):
                failures.append(f"release note {field} out of range")

    if "short_update" in deliverables:
        body_words = word_count(deliverables["short_update"].get("body", ""))
        limits = work_order["word_limits"]["short_update"]
        if not (limits["body_min_words"] <= body_words <= limits["body_max_words"]):
            failures.append("short update body out of range")

    full_text = package_text(package)
    for topic in ["parallel agents", "threads sidebar", "codex", "open source"]:
        if topic not in full_text.lower():
            failures.append(f"missing topic: {topic}")

    taboo_scan = scan_banned_phrases(full_text)

    revision_notes = package.get("revision_notes")
    if not isinstance(revision_notes, list) or len(revision_notes) < 4:
        failures.append("revision notes incomplete")

    fact_ledger = package.get("fact_ledger")
    if not isinstance(fact_ledger, list) or len(fact_ledger) < 8:
        failures.append("fact ledger incomplete")

    scorecard = compute_scorecard(package, failures, taboo_scan)
    passed = not failures and not taboo_scan and all(score >= 4 for score in scorecard.values())
    details = "quality-gate passed" if passed else "; ".join(failures + [f"banned phrase: {item['phrase']}" for item in taboo_scan])

    return {
        "scorecard": scorecard,
        "banned_phrase_scan": taboo_scan,
        "final_gate": {
            "passed": passed,
            "details": details,
        },
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "LaunchCopyService/1.0"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def write_log(self, status: int, body_bytes: int) -> None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": time.time(),
            "client": self.headers.get("X-Client", ""),
            "method": self.command,
            "path": urlparse(self.path).path,
            "status": status,
            "bytes": body_bytes,
        }
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def send_json(self, payload: object, status: int = 200) -> None:
        data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        self.write_log(status, len(data))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/health":
                self.send_json({"ok": True, "service": "launch-copy-service"})
            elif path == "/api/source-index":
                self.send_json(load_source_index())
            elif path == "/api/work-order":
                self.send_json(load_json(WORKSPACE_ROOT / "work_order.json"))
            elif path == "/api/tone-examples":
                self.send_json(load_json(DATA_ROOT / "tone_examples.json"))
            elif path == "/api/banned-phrases":
                self.send_json(load_json(DATA_ROOT / "banned_phrases.json"))
            elif path == "/api/editorial-constraints":
                self.send_json(load_json(DATA_ROOT / "editorial_constraints.json"))
            elif path == "/api/rejected-draft":
                self.send_json(load_json(DATA_ROOT / "rejected_copy.json"))
            elif path.startswith("/api/document/"):
                doc_id = path.rsplit("/", 1)[-1]
                self.send_json(load_doc(doc_id))
            else:
                self.send_json({"error": "not found"}, status=404)
        except Exception as exc:
            self.send_json({"error": type(exc).__name__, "message": str(exc)}, status=500)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/quality-gate":
                payload = self.read_json_body()
                self.send_json(validate_package(payload))
            else:
                self.send_json({"error": "not found"}, status=404)
        except Exception as exc:
            self.send_json({"error": type(exc).__name__, "message": str(exc)}, status=500)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
