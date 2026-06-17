from __future__ import annotations

from common import (
    LIQUIDITY_ALERTS_PATH,
    MARKET_REPORT_PATH,
    RUNBOOK_PATH,
    SOURCE_MANIFEST_PATH,
    build_expected,
    load_alert_rows,
    load_market_report,
    load_source_manifest,
    run_build,
)


def test_required_output_files_exist() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    assert MARKET_REPORT_PATH.exists(), "Missing /app/output/surveillance/market_report.json"
    assert LIQUIDITY_ALERTS_PATH.exists(), "Missing /app/output/surveillance/liquidity_alerts.csv"
    assert SOURCE_MANIFEST_PATH.exists(), "Missing /app/output/surveillance/source_manifest.json"
    assert RUNBOOK_PATH.exists(), "Missing /app/output/surveillance/runbook.md"


def test_market_report_matches_recomputed_expected_values() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    assert load_market_report() == build_expected()["report"]


def test_alert_csv_matches_threshold_evaluation() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    expected_rows = build_expected()["alerts"]
    actual_rows = load_alert_rows()
    assert len(actual_rows) == len(expected_rows), "Unexpected alert row count"
    for expected, actual in zip(expected_rows, actual_rows, strict=True):
        assert actual["canonical_symbol"] == expected["canonical_symbol"]
        assert actual["exchange"] == expected["exchange"]
        assert actual["alert_code"] == expected["alert_code"]
        assert float(actual["observed_value"]) == float(expected["observed_value"])
        assert float(actual["threshold"]) == float(expected["threshold"])
        assert actual["severity"] == expected["severity"]


def test_source_manifest_and_runbook_are_consistent() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    assert load_source_manifest() == build_expected()["source_manifest"]
    text = RUNBOOK_PATH.read_text(encoding="utf-8")
    assert "Collection" in text
    assert "Checks" in text
    assert "Outputs" in text
    assert "/api/manifest" in text
    assert "catalog" in text.lower()
    assert "ohlcv" in text.lower()
