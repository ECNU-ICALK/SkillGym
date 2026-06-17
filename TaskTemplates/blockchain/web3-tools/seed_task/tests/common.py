from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path


DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/app/data"))
WORKSPACE_ROOT = Path(os.environ.get("TASK_WORKSPACE_ROOT", "/app/workspace/marketwatch"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/app/output/surveillance"))

CONTRACT_PATH = DATA_ROOT / "contracts" / "surveillance_contract.json"
TASK_MANIFEST_PATH = DATA_ROOT / "task_manifest.json"
REFERENCE_EXPORT_PATH = DATA_ROOT / "reference" / "market_reference.csv"
FIXTURE_PATH = DATA_ROOT / "service_fixtures" / "market_data.json"

MARKET_REPORT_PATH = OUTPUT_ROOT / "market_report.json"
LIQUIDITY_ALERTS_PATH = OUTPUT_ROOT / "liquidity_alerts.csv"
SOURCE_MANIFEST_PATH = OUTPUT_ROOT / "source_manifest.json"
RUNBOOK_PATH = OUTPUT_ROOT / "runbook.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_base(base_asset: str, aliases: dict[str, str]) -> str:
    return aliases.get(base_asset, base_asset)


def canonical_symbol(base_asset: str, quote_asset: str, aliases: dict[str, str]) -> str:
    return f"{canonical_base(base_asset, aliases)}/{quote_asset}"


def normalize_bars(market: dict) -> list[dict]:
    bars = list(market["bars"])
    if market["bars_order"] == "newest_first":
        bars.reverse()
    bars.sort(key=lambda row: row["date"])
    return bars


def market_metrics(market: dict, contract: dict) -> tuple[dict, list[dict]]:
    bars = normalize_bars(market)
    last = bars[-1]
    canonical = canonical_symbol(market["base_asset"], market["quote_asset"], contract["base_aliases"])
    recent = bars[-7:]
    if market["volume_unit"] == "base":
        qv7 = sum(float(bar["volume_raw"]) * float(bar["close"]) for bar in recent)
    else:
        qv7 = sum(float(bar["volume_raw"]) for bar in recent)
    spread7 = sum(float(bar["bid_ask_spread"]) * 10000.0 for bar in recent) / len(recent)
    ret1 = float(last["close"]) / float(bars[-2]["close"]) - 1.0
    ret7 = float(last["close"]) / float(bars[-8]["close"]) - 1.0
    ret30 = float(last["close"]) / float(bars[-31]["close"]) - 1.0

    alerts = []
    thresholds = contract["market_alert_thresholds"]
    severity_map = contract["severity_map"]
    if len(bars) < int(contract["history_bars_required"]):
        alerts.append(
            {
                "canonical_symbol": canonical,
                "exchange": market["exchange"],
                "alert_code": "insufficient_history",
                "observed_value": float(len(bars)),
                "threshold": float(contract["history_bars_required"]),
                "severity": severity_map["insufficient_history"],
            }
        )
    if spread7 > float(thresholds["avg_spread_bps_7d_max"]):
        alerts.append(
            {
                "canonical_symbol": canonical,
                "exchange": market["exchange"],
                "alert_code": "wide_avg_spread_bps_7d",
                "observed_value": round(spread7, 6),
                "threshold": float(thresholds["avg_spread_bps_7d_max"]),
                "severity": severity_map["wide_avg_spread_bps_7d"],
            }
        )
    min_qv = float(thresholds["min_quote_volume_7d_usd"][canonical])
    if qv7 < min_qv:
        alerts.append(
            {
                "canonical_symbol": canonical,
                "exchange": market["exchange"],
                "alert_code": "low_quote_volume_7d_usd",
                "observed_value": round(qv7, 3),
                "threshold": min_qv,
                "severity": severity_map["low_quote_volume_7d_usd"],
            }
        )

    entry = {
        "exchange": market["exchange"],
        "native_symbol": market["native_symbol"],
        "canonical_symbol": canonical,
        "latest_date": last["date"],
        "latest_close": round(float(last["close"]), 8),
        "return_1d": round(ret1, 10),
        "return_7d": round(ret7, 10),
        "return_30d": round(ret30, 10),
        "quote_volume_7d_usd": round(qv7, 3),
        "avg_spread_bps_7d": round(spread7, 6),
        "bar_count": len(bars),
        "status": "alert" if alerts else "ok",
    }
    return entry, alerts


def build_expected() -> dict:
    fixture = load_json(FIXTURE_PATH)
    contract = load_json(CONTRACT_PATH)
    symbols = []
    market_alert_rows = []
    exchange_summary = {}
    covered_markets = 0
    full_coverage_symbols = 0

    for tracked in contract["tracked_symbols"]:
        canonical = tracked["canonical_symbol"]
        required = tracked["required_exchanges"]
        market_entries = []
        for exchange in required:
            for market in fixture["markets"].values():
                if market["exchange"] != exchange:
                    continue
                symbol = canonical_symbol(market["base_asset"], market["quote_asset"], contract["base_aliases"])
                if symbol != canonical:
                    continue
                entry, alerts = market_metrics(market, contract)
                market_entries.append(entry)
                market_alert_rows.extend(alerts)
                covered_markets += 1
                summary = exchange_summary.setdefault(exchange, {"markets_covered": 0, "alerts_triggered": 0})
                summary["markets_covered"] += 1
                summary["alerts_triggered"] += len(alerts)

        market_entries.sort(key=lambda row: row["exchange"])
        has_full = len(market_entries) == len(required)
        if has_full:
            full_coverage_symbols += 1
            gap = abs(float(market_entries[0]["latest_close"]) - float(market_entries[1]["latest_close"])) / (
                (float(market_entries[0]["latest_close"]) + float(market_entries[1]["latest_close"])) / 2.0
            ) * 10000.0
            alert_codes = []
            if gap > float(contract["cross_exchange_alert_thresholds"]["close_gap_bps_max"]):
                alert_codes.append("close_gap_bps")
            cross_exchange = {
                "best_return_30d_exchange": max(market_entries, key=lambda row: row["return_30d"])["exchange"],
                "lowest_spread_exchange": min(market_entries, key=lambda row: row["avg_spread_bps_7d"])["exchange"],
                "close_gap_bps": round(gap, 6),
                "has_full_coverage": True,
                "alert_codes": alert_codes,
            }
        else:
            cross_exchange = {
                "best_return_30d_exchange": None,
                "lowest_spread_exchange": None,
                "close_gap_bps": None,
                "has_full_coverage": False,
                "alert_codes": [],
            }
        symbols.append({"canonical_symbol": canonical, "markets": market_entries, "cross_exchange": cross_exchange})

    market_alert_rows.sort(key=lambda row: (row["canonical_symbol"], row["exchange"], row["alert_code"]))
    return {
        "report": {
            "report_id": contract["report_id"],
            "as_of_date": fixture["as_of_date"],
            "analysis_window_days": contract["analysis_window_days"],
            "symbols": symbols,
            "exchange_summary": exchange_summary,
            "coverage_summary": {
                "required_markets": sum(len(symbol["required_exchanges"]) for symbol in contract["tracked_symbols"]),
                "covered_markets": covered_markets,
                "full_coverage_symbols": full_coverage_symbols,
            },
        },
        "alerts": market_alert_rows,
        "source_manifest": {
            "source_files": sorted([str(CONTRACT_PATH), str(TASK_MANIFEST_PATH), str(REFERENCE_EXPORT_PATH), str(FIXTURE_PATH)]),
            "source_sha256": {
                str(CONTRACT_PATH): sha256_file(CONTRACT_PATH),
                str(TASK_MANIFEST_PATH): sha256_file(TASK_MANIFEST_PATH),
                str(REFERENCE_EXPORT_PATH): sha256_file(REFERENCE_EXPORT_PATH),
                str(FIXTURE_PATH): sha256_file(FIXTURE_PATH),
            },
            "records_used": {
                f"{market['exchange']}:{market['native_symbol']}": len(normalize_bars(market))
                for key, market in sorted(fixture["markets"].items())
                if canonical_symbol(market["base_asset"], market["quote_asset"], contract["base_aliases"])
                in {tracked["canonical_symbol"] for tracked in contract["tracked_symbols"]}
            },
            "contract_symbols": [tracked["canonical_symbol"] for tracked in contract["tracked_symbols"]],
            "exchanges": sorted({market["exchange"] for market in fixture["markets"].values()}),
        },
    }


def run_build() -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["MARKETWATCH_CLIENT_NAME"] = "verifier-build"
    return subprocess.run(
        ["python3", str(WORKSPACE_ROOT / "build_surveillance.py")],
        cwd=WORKSPACE_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )


def load_market_report() -> dict:
    return load_json(MARKET_REPORT_PATH)


def load_source_manifest() -> dict:
    return load_json(SOURCE_MANIFEST_PATH)


def load_alert_rows() -> list[dict]:
    with LIQUIDITY_ALERTS_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

