from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


APP_ROOT = Path(os.environ.get("TASK_APP_ROOT", "/app"))
DATA_ROOT = APP_ROOT / "data" / "ourairports"
OUTPUT_ROOT = APP_ROOT / "output"
SCRIPT_PATH = APP_ROOT / "bin" / "rebuild_airport_reports.sh"
ALT_FIXTURE_ROOT = Path(os.environ.get("TASK_ALT_FIXTURE_ROOT", "/tests/fixtures/alternate_data"))


def parse_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def stable_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_expected_outputs(data_root: Path) -> tuple[list[list[object]], dict[str, object]]:
    countries = parse_tsv(data_root / "countries.tsv")
    regions = parse_tsv(data_root / "regions.tsv")
    airports = parse_tsv(data_root / "airports.tsv")
    runways = parse_tsv(data_root / "runways.tsv")

    countries_by_code = {row["country_code"]: row for row in countries}
    regions_by_code = {row["region_code"]: row for row in regions}

    open_airports = [row for row in airports if row["airport_type"] != "closed"]
    runway_stats: dict[str, dict[str, object]] = {}
    for airport in open_airports:
        runway_stats[airport["airport_ident"]] = {"runway_count": 0, "longest_runway_ft": ""}

    seen_runways: set[tuple[str, str, str, str, str]] = set()
    for runway in runways:
        if runway["closed"] == "1":
            continue
        dedupe_key = (
            runway["airport_ident"],
            runway["length_ft"],
            runway["surface"],
            runway["lighted"],
            runway["closed"],
        )
        if dedupe_key in seen_runways:
            continue
        seen_runways.add(dedupe_key)
        stats = runway_stats.setdefault(runway["airport_ident"], {"runway_count": 0, "longest_runway_ft": ""})
        stats["runway_count"] = int(stats["runway_count"]) + 1
        length_text = runway["length_ft"].strip()
        if length_text:
            length_value = int(length_text)
            if stats["longest_runway_ft"] == "" or length_value > int(stats["longest_runway_ft"]):
                stats["longest_runway_ft"] = length_value

    country_rows: list[list[object]] = [[
        "country_code",
        "country_name",
        "airport_count",
        "open_airport_count",
        "scheduled_open_airport_count",
        "runway_count",
        "longest_runway_ft",
    ]]
    for country in sorted(countries, key=lambda row: row["country_code"]):
        country_airports = [row for row in airports if row["country_code"] == country["country_code"]]
        open_country_airports = [row for row in country_airports if row["airport_type"] != "closed"]
        scheduled_open = [row for row in open_country_airports if row["scheduled_service"] == "yes"]
        longest: object = ""
        runway_count = 0
        for airport in open_country_airports:
            stats = runway_stats.get(airport["airport_ident"], {"runway_count": 0, "longest_runway_ft": ""})
            runway_count += int(stats["runway_count"])
            candidate = stats["longest_runway_ft"]
            if candidate != "" and (longest == "" or int(candidate) > int(longest)):
                longest = int(candidate)
        country_rows.append([
            country["country_code"],
            country["country_name"],
            len(country_airports),
            len(open_country_airports),
            len(scheduled_open),
            runway_count,
            longest,
        ])

    grouped_regions: dict[str, dict[str, object]] = {}
    for airport in open_airports:
        region = regions_by_code[airport["region_code"]]
        country = countries_by_code[airport["country_code"]]
        stats = runway_stats.get(airport["airport_ident"], {"runway_count": 0, "longest_runway_ft": ""})
        bucket = grouped_regions.setdefault(
            airport["region_code"],
            {
                "region_code": region["region_code"],
                "region_name": region["region_name"],
                "country_code": country["country_code"],
                "country_name": country["country_name"],
                "open_airport_count": 0,
                "scheduled_open_airport_count": 0,
                "runway_count": 0,
                "longest_runway_ft": "",
            },
        )
        bucket["open_airport_count"] = int(bucket["open_airport_count"]) + 1
        bucket["scheduled_open_airport_count"] = int(bucket["scheduled_open_airport_count"]) + (1 if airport["scheduled_service"] == "yes" else 0)
        bucket["runway_count"] = int(bucket["runway_count"]) + int(stats["runway_count"])
        candidate = stats["longest_runway_ft"]
        if candidate != "" and (bucket["longest_runway_ft"] == "" or int(candidate) > int(bucket["longest_runway_ft"])):
            bucket["longest_runway_ft"] = int(candidate)

    ordered_regions = sorted(
        grouped_regions.values(),
        key=lambda row: (-int(row["scheduled_open_airport_count"]), -int(row["open_airport_count"]), row["region_code"]),
    )
    return country_rows, {"generated_from": "ourairports", "regions": ordered_regions}


def run_pipeline(
    app_root: Path,
    *,
    data_root: Path | None = None,
    output_root: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    }
    if data_root is not None:
        env["AIRPORTS_DATA_DIR"] = str(data_root)
    if output_root is not None:
        env["AIRPORTS_OUTPUT_DIR"] = str(output_root)
    if extra_env is not None:
        env.update(extra_env)
    return subprocess.run(
        [str(app_root / "bin" / "rebuild_airport_reports.sh")],
        cwd=str(app_root),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def load_country_csv(path: Path) -> list[list[object]]:
    rows: list[list[object]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for index, row in enumerate(reader):
            if index == 0:
                rows.append(row)
                continue
            converted: list[object] = []
            for cell in row:
                if cell == "":
                    converted.append("")
                elif cell.isdigit():
                    converted.append(int(cell))
                else:
                    converted.append(cell)
            rows.append(converted)
    return rows


def load_region_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_workspace_copy(source_app_root: Path, fixture_root: Path | None = None) -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="airport reports fixture "))
    target_root = temp_root / "app copy"
    shutil.copytree(source_app_root, target_root)
    if fixture_root is not None:
        shutil.rmtree(target_root / "data" / "ourairports")
        shutil.copytree(fixture_root, target_root / "data" / "ourairports")
    return target_root
