#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PORT = int(os.environ.get("HF_PLANNER_PORT", "8137"))
ACCESS_LOG = Path(os.environ.get("HF_PLANNER_ACCESS_LOG", "/var/log/health-fitness-planner/access.log"))
SEED_DIR = Path(os.environ.get("HF_PLANNER_SEED_DIR", "/opt/health-fitness-planner/seed"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


POLICY = load_json(SEED_DIR / "program_policy.json")
EXERCISES = load_json(SEED_DIR / "exercise_catalog.json")["exercises"]
FOODS = load_csv(SEED_DIR / "food_catalog.csv")
EXERCISE_BY_ID = {row["exercise_id"]: row for row in EXERCISES}
FOOD_BY_ID = {row["food_id"]: row for row in FOODS}


def log_access(handler: BaseHTTPRequestHandler, status: int) -> None:
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": handler.command,
        "path": urlparse(handler.path).path,
        "query": parse_qs(urlparse(handler.path).query, keep_blank_values=True),
        "client": handler.headers.get("X-Client", ""),
        "status": status
    }
    with ACCESS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def parse_bool(raw: str | None) -> bool | None:
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in {"true", "1", "yes"}:
        return True
    if value in {"false", "0", "no"}:
        return False
    return None


def paginate(items: list[dict], cursor: str | None, limit: int) -> tuple[list[dict], str | None]:
    start = int(cursor or "0")
    page = items[start : start + limit]
    next_cursor = str(start + limit) if start + limit < len(items) else None
    return page, next_cursor


class Handler(BaseHTTPRequestHandler):
    server_version = "HealthFitnessPlanner/1.0"

    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query, keep_blank_values=True)
        path = parsed.path

        if path == "/health":
            log_access(self, 200)
            return self._send_json({"ok": True, "service": "health-fitness-planner"})

        if path in {"/", "/api", "/api/manifest"}:
            log_access(self, 200)
            return self._send_json({
                "service": "health-fitness-planner",
                "endpoints": {
                    "policy_current": "/api/policy/current",
                    "exercises": "/api/exercises",
                    "foods": "/api/foods"
                },
                "pagination": {
                    "mode": "cursor",
                    "default_limit": 4,
                    "follow_field": "next_cursor"
                }
            })

        if path == "/api/policy/current":
            log_access(self, 200)
            return self._send_json(POLICY)

        if path == "/api/exercises":
            items = EXERCISES
            approved = parse_bool(params.get("approved", [None])[0])
            language = params.get("language", [None])[0]
            primary_muscle = params.get("primary_muscle", [None])[0]
            substitution_group = params.get("substitution_group", [None])[0]
            if approved is not None:
                items = [row for row in items if bool(row["approved"]) == approved]
            if language:
                items = [row for row in items if row["language"] == language]
            if primary_muscle:
                items = [row for row in items if row["primary_muscle"] == primary_muscle]
            if substitution_group:
                items = [row for row in items if row["substitution_group"] == substitution_group]
            limit = min(max(int(params.get("limit", ["4"])[0]), 1), 6)
            cursor = params.get("cursor", [None])[0]
            page, next_cursor = paginate(items, cursor, limit)
            log_access(self, 200)
            return self._send_json({
                "items": page,
                "page_info": {
                    "next_cursor": next_cursor,
                    "has_next_page": next_cursor is not None,
                    "returned": len(page),
                    "total": len(items)
                }
            })

        if path.startswith("/api/exercises/"):
            exercise_id = path.rsplit("/", 1)[-1]
            item = EXERCISE_BY_ID.get(exercise_id)
            if item is None:
                log_access(self, 404)
                return self._send_json({"error": "exercise_not_found"}, status=404)
            log_access(self, 200)
            return self._send_json(item)

        if path == "/api/foods":
            items = FOODS
            edible = parse_bool(params.get("edible", [None])[0])
            language = params.get("language", [None])[0]
            slot = params.get("slot", [None])[0]
            if edible is not None:
                items = [row for row in items if (row["edible"].lower() == "true") == edible]
            if language:
                items = [row for row in items if row["language"] == language]
            if slot:
                items = [row for row in items if slot in row["slot_tags"].split(";")]
            limit = min(max(int(params.get("limit", ["4"])[0]), 1), 6)
            cursor = params.get("cursor", [None])[0]
            page, next_cursor = paginate(items, cursor, limit)
            log_access(self, 200)
            return self._send_json({
                "items": page,
                "page_info": {
                    "next_cursor": next_cursor,
                    "has_next_page": next_cursor is not None,
                    "returned": len(page),
                    "total": len(items)
                }
            })

        if path.startswith("/api/foods/"):
            food_id = path.rsplit("/", 1)[-1]
            item = FOOD_BY_ID.get(food_id)
            if item is None:
                log_access(self, 404)
                return self._send_json({"error": "food_not_found"}, status=404)
            log_access(self, 200)
            return self._send_json(item)

        log_access(self, 404)
        self._send_json({"error": "not_found"}, status=404)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> None:
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
