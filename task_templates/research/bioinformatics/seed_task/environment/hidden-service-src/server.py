#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
import os
import urllib.parse
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PORT = int(os.environ.get("BIOINFO_SCANPY_PORT", "8143"))
SEED_DIR = Path(os.environ.get("BIOINFO_SCANPY_SEED_DIR", "/opt/bioinfo-scanpy/seed"))
ACCESS_LOG = Path("/var/log/bioinfo-scanpy/access.log")

POLICY = json.loads((SEED_DIR / "current_analysis_policy.json").read_text(encoding="utf-8"))
with (SEED_DIR / "current_marker_panel.csv").open(newline="", encoding="utf-8") as fh:
    MARKER_PANEL = list(csv.DictReader(fh))


def write_record(record: dict) -> None:
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ACCESS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "BioinfoScanpy/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send_json(self, payload: dict | list, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        query = {key: values[-1] for key, values in urllib.parse.parse_qs(parsed.query).items()}
        write_record(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "path": parsed.path,
                "query": query,
                "client": self.headers.get("X-Client", self.headers.get("User-Agent", "")),
            }
        )

        if parsed.path == "/health":
            self._send_json({"ok": True, "service": "bioinfo-scanpy"})
            return
        if parsed.path == "/api/analysis-policy/current":
            self._send_json(POLICY)
            return
        if parsed.path == "/api/marker-panel/current":
            self._send_json({"items": MARKER_PANEL, "count": len(MARKER_PANEL)})
            return

        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
