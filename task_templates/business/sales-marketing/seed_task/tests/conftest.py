from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path


WORKSPACE = Path("/root/workspace")
INPUT_ROOT = WORKSPACE / "seo_inputs"
OUTPUT_ROOT = Path("/root/output")
SITE_ROOT = WORKSPACE / "site"

REPORT_PATH = OUTPUT_ROOT / "seo_fixes_report.json"
CSV_PATH = OUTPUT_ROOT / "keyword_coverage.csv"
SUMMARY_PATH = OUTPUT_ROOT / "growth_summary.md"

MANIFEST = json.loads((INPUT_ROOT / "site_manifest.json").read_text(encoding="utf-8"))
KEYWORD_ROWS = {
    row["page_id"]: row
    for row in csv.DictReader((INPUT_ROOT / "keyword_map.csv").open(newline="", encoding="utf-8"))
}


def fetch_json(path: str, client: str = "verifier-main") -> dict:
    req = urllib.request.Request(
        f"http://127.0.0.1:8139{path}",
        headers={"X-Client": client},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_json(path: Path) -> dict:
    assert path.exists(), f"Missing {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv_rows() -> list[dict]:
    assert CSV_PATH.exists(), f"Missing {CSV_PATH}"
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
