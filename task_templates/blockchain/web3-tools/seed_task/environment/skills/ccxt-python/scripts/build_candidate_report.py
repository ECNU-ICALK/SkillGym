from __future__ import annotations

import csv
import hashlib
import json
import os
import urllib.request
from pathlib import Path


DATA_ROOT = Path("/app/data")
OUTPUT_ROOT = Path(os.environ.get("CCXT_PYTHON_CANDIDATE_ROOT", "/tmp/ccxt-python-candidate"))
CLIENT_NAME = "skill-build-candidate"

CONTRACT_PATH = DATA_ROOT / "contracts" / "surveillance_contract.json"
TASK_MANIFEST_PATH = DATA_ROOT / "task_manifest.json"
REFERENCE_EXPORT_PATH = DATA_ROOT / "reference" / "market_reference.csv"
FIXTURE_PATH = DATA_ROOT / "service_fixtures" / "market_data.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": CLIENT_NAME})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_base(base_asset: str, aliases: dict[str, str]) -> str:
    return aliases.get(base_asset, base_asset)


def canonical_symbol(base_asset: str, quote_asset: str, aliases: dict[str, str]) -> str:
    return f"{canonical_base(base_asset, aliases)}/{quote_asset}"


def normalize_bars(payload: dict) -> list[dict]:
    bars = list(payload["bars"])
    if payload["bars_order"] == "newest_first":
        bars.reverse()
    bars.sort(key=lambda row: row["date"])
    return bars


def compute_market_entry(payload: dict, contract: dict) -> tuple[dict, list[dict]]:
    bars = normalize_bars(payload)
    canonical = canonical_symbol(payload["base_asset"], payload["quote_asset"], contract["base_aliases"])
    latest = bars[-1]
    recent = bars[-7:]
    if payload["volume_unit"] == "base":
        quote_volume_7d = sum(float(bar["volume_raw"]) * float(bar["close"]) for bar in recent)
    else:
        quote_volume_7d = sum(float(bar["volume_raw"]) for bar in recent)
    avg_spread = sum(float(bar["bid_ask_spread"]) * 10000.0 for bar in recent) / len(recent)
    return_1d = float(latest["close"]) / float(bars[-2]["close"]) - 1.0
    return_7d = float(latest["close"]) / float(bars[-8]["close"]) - 1.0
    return_30d = float(latest["close"]) / float(bars[-31]["close"]) - 1.0

    thresholds = contract["market_alert_thresholds"]
    severity_map = contract["severity_map"]
    alerts = []
    if len(bars) < int(contract["history_bars_required"]):
        alerts.append(
            {
                "canonical_symbol": canonical,
                "exchange": payload["exchange"],
                "alert_code": "insufficient_history",
                "observed_value": float(len(bars)),
                "threshold": float(contract["history_bars_required"]),
                "severity": severity_map["insufficient_history"],
            }
        )
    if avg_spread > float(thresholds["avg_spread_bps_7d_max"]):
        alerts.append(
            {
                "canonical_symbol": canonical,
                "exchange": payload["exchange"],
                "alert_code": "wide_avg_spread_bps_7d",
                "observed_value": round(avg_spread, 6),
                "threshold": float(thresholds["avg_spread_bps_7d_max"]),
                "severity": severity_map["wide_avg_spread_bps_7d"],
            }
        )
    min_qv = float(thresholds["min_quote_volume_7d_usd"][canonical])
    if quote_volume_7d < min_qv:
        alerts.append(
            {
                "canonical_symbol": canonical,
                "exchange": payload["exchange"],
                "alert_code": "low_quote_volume_7d_usd",
                "observed_value": round(quote_volume_7d, 3),
                "threshold": min_qv,
                "severity": severity_map["low_quote_volume_7d_usd"],
            }
        )

    entry = {
        "exchange": payload["exchange"],
        "native_symbol": payload["native_symbol"],
        "canonical_symbol": canonical,
        "latest_date": latest["date"],
        "latest_close": round(float(latest["close"]), 8),
        "return_1d": round(return_1d, 10),
        "return_7d": round(return_7d, 10),
        "return_30d": round(return_30d, 10),
        "quote_volume_7d_usd": round(quote_volume_7d, 3),
        "avg_spread_bps_7d": round(avg_spread, 6),
        "bar_count": len(bars),
        "status": "alert" if alerts else "ok",
    }
    return entry, alerts


