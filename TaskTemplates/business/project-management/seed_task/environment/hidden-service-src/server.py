from __future__ import annotations

import json
import math
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PORT = int(os.environ.get("PROJECT_PLANNING_PORT", "8137"))
ROOT = Path("/services/project-planning")
DATA_PATH = Path(os.environ.get("PLANNING_DATA_PATH", str(ROOT / "live_backlog.json")))
LOG_PATH = Path(os.environ.get("PLANNING_ACCESS_LOG", "/var/log/project-planning/access.log"))


def load_items() -> list[dict]:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return sorted(payload["items"], key=lambda item: item["item_id"])


ITEMS = load_items()
ITEMS_BY_ID = {item["item_id"]: item for item in ITEMS}


def append_log(record: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


class PlanningHandler(BaseHTTPRequestHandler):
    server_version = "ProjectPlanningService/1.0"

    def _write_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        append_log(
            {
                "method": "GET",
                "path": parsed.path,
                "query": {key: value[:] for key, value in query.items()},
                "client": self.headers.get("X-Client", ""),
                "body": "",
            }
        )

        if parsed.path == "/health":
            self._write_json({"ok": True, "service": "project-planning"})
            return

        if parsed.path == "/api/items":
            page = max(1, int(query.get("page", ["1"])[0]))
            page_size = max(1, min(50, int(query.get("page_size", ["5"])[0])))
            total_items = len(ITEMS)
            total_pages = max(1, math.ceil(total_items / page_size))
            start = (page - 1) * page_size
            stop = start + page_size
            page_items = ITEMS[start:stop]
            self._write_json(
                {
                    "page": page,
                    "page_size": page_size,
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "next_page": page + 1 if page < total_pages else None,
                    "items": [
                        {
                            "item_id": item["item_id"],
                            "title": item["title"],
                            "priority": item["priority"],
                            "story_points": item["story_points"],
                            "owner_role": item["owner_role"],
                            "milestone_date": item["milestone_date"],
                            "current_status": item["current_status"],
                            "source_state": item["source_state"],
                            "detail_path": f"/api/items/{item['item_id']}"
                        }
                        for item in page_items
                    ]
                }
            )
            return

        if parsed.path.startswith("/api/items/"):
            item_id = parsed.path.rsplit("/", 1)[-1]
            item = ITEMS_BY_ID.get(item_id)
            if item is None:
                self._write_json({"error": "item_not_found", "item_id": item_id}, status=HTTPStatus.NOT_FOUND)
                return
            self._write_json(item)
            return

        self._write_json({"error": "not_found", "path": parsed.path}, status=HTTPStatus.NOT_FOUND)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), PlanningHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
