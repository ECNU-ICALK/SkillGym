from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path

from common import FIXTURE_PATH, OUTPUT_ROOT


ACCESS_LOG = Path(os.environ.get("MARKETDATA_ACCESS_LOG", "/var/log/marketdata/access.log"))
DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/app/data"))
SERVICE_ROOT = Path(os.environ.get("TASK_SERVICE_ROOT", "/services/marketdata"))
DATA_HASH_PATH = Path(os.environ.get("TASK_DATA_HASH_PATH", "/opt/task-baselines/data.sha256"))
SERVICE_HASH_PATH = Path(os.environ.get("TASK_SERVICE_HASH_PATH", "/opt/task-baselines/service.sha256"))
HEALTH_URL = os.environ.get("TASK_HEALTH_URL", "http://127.0.0.1:8155/health")

PRE_VERIFIER_LOG = ACCESS_LOG.read_text(encoding="utf-8") if ACCESS_LOG.exists() else ""


def parse_pre_verifier_records() -> list[dict]:
    records = []
    for line in PRE_VERIFIER_LOG.splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        if record.get("client", "").startswith("verifier-"):
            continue
        records.append(record)
    return records


def test_solver_used_live_manifest_catalog_and_market_endpoints_before_verifier() -> None:
    records = parse_pre_verifier_records()
    assert records, "No pre-verifier marketdata traffic was recorded"
    assert any(record["path"] == "/api/manifest" for record in records), "Solver did not query the manifest endpoint"

    required_catalog = {
        ("/api/catalog/coinbase", tuple()),
        ("/api/catalog/coinbase", (("cursor", ("1",)),)),
        ("/api/catalog/kraken", tuple()),
        ("/api/catalog/kraken", (("cursor", ("1",)),)),
    }
    seen_catalog = set()
    for record in records:
        if not record["path"].startswith("/api/catalog/"):
            continue
        seen_catalog.add((record["path"], tuple(sorted((k, tuple(v)) for k, v in record.get("query", {}).items()))))
    assert required_catalog.issubset(seen_catalog), "Solver did not fetch every catalog page"

    expected_market_paths = {
        "/api/ohlcv/coinbase/BTC-USD",
        "/api/ohlcv/coinbase/ETH-USD",
        "/api/ohlcv/kraken/XBTUSD",
        "/api/ohlcv/kraken/ETHUSD",
    }
    seen_market_paths = {record["path"] for record in records if record["path"].startswith("/api/ohlcv/")}
    assert expected_market_paths.issubset(seen_market_paths), "Solver did not fetch all required market OHLCV payloads"


def test_inputs_and_hidden_service_are_unchanged() -> None:
    current_data = subprocess.check_output(f"find {DATA_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum", shell=True, text=True)
    assert current_data == DATA_HASH_PATH.read_text(encoding="utf-8"), "Task input data was modified"

    current_service = subprocess.check_output(
        f"find {SERVICE_ROOT} -type f ! -path '*/__pycache__/*' -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    assert current_service == SERVICE_HASH_PATH.read_text(encoding="utf-8"), "Hidden marketdata service files were modified"


def test_live_service_still_healthy() -> None:
    with urllib.request.urlopen(HEALTH_URL, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    assert payload["ok"] is True
    assert payload["service"] == "marketdata"


def test_output_inventory_is_restricted() -> None:
    expected = {"market_report.json", "liquidity_alerts.csv", "source_manifest.json", "runbook.md"}
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == expected


def test_outputs_do_not_contain_placeholders_or_verifier_strings() -> None:
    for path in OUTPUT_ROOT.iterdir():
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        assert "placeholder" not in text
        assert "verifier" not in text
        assert "todo" not in text
        assert "{{" not in text
        assert "tbd" not in text


def test_fixture_contains_live_only_required_eth_markets() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert "coinbase:ETH-USD" in fixture["markets"]
    assert "kraken:ETHUSD" in fixture["markets"]