def main() -> None:
    contract = load_json(CONTRACT_PATH)
    task_manifest = load_json(TASK_MANIFEST_PATH)
    live_manifest = fetch_json(task_manifest["manifest_endpoint"])

    catalog_items = []
    for exchange, url in live_manifest["service_urls"]["catalog"].items():
        cursor = None
        while True:
            page_url = url if cursor is None else f"{url}?cursor={cursor}"
            page = fetch_json(page_url)
            for item in page["items"]:
                item["exchange"] = exchange
            catalog_items.extend(page["items"])
            if not page["has_next_page"]:
                break
            cursor = page["next_cursor"]

    tracked_by_exchange = {
        (item["base_asset"], item["quote_asset"], exchange): item["canonical_symbol"]
        for item in contract["tracked_symbols"]
        for exchange in item["required_exchanges"]
    }
    market_entries_by_symbol = {item["canonical_symbol"]: [] for item in contract["tracked_symbols"]}
    market_alerts = []
    exchange_summary: dict[str, dict] = {}

    for item in catalog_items:
        key = (
            canonical_base(item["base_asset"], contract["base_aliases"]),
            item["quote_asset"],
            item["exchange"],
        )
        if key not in tracked_by_exchange:
            continue
        payload = fetch_json(f"{live_manifest['service_urls']['ohlcv_base']}/{item['exchange']}/{item['market_id']}")
        entry, alerts = compute_market_entry(payload, contract)
        market_entries_by_symbol[entry["canonical_symbol"]].append(entry)
        market_alerts.extend(alerts)
        summary = exchange_summary.setdefault(item["exchange"], {"markets_covered": 0, "alerts_triggered": 0})
        summary["markets_covered"] += 1
        summary["alerts_triggered"] += len(alerts)

    symbol_rows = []
    full_coverage_symbols = 0
    covered_markets = 0
    for tracked_symbol in contract["tracked_symbols"]:
        canonical = tracked_symbol["canonical_symbol"]
        entries = sorted(market_entries_by_symbol[canonical], key=lambda row: row["exchange"])
        covered_markets += len(entries)
        has_full = len(entries) == len(tracked_symbol["required_exchanges"])
        if has_full:
            full_coverage_symbols += 1
            gap = abs(float(entries[0]["latest_close"]) - float(entries[1]["latest_close"])) / (
                (float(entries[0]["latest_close"]) + float(entries[1]["latest_close"])) / 2.0
            ) * 10000.0
            alert_codes = []
            if gap > float(contract["cross_exchange_alert_thresholds"]["close_gap_bps_max"]):
                alert_codes.append("close_gap_bps")
            cross_exchange = {
                "best_return_30d_exchange": max(entries, key=lambda row: row["return_30d"])["exchange"],
                "lowest_spread_exchange": min(entries, key=lambda row: row["avg_spread_bps_7d"])["exchange"],
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
        symbol_rows.append({"canonical_symbol": canonical, "markets": entries, "cross_exchange": cross_exchange})

    report = {
        "report_id": contract["report_id"],
        "as_of_date": live_manifest["as_of_date"],
        "analysis_window_days": contract["analysis_window_days"],
        "symbols": symbol_rows,
        "exchange_summary": exchange_summary,
        "coverage_summary": {
            "required_markets": sum(len(item["required_exchanges"]) for item in contract["tracked_symbols"]),
            "covered_markets": covered_markets,
            "full_coverage_symbols": full_coverage_symbols,
        },
    }
    source_manifest = {
        "source_files": sorted([str(CONTRACT_PATH), str(TASK_MANIFEST_PATH), str(REFERENCE_EXPORT_PATH), str(FIXTURE_PATH)]),
        "source_sha256": {
            str(CONTRACT_PATH): sha256_file(CONTRACT_PATH),
            str(TASK_MANIFEST_PATH): sha256_file(TASK_MANIFEST_PATH),
            str(REFERENCE_EXPORT_PATH): sha256_file(REFERENCE_EXPORT_PATH),
            str(FIXTURE_PATH): sha256_file(FIXTURE_PATH),
        },
        "records_used": {
            f"{entry['exchange']}:{entry['native_symbol']}": entry["bar_count"]
            for symbol in symbol_rows
            for entry in symbol["markets"]
        },
        "contract_symbols": [item["canonical_symbol"] for item in contract["tracked_symbols"]],
        "exchanges": sorted({entry["exchange"] for symbol in symbol_rows for entry in symbol["markets"]}),
    }
    runbook = "\n".join(
        [
            "# Collection",
            "- Read the local task manifest and query the live manifest endpoint.",
            "- Request `/api/manifest` before collecting any market payloads.",
            "- Walk every catalog page for every exchange.",
            "- Fetch OHLCV payloads for each required market.",
            "",
            "# Checks",
            "- Normalize native base asset aliases before building canonical symbols.",
            "- Sort daily bars into ascending date order before computing returns.",
            "- Reconcile `volume_unit` before computing quote volume metrics.",
            "",
            "# Outputs",
            "- Write the four delivery files into the target output directory.",
        ]
    ) + "\n"

    market_alerts.sort(key=lambda row: (row["canonical_symbol"], row["exchange"], row["alert_code"]))
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "market_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    with (OUTPUT_ROOT / "liquidity_alerts.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["canonical_symbol", "exchange", "alert_code", "observed_value", "threshold", "severity"],
        )
        writer.writeheader()
        for row in market_alerts:
            writer.writerow(row)
    (OUTPUT_ROOT / "source_manifest.json").write_text(json.dumps(source_manifest, indent=2, sort_keys=True), encoding="utf-8")
    (OUTPUT_ROOT / "runbook.md").write_text(runbook, encoding="utf-8")
    print(f"Wrote candidate delivery to {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
