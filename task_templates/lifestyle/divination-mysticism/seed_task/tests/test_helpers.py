from __future__ import annotations

import hashlib
import io
import itertools
import json
import os
import tarfile
from datetime import datetime
from pathlib import Path


ROOT = Path(os.environ.get("DIVINATION_TASK_ROOT", "/root"))
OUTPUT_DIR = ROOT / "answer"
DATA_DIR = ROOT / "environment" / "data"
EVIDENCE_DIR = OUTPUT_DIR / "evidence"
SCHEDULE_PATH = OUTPUT_DIR / "observance_schedule.json"
RESOLUTION_PATH = OUTPUT_DIR / "date_resolution.json"
AUDIT_PATH = OUTPUT_DIR / "source_audit.json"
REPORT_PATH = OUTPUT_DIR / "selection_report.md"
BRIEF_PATH = DATA_DIR / "brief" / "program_request.json"
CATALOG_PATH = DATA_DIR / "catalog" / "observance_catalog.json"
OPS_PATH = DATA_DIR / "ops" / "venue_constraints.json"
POLICY_PATH = DATA_DIR / "policy" / "schedule_rules.json"
ARCHIVE_PATH = Path(os.environ.get("DIVINATION_ARCHIVE_PATH", "/root/.x-cmd.root/data/ccal/data/ccal-data-v0.0.6.tar.xz"))
ACCESS_LOG = Path(os.environ.get("CCAL_ACCESS_LOG", "/var/log/ccal/access.log"))

CCAL_HEADER = [
    "gregorian_date",
    "lunar_date",
    "month_day_count",
    "jianchu_day",
    "weekday_cn",
    "ganzhi",
    "current_solar_term",
    "next_solar_term",
    "solar_festival",
    "memorial_tag",
    "misc_tag",
    "yi",
    "ji",
]
ARCHIVE_NATIVE_HEADER = "Date\tRi\tYue\tZhiXingWeekday\tBaZi\tJieQi\tXiaGeJieQi\tLegal Holiday\tWRN\tRelated Holiday\tYi\tJi"

WEEKEND_NAMES = {"Saturday", "Sunday"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def catalog() -> list[dict]:
    return load_json(CATALOG_PATH)["observances"]


def ops() -> dict:
    return load_json(OPS_PATH)


def policy() -> dict:
    return load_json(POLICY_PATH)


def resolve_candidates() -> dict[str, dict]:
    by_rule = {f"2026-{item['lunar_rule']}": item for item in catalog()}
    resolved: dict[str, dict] = {}
    with tarfile.open(ARCHIVE_PATH, "r:xz") as tf:
        for member in tf.getmembers():
            if not member.name.startswith("ccal-data/lunar/2026_"):
                continue
            extracted = tf.extractfile(member)
            assert extracted is not None
            for raw in extracted:
                row = raw.decode("utf-8").rstrip("\n")
                cols = row.split("\t")
                solar_date, lunar_date = cols[0], cols[1]
                candidate = by_rule.get(lunar_date)
                if not candidate:
                    continue
                dt = datetime.strptime(solar_date, "%Y-%m-%d")
                resolved[candidate["observance_id"]] = {
                    **candidate,
                    "gregorian_date": solar_date,
                    "weekday": dt.strftime("%A"),
                    "source_month_file": member.name,
                    "source_row": row,
                }
    assert len(resolved) == len(catalog()), "Some candidate observances were not resolved from the archive"
    return resolved


def valid_combo(entries: tuple[dict, ...]) -> bool:
    current_ops = ops()
    current_policy = policy()

    if len(entries) != current_policy["selected_count"]:
        return False

    buckets = [entry["season_bucket"] for entry in entries]
    if sorted(buckets) != sorted(current_policy["season_bucket_order"]):
        return False

    if any(entry["gregorian_date"] in current_ops["blackout_dates"] for entry in entries):
        return False

    if any(entry["weekday"] in current_ops["disallowed_weekdays"] for entry in entries):
        return False

    weekend_count = sum(entry["weekday"] in WEEKEND_NAMES for entry in entries)
    if weekend_count != current_ops["exact_weekend_count"]:
        return False

    friday_count = sum(entry["weekday"] == "Friday" for entry in entries)
    if friday_count != current_ops["exact_friday_count"]:
        return False

    sorted_entries = sorted(entries, key=lambda item: item["gregorian_date"])
    for left, right in zip(sorted_entries, sorted_entries[1:]):
        left_dt = datetime.strptime(left["gregorian_date"], "%Y-%m-%d")
        right_dt = datetime.strptime(right["gregorian_date"], "%Y-%m-%d")
        if (right_dt - left_dt).days < int(current_ops["minimum_gap_days"]):
            return False

    for bucket_name, requirements in current_policy["bucket_requirements"].items():
        matches = [entry for entry in entries if entry["season_bucket"] == bucket_name]
        if len(matches) != 1:
            return False
        entry = matches[0]
        if "required_program_kind" in requirements and entry["program_kind"] != requirements["required_program_kind"]:
            return False
        if "required_audience_tag" in requirements and entry["audience_tag"] != requirements["required_audience_tag"]:
            return False

    return True


def expected_selection() -> list[dict]:
    resolved = list(resolve_candidates().values())
    valid = []
    for combo in itertools.combinations(resolved, policy()["selected_count"]):
        if valid_combo(combo):
            valid.append(sorted(combo, key=lambda item: item["gregorian_date"]))
    assert len(valid) == 1, f"Expected exactly one valid combo, found {len(valid)}"
    return valid[0]


def access_records() -> list[dict]:
    if not ACCESS_LOG.exists():
        return []
    records = []
    for line in ACCESS_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def evidence_rows() -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    if not EVIDENCE_DIR.exists():
        return rows
    for path in sorted(EVIDENCE_DIR.glob("*.tsv")):
        rows[path.stem] = path.read_text(encoding="utf-8").splitlines()
    return rows
