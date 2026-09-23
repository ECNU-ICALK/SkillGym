from __future__ import annotations

import json
import os
import ssl
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
TLS_DIR = BASE_DIR / "tls"
CATALOG_PATH = BASE_DIR / "catalog_seed.json"
FILES_DIR = Path(os.environ.get("MODEL_SOURCE_FILES_DIR", "/srv/model-source/files"))
ACCESS_LOG = Path(os.environ.get("MODEL_SOURCE_ACCESS_LOG", "/var/log/model-source/access.log"))
HOST = "0.0.0.0"
PORT = int(os.environ.get("MODEL_SOURCE_PORT", "443"))
USE_TLS = os.environ.get("MODEL_SOURCE_USE_TLS", "1") != "0"
PUBLIC_BASE = os.environ.get("MODEL_SOURCE_PUBLIC_BASE", "https://api.printables.com")


def load_seed() -> dict:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    models = {str(model["id"]): model for model in payload["models"]}
    return {"models": models}


SEED = load_seed()


def record_access(method: str, path: str, handler: BaseHTTPRequestHandler, body: str = "") -> None:
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": method,
        "path": path,
        "client": handler.headers.get("X-Client") or handler.headers.get("User-Agent", ""),
        "host": handler.headers.get("Host", ""),
        "origin": handler.headers.get("Origin", ""),
        "referer": handler.headers.get("Referer", ""),
        "body": body,
    }
    with ACCESS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=True) + "\n")


def match_score(model: dict, query: str) -> int:
    query_terms = [term for term in query.lower().replace("-", " ").split() if term]
    haystack = " ".join(
        [
            model["name"],
            model.get("summary", ""),
            model.get("description", ""),
            " ".join(model.get("search_terms", [])),
            " ".join(model.get("slot_hints", [])),
        ]
    ).lower()
    score = 0
    for term in query_terms:
        if term in haystack:
            score += 2
        if term in model["name"].lower():
            score += 3
    score += min(int(model["downloadCount"]) // 100, 50)
    return score


def search_prints(query: str, limit: int, offset: int) -> dict:
    scored = sorted(
        SEED["models"].values(),
        key=lambda item: (match_score(item, query), int(item["likesCount"]), int(item["downloadCount"])),
        reverse=True,
    )
    scored = [item for item in scored if match_score(item, query) > 0]
    items = scored[offset : offset + limit]
    return {
        "totalCount": len(scored),
        "items": [
            {
                "id": item["id"],
                "name": item["name"],
                "slug": item["slug"],
                "downloadCount": item["downloadCount"],
                "likesCount": item["likesCount"],
                "filesCount": item["filesCount"],
                "user": {"handle": item["user"]["handle"]},
            }
            for item in items
        ],
    }


def print_details(print_id: str) -> dict:
    item = SEED["models"][str(print_id)]
    return {
        "id": item["id"],
        "name": item["name"],
        "slug": item["slug"],
        "summary": item["summary"],
        "description": item["description"],
        "downloadCount": item["downloadCount"],
        "likesCount": item["likesCount"],
        "filesCount": item["filesCount"],
        "user": {"handle": item["user"]["handle"]},
        "license": {
            "id": item["license"]["id"],
            "disallowRemixing": item["license"]["disallowRemixing"],
        },
        "excludeCommercialUsage": item["excludeCommercialUsage"],
        "stls": [
            {
                "id": file_info["id"],
                "name": file_info["name"],
                "fileSize": file_info["fileSize"],
                "folder": "",
                "note": file_info.get("note", ""),
            }
            for file_info in item["files"]
        ],
        "downloadPacks": [
            {
                "id": item["pack"]["id"],
                "fileSize": item["pack"]["fileSize"],
                "fileType": "MODEL_FILES",
            }
        ],
    }


def download_link(print_id: str, file_type: str, ids: list[str]) -> str:
    item = SEED["models"][str(print_id)]
    if file_type == "pack":
        pack_id = str(ids[0])
        if pack_id != str(item["pack"]["id"]):
            raise KeyError(f"Unknown pack id {pack_id} for model {print_id}")
        return f"{PUBLIC_BASE}/files/pack/{pack_id}"
    if file_type == "stl":
        file_id = str(ids[0])
        for file_info in item["files"]:
            if str(file_info["id"]) == file_id:
                return f"{PUBLIC_BASE}/files/stl/{file_id}"
        raise KeyError(f"Unknown file id {file_id} for model {print_id}")
    raise KeyError(f"Unknown file type {file_type}")


class Handler(BaseHTTPRequestHandler):
    server_version = "ModelSource/0.1"

    def _canonical_graphql_headers(self) -> bool:
        user_agent = self.headers.get("User-Agent", "")
        return (
            self.headers.get("Host", "") == "api.printables.com"
            and "Mozilla" in user_agent
            and self.headers.get("Origin", "") == "https://www.printables.com"
            and self.headers.get("Referer", "") == "https://www.printables.com/"
        )

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        record_access("GET", path, self)
        if path == "/healthz":
            self._json({"ok": True, "service": "model-source"})
            return
        if path.startswith("/files/pack/"):
            pack_id = path.rsplit("/", 1)[-1]
            file_path = FILES_DIR / "packs" / f"{pack_id}.zip"
            if not file_path.exists():
                self.send_error(HTTPStatus.NOT_FOUND, "pack not found")
                return
            payload = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if path.startswith("/files/stl/"):
            file_id = path.rsplit("/", 1)[-1]
            file_path = FILES_DIR / "individual" / f"{file_id}.stl"
            if not file_path.exists():
                file_path = FILES_DIR / "individual" / f"{file_id}.3mf"
            if not file_path.exists():
                self.send_error(HTTPStatus.NOT_FOUND, "file not found")
                return
            payload = file_path.read_bytes()
            content_type = "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "route not found")

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""
        text = raw.decode("utf-8")
        record_access("POST", path, self, text)
        if path != "/graphql/":
            self.send_error(HTTPStatus.NOT_FOUND, "route not found")
            return
        if not self._canonical_graphql_headers():
            self._json({"errors": [{"message": "canonical GraphQL headers required"}]}, status=400)
            return
        payload = json.loads(text or "{}")
        query = payload.get("query", "")
        variables = payload.get("variables", {}) or {}
        if "searchPrints2" in query:
            response = {
                "data": {
                    "searchPrints2": search_prints(
                        str(variables.get("q", "")),
                        int(variables.get("limit", 10)),
                        int(variables.get("offset", 0)),
                    )
                }
            }
            self._json(response)
            return
        if "print(id:$id)" in query or "print(id: $id)" in query:
            response = {"data": {"print": print_details(str(variables["id"]))}}
            self._json(response)
            return
        if (
            "getDownloadLink" in query
            and "source:model_detail" in query
            and "files:[{fileType:$ft, ids:$ids}]" in query
        ):
            link = download_link(
                str(variables["printId"]),
                str(variables["ft"]),
                [str(value) for value in variables.get("ids", [])],
            )
            response = {
                "data": {
                    "getDownloadLink": {
                        "ok": True,
                        "errors": [],
                        "output": {"link": link, "ttl": 3600},
                    }
                }
            }
            self._json(response)
            return
        self._json({"errors": [{"message": "unsupported query"}]}, status=400)

    def log_message(self, fmt: str, *args: object) -> None:
        return


def main() -> None:
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    if USE_TLS:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            certfile=str(TLS_DIR / "api.printables.com.crt"),
            keyfile=str(TLS_DIR / "api.printables.com.key"),
        )
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
