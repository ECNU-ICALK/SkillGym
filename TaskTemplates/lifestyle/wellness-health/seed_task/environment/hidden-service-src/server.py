#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PORT = int(os.environ.get("WELLNESS_PLANNER_PORT", "8147"))
ACCESS_LOG = Path(os.environ.get("WELLNESS_PLANNER_ACCESS_LOG", "/var/log/wellness-planner/access.log"))
SEED_DIR = Path(os.environ.get("WELLNESS_PLANNER_SEED_DIR", "/opt/wellness-planner/seed"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


CONDITIONS = load_json(SEED_DIR / "conditions_hourly.json")
BY_DATE = {row["date_local"]: row["hours"] for row in CONDITIONS["days"]}


def log_access(handler: BaseHTTPRequestHandler, status: int) -> None:
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": handler.command,
        "path": urlparse(handler.path).path,
        "query": parse_qs(urlparse(handler.path).query, keep_blank_values=True),
        "client": handler.headers.get("X-Client", ""),
        "status": status,
    }
    with ACCESS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "WellnessPlanner/1.0"

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
            return self._send_json({"ok": True, "service": "wellness-planner"})

        if path in {"/", "/api", "/api/manifest"}:
            log_access(self, 200)
            return self._send_json({
                "service": "wellness-planner",
                "generated_at": CONDITIONS["generated_at"],
                "required_dates": CONDITIONS["required_dates"],
                "timezone": CONDITIONS["timezone"],
                "endpoints": {
                    "hourly_conditions": "/api/conditions/hourly?date=YYYY-MM-DD",
                },
                "notes": [
                    "Use the local planning service for current conditions.",
                    "Earlier exports may not cover the full planning window.",
                ],
            })

        if path == "/api/conditions/hourly":
            date_local = params.get("date", [""])[0]
            hours = BY_DATE.get(date_local)
            if hours is None:
                log_access(self, 404)
                return self._send_json({"error": "date_not_found"}, status=404)
            log_access(self, 200)
            return self._send_json({
                "date_local": date_local,
                "timezone": CONDITIONS["timezone"],
                "hours": hours,
            })

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
