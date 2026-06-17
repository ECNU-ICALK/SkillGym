#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PORT = int(os.environ.get("REAUCTION_PORT", "8146"))
ACCESS_LOG = Path(os.environ.get("REAUCTION_ACCESS_LOG", "/var/log/real-estate-legal-audit/access.log"))
SEED_DIR = Path(os.environ.get("REAUCTION_SEED_DIR", "/opt/real-estate-legal-audit/seed"))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


ASSET = load_json(SEED_DIR / "authority_asset.json")
COST_MODEL = load_json(SEED_DIR / "cost_model.json")
DECISION_POLICY = load_json(SEED_DIR / "decision_policy.json")
RISK_SIGNALS = load_json(SEED_DIR / "risk_signals.json")


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


def paginate(items: list[dict], cursor: str | None, limit: int) -> tuple[list[dict], str | None]:
    start = int(cursor or "0")
    page = items[start : start + limit]
    next_cursor = str(start + limit) if start + limit < len(items) else None
    return page, next_cursor


class Handler(BaseHTTPRequestHandler):
    server_version = "RealEstateLegalAudit/1.0"

    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query, keep_blank_values=True)

        if path == "/health":
            log_access(self, 200)
            return self._send_json({"ok": True, "service": "real-estate-legal-audit"})

        if path in {"/", "/api", "/api/manifest"}:
            log_access(self, 200)
            return self._send_json(
                {
                    "service": "real-estate-legal-audit",
                    "endpoints": {
                        "asset_current": "/api/asset/current",
                        "cost_model_current": "/api/cost-model/current",
                        "risk_signals": "/api/risk-signals",
                        "decision_policy_current": "/api/decision-policy/current",
                    },
                    "pagination": {
                        "mode": "cursor",
                        "default_limit": 3,
                        "follow_field": "next_cursor",
                    },
                }
            )

        if path == "/api/asset/current":
            log_access(self, 200)
            return self._send_json(ASSET)

        if path == "/api/cost-model/current":
            log_access(self, 200)
            return self._send_json(COST_MODEL)

        if path == "/api/decision-policy/current":
            log_access(self, 200)
            return self._send_json(DECISION_POLICY)

        if path == "/api/risk-signals":
            limit = min(max(int(params.get("limit", ["3"])[0]), 1), 4)
            cursor = params.get("cursor", [None])[0]
            page, next_cursor = paginate(RISK_SIGNALS, cursor, limit)
            log_access(self, 200)
            return self._send_json(
                {
                    "items": page,
                    "page_info": {
                        "next_cursor": next_cursor,
                        "has_next_page": next_cursor is not None,
                        "returned": len(page),
                        "total": len(RISK_SIGNALS),
                    },
                }
            )

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
