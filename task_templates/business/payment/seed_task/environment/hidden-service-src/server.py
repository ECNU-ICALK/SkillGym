from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


HOST = "127.0.0.1"
PORT = int(os.environ.get("AP_REVIEW_PORT", "8148"))
STATE_PATH = Path(os.environ.get("AP_REVIEW_STATE_PATH", "/services/ap-review/live_review.json"))
ACCESS_LOG = Path(os.environ.get("AP_REVIEW_ACCESS_LOG", "/var/log/ap-review/access.log"))


def load_state() -> dict:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def append_log(path: str, query: dict[str, list[str]], client: str) -> None:
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "path": path,
        "query": query,
        "client": client,
    }
    with ACCESS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "ap-review/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        client = self.headers.get("X-Client") or self.headers.get("User-Agent", "")
        append_log(parsed.path, query, client)

        if parsed.path == "/health":
            self._json({"ok": True, "service": "ap-review"})
            return

        state = load_state()
        documents = state["documents"]
        page_size = int(state["page_size"])
        base_url = f"http://{HOST}:{PORT}"

        if parsed.path == "/api/manifest":
            self._json(
                {
                    "service": "ap-review",
                    "batch_id": state["batch_id"],
                    "document_count": len(documents),
                    "service_urls": {
                        "documents": f"{base_url}/api/documents",
                        "document_base": f"{base_url}/api/documents",
                    },
                }
            )
            return

        if parsed.path == "/api/documents":
            page = int(query.get("page", ["1"])[0])
            start = (page - 1) * page_size
            end = start + page_size
            items = [
                {
                    "doc_id": item["doc_id"],
                    "source_file": item["source_file"],
                }
                for item in documents[start:end]
            ]
            self._json(
                {
                    "items": items,
                    "page": page,
                    "has_next_page": end < len(documents),
                    "next_page": page + 1 if end < len(documents) else None,
                }
            )
            return

        if parsed.path.startswith("/api/documents/"):
            doc_id = parsed.path.rsplit("/", 1)[-1]
            for item in documents:
                if item["doc_id"] == doc_id:
                    self._json(item)
                    return
            self._json({"error": f"unknown document {doc_id}"}, status=HTTPStatus.NOT_FOUND)
            return

        self._json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
