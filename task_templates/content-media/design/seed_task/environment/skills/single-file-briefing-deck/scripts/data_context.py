#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path


POWER_BRIEF_ROOT = Path("/app/power_brief")
COUNTRY_ORDER = ["CAN", "MEX", "USA"]
COUNTRY_NAMES = {"CAN": "Canada", "MEX": "Mexico", "USA": "United States"}
SOURCE_LABELS = ["Other renewables", "Bioenergy", "Solar", "Wind", "Hydropower", "Nuclear", "Oil", "Gas", "Coal"]
CLEAN_SOURCES = ["Other renewables", "Bioenergy", "Solar", "Wind", "Hydropower", "Nuclear"]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def latest_common_world_bank_year(rows: list[dict], codes: list[str]) -> tuple[int, dict[str, float]]:
    filtered = [row for row in rows if row["countryiso3code"] in codes and row["value"] is not None]
    years = sorted({int(row["date"]) for row in filtered}, reverse=True)
    for year in years:
        sample = {row["countryiso3code"]: float(row["value"]) for row in filtered if int(row["date"]) == year}
        if set(sample) == set(codes):
            return year, sample
    raise ValueError("missing common World Bank year")


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
    raise ValueError("missing common CSV year")


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


def main() -> int:
    contract = load_json(POWER_BRIEF_ROOT / "contracts" / "layout_contract.json")
    profiles = {row["id"]: row for row in load_json(POWER_BRIEF_ROOT / "data" / "country_profile.json")[1]}
    pop_year, pop_values = latest_common_world_bank_year(load_json(POWER_BRIEF_ROOT / "data" / "world_bank_population.json")[1], COUNTRY_ORDER)
    gdp_year, gdp_values = latest_common_world_bank_year(load_json(POWER_BRIEF_ROOT / "data" / "world_bank_gdp.json")[1], COUNTRY_ORDER)
    co2_rows = load_csv_rows(POWER_BRIEF_ROOT / "data" / "annual_co2_emissions.csv")
    co2_column = "Annual CO₂ emissions" if "Annual CO₂ emissions" in co2_rows[0] else "Annual CO2 emissions"
    co2_year, co2_values = latest_common_csv_year(co2_rows, COUNTRY_ORDER, [co2_column])
    electricity_rows = load_csv_rows(POWER_BRIEF_ROOT / "data" / "electricity_prod_source.csv")
    electricity_year, electricity_values = latest_common_csv_year(electricity_rows, COUNTRY_ORDER, SOURCE_LABELS)
    trend = recent_common_window(co2_rows, COUNTRY_ORDER, co2_column, contract["metrics_policy"]["recent_co2_window_years"])

    snapshot_rows = []
    for code in COUNTRY_ORDER:
        source_name, source_value = top_source(electricity_values[code])
        snapshot_rows.append({
            "country": COUNTRY_NAMES[code],
            "population_m": fmt_millions(pop_values[code]),
            "gdp_t": fmt_trillions(gdp_values[code]),
            "co2_mt": fmt_megatonnes(co2_values[code][co2_column]),
            "top_source": source_name,
            "top_source_twh": f"{source_value:.1f}",
            "capital": profiles[code]["capitalCity"],
            "income": profiles[code]["incomeLevel"]["value"],
            "region": profiles[code]["region"]["value"].strip(),
            "clean_total_twh": f"{clean_total(electricity_values[code]):.1f}",
        })

    context = {
        "metric_years": {
            "population_year": pop_year,
            "gdp_year": gdp_year,
            "co2_year": co2_year,
            "electricity_year": electricity_year,
        },
        "snapshot_rows": snapshot_rows,
        "co2_window": [{"year": year, **{COUNTRY_NAMES[code]: values[code] for code in COUNTRY_ORDER}} for year, values in trend],
    }
    print(json.dumps(context, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
