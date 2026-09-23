from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PORT = int(os.environ.get("REVOPS_SERVICE_PORT", "8144"))
STATE_PATH = Path(os.environ.get("REVOPS_STATE_PATH", "/services/revops/live_state.json"))
LOG_PATH = Path(os.environ.get("REVOPS_ACCESS_LOG", "/var/log/revops/access.log"))

STATE = json.loads(STATE_PATH.read_text(encoding="utf-8"))
ACCOUNTS = STATE["accounts"]
PREVIEWS = STATE["renewal_previews"]
DUNNING = STATE["dunning_events"]


def append_log(record: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


class RevopsHandler(BaseHTTPRequestHandler):
    server_version = "RevopsService/1.0"

    def log_message(self, fmt: str, *args) -> None:
        return

    def _write_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        append_log(
            {
                "method": "GET",
                "path": parsed.path,
                "query": {key: value[:] for key, value in query.items()},
                "client": self.headers.get("X-Client", ""),
                "body": ""
            }
        )

        if parsed.path == "/health":
            self._write_json({"ok": True, "service": "revops"})
            return

        if parsed.path == "/api/manifest":
            self._write_json(
                {
                    "workspace_id": STATE["workspace_id"],
                    "cohort_date": STATE["cohort_date"],
                    "service_urls": {
                        "cohort": f"http://127.0.0.1:{PORT}/api/cohort",
                        "accounts_base": f"http://127.0.0.1:{PORT}/api/accounts"
                    },
                    "page_size_hint": STATE["page_size"]
                }
            )
            return

        if parsed.path == "/api/cohort":
            cursor = query.get("cursor", [None])[0]
            page = None
            for candidate in STATE["cohort_pages"]:
                if candidate["cursor"] == cursor:
                    page = candidate
                    break
            if page is None:
                self._write_json({"error": "cursor_not_found", "cursor": cursor}, status=HTTPStatus.NOT_FOUND)
                return
            self._write_json(
                {
                    "items": [
                        {
                            "account_id": account_id,
                            "company_name": ACCOUNTS[account_id]["company_name"],
                            "crm_deal_id": ACCOUNTS[account_id]["crm_deal_id"]
                        }
                        for account_id in page["items"]
                    ],
                    "has_next_page": page["next_cursor"] is not None,
                    "next_cursor": page["next_cursor"]
                }
            )
            return

        if parsed.path.startswith("/api/accounts/") and parsed.path.endswith("/renewal-preview"):
            account_id = parsed.path.split("/")[3]
            if account_id not in PREVIEWS:
                self._write_json({"error": "account_not_found", "account_id": account_id}, status=HTTPStatus.NOT_FOUND)
                return
            self._write_json(PREVIEWS[account_id])
            return

        if parsed.path.startswith("/api/accounts/") and parsed.path.endswith("/dunning-events"):
            account_id = parsed.path.split("/")[3]
            if account_id not in DUNNING:
                self._write_json({"error": "account_not_found", "account_id": account_id}, status=HTTPStatus.NOT_FOUND)
                return
            self._write_json(DUNNING[account_id])
            return

        if parsed.path.startswith("/api/accounts/"):
            account_id = parsed.path.rsplit("/", 1)[-1]
            account = ACCOUNTS.get(account_id)
            if account is None:
                self._write_json({"error": "account_not_found", "account_id": account_id}, status=HTTPStatus.NOT_FOUND)
                return
            self._write_json(account)
            return

        self._write_json({"error": "not_found", "path": parsed.path}, status=HTTPStatus.NOT_FOUND)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), RevopsHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
