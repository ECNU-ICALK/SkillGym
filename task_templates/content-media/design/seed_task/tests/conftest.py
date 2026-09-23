from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup


TASK_ROOT = Path("/app")
BRIEF_ROOT = Path(os.environ.get("TASK_BRIEF_ROOT", "/app/power_brief"))
WORKSPACE_ROOT = Path(os.environ.get("TASK_WORKSPACE_ROOT", "/app/workspace"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/app/output"))
BUILD_ENTRYPOINT = WORKSPACE_ROOT / "build_site.py"
CONTRACT_PATH = BRIEF_ROOT / "contracts" / "layout_contract.json"
OUTLINES_PATH = BRIEF_ROOT / "outlines" / "slide_outline.json"
BRAND_TOKENS_PATH = BRIEF_ROOT / "assets" / "brand_tokens.json"
BRAND_MARK_PATH = BRIEF_ROOT / "assets" / "brand_mark.svg"
BASELINE_ROOT = Path(os.environ.get("TASK_BASELINE_ROOT", "/opt/task-baselines"))

COUNTRY_ORDER = ["CAN", "MEX", "USA"]
COUNTRY_NAMES = {"CAN": "Canada", "MEX": "Mexico", "USA": "United States"}
SOURCE_LABELS = ["Other renewables", "Bioenergy", "Solar", "Wind", "Hydropower", "Nuclear", "Oil", "Gas", "Coal"]
CLEAN_SOURCES = ["Other renewables", "Bioenergy", "Solar", "Wind", "Hydropower", "Nuclear"]


def run_site(brief_root: Path = BRIEF_ROOT, output_root: Path = OUTPUT_ROOT) -> subprocess.CompletedProcess[str]:
    output_root.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            "python3",
            str(BUILD_ENTRYPOINT),
            "--brief-root",
            str(brief_root),
            "--output-root",
            str(output_root),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_soup(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def normalize_space(text: str) -> str:
    return " ".join(text.split())


def latest_common_world_bank_year(rows: list[dict], codes: list[str]) -> tuple[int, dict[str, float]]:
    filtered = [row for row in rows if row["countryiso3code"] in codes and row["value"] is not None]
    years = sorted({int(row["date"]) for row in filtered}, reverse=True)
    for year in years:
        sample = {row["countryiso3code"]: float(row["value"]) for row in filtered if int(row["date"]) == year}
        if set(sample) == set(codes):
            return year, sample
    raise AssertionError("missing common World Bank year")


def latest_common_csv_year(rows: list[dict[str, str]], codes: list[str], value_columns: list[str]) -> tuple[int, dict[str, dict[str, float]]]:
    years = sorted({int(row["Year"]) for row in rows if row["Code"] in codes}, reverse=True)
    for year in years:
        sample: dict[str, dict[str, float]] = {}
        for row in rows:
            if row["Code"] not in codes or int(row["Year"]) != year:
                continue
            values: dict[str, float] = {}
            for column in value_columns:
                raw = row.get(column, "")
                if raw in ("", None):
                    continue
                values[column] = float(raw)
            if values:
                sample[row["Code"]] = values
        if set(sample) == set(codes):
            return year, sample
    raise AssertionError("missing common CSV year")


def recent_common_window(rows: list[dict[str, str]], codes: list[str], value_column: str, years_count: int) -> list[tuple[int, dict[str, float]]]:
    samples: list[tuple[int, dict[str, float]]] = []
    years = sorted({int(row["Year"]) for row in rows if row["Code"] in codes})
    for year in years:
        yearly = {
            row["Code"]: float(row[value_column])
            for row in rows
            if row["Code"] in codes and int(row["Year"]) == year and row.get(value_column) not in ("", None)
        }
        if set(yearly) == set(codes):
            samples.append((year, yearly))
    return samples[-years_count:]


def top_source(values: dict[str, float]) -> tuple[str, float]:
    ranked = sorted(((source, values.get(source, 0.0)) for source in SOURCE_LABELS), key=lambda item: item[1], reverse=True)
    return ranked[0]


def clean_total(values: dict[str, float]) -> float:
    return sum(values.get(source, 0.0) for source in CLEAN_SOURCES)


def fmt_millions(value: float) -> str:
    return f"{value / 1_000_000:.1f}"


def fmt_trillions(value: float) -> str:
    return f"{value / 1_000_000_000_000:.2f}"


def fmt_megatonnes(value: float) -> str:
    return f"{value / 1_000_000:.1f}"


def current_hash_lines(root: Path) -> str:
    if not root.exists():
        return ""
    return subprocess.check_output(
        f"cd {root} && find . -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )


def page_ids_from_soup(soup: BeautifulSoup) -> list[str]:
    return [node.get("data-page-id") for node in soup.select("[data-page-id]")]


def page_by_id(soup: BeautifulSoup, page_id: str):
    return soup.select_one(f'[data-page-id="{page_id}"]')


def expected_context(brief_root: Path = BRIEF_ROOT) -> dict:
    contract = load_json(brief_root / "contracts" / "layout_contract.json")
    outlines = load_json(brief_root / "outlines" / "slide_outline.json")
    profiles = {row["id"]: row for row in load_json(brief_root / "data" / "country_profile.json")[1]}
    pop_year, pop_values = latest_common_world_bank_year(load_json(brief_root / "data" / "world_bank_population.json")[1], COUNTRY_ORDER)
    gdp_year, gdp_values = latest_common_world_bank_year(load_json(brief_root / "data" / "world_bank_gdp.json")[1], COUNTRY_ORDER)
    co2_rows = load_csv_rows(brief_root / "data" / "annual_co2_emissions.csv")
    co2_column = "Annual CO₂ emissions" if "Annual CO₂ emissions" in co2_rows[0] else "Annual CO2 emissions"
    co2_year, co2_values = latest_common_csv_year(co2_rows, COUNTRY_ORDER, [co2_column])
    co2_latest = {code: values[co2_column] for code, values in co2_values.items()}
    electricity_rows = load_csv_rows(brief_root / "data" / "electricity_prod_source.csv")
    electricity_year, electricity_values = latest_common_csv_year(electricity_rows, COUNTRY_ORDER, SOURCE_LABELS)
    trend = recent_common_window(co2_rows, COUNTRY_ORDER, co2_column, contract["metrics_policy"]["recent_co2_window_years"])

    snapshot_rows = []
    appendix_rows = []
    for code in COUNTRY_ORDER:
        source_name, source_value = top_source(electricity_values[code])
        profile = profiles[code]
        snapshot_rows.append({
            "country": COUNTRY_NAMES[code],
            "population_m": fmt_millions(pop_values[code]),
            "gdp_t": fmt_trillions(gdp_values[code]),
            "co2_mt": fmt_megatonnes(co2_latest[code]),
            "top_source": source_name,
            "top_source_twh": f"{source_value:.1f}",
        })
        appendix_rows.append({
            "country": COUNTRY_NAMES[code],
            "capital": profile["capitalCity"],
            "income": profile["incomeLevel"]["value"],
            "region": profile["region"]["value"].strip(),
        })

    highest_gdp_code = max(gdp_values, key=gdp_values.get)
    lowest_co2_code = min(co2_latest, key=co2_latest.get)
    clean_leader_code = max(electricity_values, key=lambda code: clean_total(electricity_values[code]))

    implications = [
        {
            "title": "GDP scale",
            "country": COUNTRY_NAMES[highest_gdp_code],
            "metric": fmt_trillions(gdp_values[highest_gdp_code]),
            "body": f"{COUNTRY_NAMES[highest_gdp_code]} had the largest GDP in {gdp_year} at ${fmt_trillions(gdp_values[highest_gdp_code])}T."
        },
        {
            "title": "Lowest latest annual CO2 total",
            "country": COUNTRY_NAMES[lowest_co2_code],
            "metric": fmt_megatonnes(co2_latest[lowest_co2_code]),
            "body": f"{COUNTRY_NAMES[lowest_co2_code]} posted the lowest annual CO2 total in {co2_year} at {fmt_megatonnes(co2_latest[lowest_co2_code])} Mt."
        },
        {
            "title": "Latest clean-generation lead",
            "country": COUNTRY_NAMES[clean_leader_code],
            "metric": f"{clean_total(electricity_values[clean_leader_code]):.1f}",
            "body": f"{COUNTRY_NAMES[clean_leader_code]} led the latest clean-power stack in {electricity_year} with {clean_total(electricity_values[clean_leader_code]):.1f} TWh across renewables and nuclear."
        },
    ]

    return {
        "contract": contract,
        "outlines": outlines,
        "population_year": pop_year,
        "gdp_year": gdp_year,
        "co2_year": co2_year,
        "electricity_year": electricity_year,
        "snapshot_rows": snapshot_rows,
        "appendix_rows": appendix_rows,
        "electricity_values": electricity_values,
        "co2_latest": co2_latest,
        "co2_trend": trend,
        "implications": implications,
    }


def make_alternate_brief_copy() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmpdir = tempfile.TemporaryDirectory()
    alt_root = Path(tmpdir.name) / "power_brief"
    shutil.copytree(BRIEF_ROOT, alt_root)

    gdp_payload = load_json(alt_root / "data" / "world_bank_gdp.json")
    for row in gdp_payload[1]:
        if row["date"] == "2024" and row["countryiso3code"] == "USA" and row["value"] is not None:
            row["value"] = row["value"] * 0.50
        if row["date"] == "2024" and row["countryiso3code"] == "CAN" and row["value"] is not None:
            row["value"] = row["value"] * 1.80
    (alt_root / "data" / "world_bank_gdp.json").write_text(json.dumps(gdp_payload), encoding="utf-8")

    electricity_rows = load_csv_rows(alt_root / "data" / "electricity_prod_source.csv")
    for row in electricity_rows:
        if row["Code"] == "USA" and row["Year"] == "2025":
            row["Gas"] = "110.00"
            row["Solar"] = "1900.00"
        if row["Code"] == "CAN" and row["Year"] == "2025":
            row["Hydropower"] = "90.00"
            row["Wind"] = "420.00"
    with (alt_root / "data" / "electricity_prod_source.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=electricity_rows[0].keys())
        writer.writeheader()
        writer.writerows(electricity_rows)

    co2_rows = load_csv_rows(alt_root / "data" / "annual_co2_emissions.csv")
    co2_column = "Annual CO₂ emissions" if "Annual CO₂ emissions" in co2_rows[0] else "Annual CO2 emissions"
    for row in co2_rows:
        if row["Code"] == "MEX" and row["Year"] == "2024":
            row[co2_column] = "210000000.0"
    with (alt_root / "data" / "annual_co2_emissions.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=co2_rows[0].keys())
        writer.writeheader()
        writer.writerows(co2_rows)

    return tmpdir, alt_root
