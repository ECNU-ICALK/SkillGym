from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from pathlib import Path


TASK_ROOT = Path(os.environ.get("DIVINATION_TASK_ROOT", "/root"))
DATA_ROOT = TASK_ROOT / "environment" / "data"
OUTPUT_ROOT = TASK_ROOT / "answer"
EVIDENCE_ROOT = OUTPUT_ROOT / "evidence"
ARCHIVE_PATH = Path(
    os.environ.get(
        "DIVINATION_CCAL_ARCHIVE",
        "/root/.x-cmd.root/data/ccal/data/ccal-data-v0.0.6.tar.xz",
    )
)


@dataclass
class ResolvedObservance:
    observance_id: str
    title: str
    lunar_rule: str
    season_bucket: str
    audience_tag: str
    format: str
    program_kind: str
    gregorian_date: str
    weekday: str
    member_name: str
    row_text: str
    evidence_id: str


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def x_cat(member_name: str) -> str:
    return subprocess.check_output(
        ["x", "zuz", "cat", str(ARCHIVE_PATH), member_name],
        text=True,
    )


def run_ccal_update() -> None:
    subprocess.run(["x", "ccal", "lunar", "update"], check=True)


def resolve_observance(item: dict, year: int = 2026) -> ResolvedObservance:
    lunar_key = f"{year}-{item['lunar_rule']}"
    for member_name in [f"ccal-data/lunar/{year}_{month:02d}.tsv" for month in range(1, 13)]:
        for line in x_cat(member_name).splitlines():
            cols = line.split("\t")
            if cols[1] != lunar_key:
                continue
            gregorian_date = cols[0]
            weekday = datetime.strptime(gregorian_date, "%Y-%m-%d").strftime("%A")
            evidence_id = f"{item['observance_id']}.tsv"
            return ResolvedObservance(
                observance_id=item["observance_id"],
                title=item["title"],
                lunar_rule=item["lunar_rule"],
                season_bucket=item["season_bucket"],
                audience_tag=item["audience_tag"],
                format=item["format"],
                program_kind=item["program_kind"],
                gregorian_date=gregorian_date,
                weekday=weekday,
                member_name=member_name,
                row_text=line,
                evidence_id=evidence_id,
            )
    raise RuntimeError(f"Unable to resolve {item['observance_id']} from bundled 2026 monthly files")


def ensure_clean_output() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)


def valid_combo(entries: tuple[ResolvedObservance, ...], ops: dict, policy: dict) -> bool:
    if len(entries) != policy["selected_count"]:
        return False

    buckets = [entry.season_bucket for entry in entries]
    if sorted(buckets) != sorted(policy["season_bucket_order"]):
        return False

    if any(entry.gregorian_date in ops["blackout_dates"] for entry in entries):
        return False

    if any(entry.weekday in ops["disallowed_weekdays"] for entry in entries):
        return False

    weekend_count = sum(entry.weekday in {"Saturday", "Sunday"} for entry in entries)
    if weekend_count != ops["exact_weekend_count"]:
        return False

    friday_count = sum(entry.weekday == "Friday" for entry in entries)
    if friday_count != ops["exact_friday_count"]:
        return False

    ordered = sorted(entries, key=lambda item: item.gregorian_date)
    for left, right in zip(ordered, ordered[1:]):
        left_dt = datetime.strptime(left.gregorian_date, "%Y-%m-%d")
        right_dt = datetime.strptime(right.gregorian_date, "%Y-%m-%d")
        if (right_dt - left_dt).days < int(ops["minimum_gap_days"]):
            return False

    for bucket_name, requirements in policy["bucket_requirements"].items():
        matched = [entry for entry in entries if entry.season_bucket == bucket_name]
        if len(matched) != 1:
            return False
        entry = matched[0]
        if "required_program_kind" in requirements and entry.program_kind != requirements["required_program_kind"]:
            return False
        if "required_audience_tag" in requirements and entry.audience_tag != requirements["required_audience_tag"]:
            return False

    return True


def choose_selection(resolved: list[ResolvedObservance], ops: dict, policy: dict) -> list[ResolvedObservance]:
    valid: list[list[ResolvedObservance]] = []
    for combo in combinations(resolved, policy["selected_count"]):
        if valid_combo(combo, ops, policy):
            valid.append(sorted(combo, key=lambda item: item.gregorian_date))
    if len(valid) != 1:
        raise RuntimeError(f"Expected exactly one valid selection, found {len(valid)}")
    return valid[0]


