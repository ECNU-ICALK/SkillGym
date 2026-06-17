from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


FIXTURE_PATH = Path(os.environ.get("MARKETDATA_FIXTURE_PATH", "/app/data/service_fixtures/market_data.json"))
ACCESS_LOG = Path(os.environ.get("MARKETDATA_ACCESS_LOG", "/var/log/marketdata/access.log"))
HOST = os.environ.get("MARKETDATA_HOST", "127.0.0.1")
PORT = int(os.environ.get("MARKETDATA_PORT", "8155"))


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


FIXTURE = load_fixture()


def append_access_log(handler: BaseHTTPRequestHandler, query: dict[str, list[str]]) -> None:
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "client": handler.headers.get("X-Client", ""),
        "method": handler.command,
        "path": urlparse(handler.path).path,
        "query": query,
    }
    with ACCESS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def json_response(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def catalog_items(exchange: str, page_index: int) -> list[dict]:
    market_ids = FIXTURE["catalog_pages"][exchange][page_index]
    items = []
    for market_id in market_ids:
        market = FIXTURE["markets"][f"{exchange}:{market_id}"]
        items.append(
            {
                "market_id": market["market_id"],
                "native_symbol": market["native_symbol"],
                "base_asset": market["base_asset"],
                "quote_asset": market["quote_asset"],
                "volume_unit": market["volume_unit"],
                "bar_granularity": market["bar_granularity"],
            }
        )
    return items


class Handler(BaseHTTPRequestHandler):
    server_version = "marketdata/1.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        append_access_log(self, query)

        if parsed.path == "/health":
            json_response(self, {"ok": True, "service": "marketdata"})
            return

        if parsed.path == "/api/manifest":
            base_url = f"http://{HOST}:{PORT}"
            json_response(
                self,
                {
                    "workspace_id": FIXTURE["workspace_id"],
                    "as_of_date": FIXTURE["as_of_date"],
                    "analysis_window_days": FIXTURE["analysis_window_days"],
                    "service_urls": {
                        "catalog": {
                            "coinbase": f"{base_url}/api/catalog/coinbase",
                            "kraken": f"{base_url}/api/catalog/kraken",
                        },
                        "ohlcv_base": f"{base_url}/api/ohlcv",
                    },
                },
            )
            return

        if parsed.path.startswith("/api/catalog/"):
            exchange = parsed.path.rsplit("/", 1)[-1]
            if exchange not in FIXTURE["catalog_pages"]:
                json_response(self, {"error": "unknown exchange"}, status=HTTPStatus.NOT_FOUND)
                return
            cursor = query.get("cursor", [""])[0]
            page_index = 0 if not cursor else int(cursor)
            pages = FIXTURE["catalog_pages"][exchange]
            if page_index < 0 or page_index >= len(pages):
                json_response(self, {"error": "invalid cursor"}, status=HTTPStatus.BAD_REQUEST)
                return
            has_next = page_index + 1 < len(pages)
            json_response(
                self,
                {
                    "exchange": exchange,
                    "items": catalog_items(exchange, page_index),
                    "has_next_page": has_next,
                    "next_cursor": str(page_index + 1) if has_next else None,
                },
            )
            return

        if parsed.path.startswith("/api/ohlcv/"):
            _, _, _, exchange, market_id = parsed.path.split("/", 4)
            market = FIXTURE["markets"].get(f"{exchange}:{market_id}")
            if market is None:
                json_response(self, {"error": "unknown market"}, status=HTTPStatus.NOT_FOUND)
                return
            json_response(
                self,
                {
                    "exchange": market["exchange"],
                    "market_id": market["market_id"],
                    "native_symbol": market["native_symbol"],
                    "base_asset": market["base_asset"],
                    "quote_asset": market["quote_asset"],
                    "volume_unit": market["volume_unit"],
                    "bars_order": market["bars_order"],
                    "bar_granularity": market["bar_granularity"],
                    "bars": market["bars"],
                },
            )
            return

        json_response(self, {"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()