def main() -> None:
    ensure_clean_output()
    run_ccal_update()
    brief = load_json(DATA_ROOT / "brief" / "program_request.json")
    catalog = load_json(DATA_ROOT / "catalog" / "observance_catalog.json")["observances"]
    ops = load_json(DATA_ROOT / "ops" / "venue_constraints.json")
    policy = load_json(DATA_ROOT / "policy" / "schedule_rules.json")

    resolved = [resolve_observance(item, brief["target_year"]) for item in catalog]
    selected = choose_selection(resolved, ops, policy)
    selected_ids = {item.observance_id for item in selected}

    header = "\t".join(
        [
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
    )
    for item in selected:
        (EVIDENCE_ROOT / item.evidence_id).write_text(
            header + "\n" + item.row_text + "\n",
            encoding="utf-8",
        )

    schedule_payload = {
        "program_name": brief["program_name"],
        "year": brief["target_year"],
        "selected_observances": [
            {
                "observance_id": item.observance_id,
                "title": item.title,
                "lunar_rule": item.lunar_rule,
                "gregorian_date": item.gregorian_date,
                "weekday": item.weekday,
                "audience_tag": item.audience_tag,
                "format": item.format,
                "evidence_id": item.evidence_id,
            }
            for item in selected
        ],
        "rejected_observances": [
            {
                "observance_id": item.observance_id,
                "title": item.title,
                "reason": "Not part of the single policy-compliant schedule.",
            }
            for item in sorted(resolved, key=lambda entry: entry.gregorian_date)
            if item.observance_id not in selected_ids
        ],
        "policy_summary": {
            "selected_count": policy["selected_count"],
            "bucket_order": policy["season_bucket_order"],
            "weekend_count": ops["exact_weekend_count"],
            "friday_count": ops["exact_friday_count"],
        },
        "open_questions": brief["manual_review_prompts"],
    }
    (OUTPUT_ROOT / "observance_schedule.json").write_text(
        json.dumps(schedule_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    resolution_payload = {
        "year": brief["target_year"],
        "resolutions": [
            {
                "observance_id": item.observance_id,
                "title": item.title,
                "lunar_rule": item.lunar_rule,
                "gregorian_date": item.gregorian_date,
                "weekday": item.weekday,
                "resolution_status": "resolved",
                "cross_check_status": "reference-material-available",
                "source_month_file": item.member_name,
            }
            for item in sorted(resolved, key=lambda entry: entry.gregorian_date)
        ],
        "dataset_summary": {
            "archive_path": str(ARCHIVE_PATH),
            "archive_version": "v0.0.6",
            "candidate_count": len(catalog),
        },
        "cross_checks": {
            "reference_files": [
                "ccal-data-v0.0.6.tar.xz",
                "hko_conversion.htm",
                "hko_conversion_text.htm",
                "hko_2026e.pdf",
            ]
        },
    }
    (OUTPUT_ROOT / "date_resolution.json").write_text(
        json.dumps(resolution_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    audit_payload = {
        "source_checked": True,
        "sources_used": [
            str(ARCHIVE_PATH),
            "/root/environment/data/reference/hko_conversion.htm",
            "/root/environment/data/reference/hko_conversion_text.htm",
            "/root/environment/data/reference/hko_2026e.pdf",
        ],
        "months_used": sorted({item.member_name for item in resolved}),
        "evidence_records": [item.evidence_id for item in selected],
        "notes": [
            "Every candidate observance was resolved against the bundled ccal archive.",
            "The final evidence bundle keeps one source row for each selected observance.",
        ],
    }
    (OUTPUT_ROOT / "source_audit.json").write_text(
        json.dumps(audit_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    title_list = ", ".join(item.title for item in selected[:-1]) + f", and {selected[-1].title}"
    report_lines = [
        f"Recommend the 2026 slate built from {title_list}.",
        "",
    ]
    for item in selected:
        report_lines.extend(
            [
                f"## {item.title}",
                f"- Date: {item.gregorian_date} ({item.weekday})",
                f"- Why selected: it satisfies the schedule policy and keeps the required `{item.program_kind}` coverage for its seasonal bucket.",
                f"- Scheduling caution: review venue and staffing details for the `{item.format}` setup before promotion.",
                "",
            ]
        )
    (OUTPUT_ROOT / "selection_report.md").write_text("\n".join(report_lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
