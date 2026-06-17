from __future__ import annotations

import csv
import json
import os
from pathlib import Path


SOURCE_BUNDLE = Path(os.environ.get("SOURCE_BUNDLE_DIR", "/root/workspace/source_bundle"))
YEARS = list(range(2018, 2023))
INDICATOR_ORDER = [
    "education_spending_pct_gdp",
    "gross_upper_secondary_enrolment_pct",
    "mean_years_schooling",
]
UNITS = {
    "mean_years_schooling": "years",
    "gross_upper_secondary_enrolment_pct": "percent",
    "education_spending_pct_gdp": "percent of GDP",
}


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def included_cohort() -> list[dict[str, str]]:
    rows = read_csv_rows(SOURCE_BUNDLE / "country_cohort.csv")
    included = [row for row in rows if row["include_in_lesson"].strip().lower() == "yes"]
    return sorted(included, key=lambda row: row["entity"])


def target_entities() -> list[str]:
    return [row["entity"] for row in included_cohort()]


def target_codes() -> list[str]:
    return [row["code"] for row in included_cohort()]


def lesson_topic() -> str:
    return "Global education cohort workshop"


def target_audience() -> str:
    return "early-career education policy analysts"


def canonical_rows() -> list[dict[str, object]]:
    code_to_entity = {row["code"]: row["entity"] for row in included_cohort()}
    rows: list[dict[str, object]] = []

    for raw in read_csv_rows(SOURCE_BUNDLE / "years_of_schooling.csv"):
        code = raw["iso3_code"]
        if code not in code_to_entity:
            continue
        year = int(raw["year"])
        if year not in YEARS:
            continue
        rows.append(
            {
                "entity": code_to_entity[code],
                "entity_type": "country",
                "indicator": "mean_years_schooling",
                "year": year,
                "value": round2(float(raw["mean_years_schooling"])),
                "unit": UNITS["mean_years_schooling"],
            }
        )

    for raw in read_csv_rows(SOURCE_BUNDLE / "school_enrolment.csv"):
        code = raw["code"]
        if code not in code_to_entity:
            continue
        year = int(raw["year"])
        if year not in YEARS:
            continue
        rows.append(
            {
                "entity": code_to_entity[code],
                "entity_type": "country",
                "indicator": "gross_upper_secondary_enrolment_pct",
                "year": year,
                "value": round2(float(raw["gross_upper_secondary_enrolment_pct"])),
                "unit": UNITS["gross_upper_secondary_enrolment_pct"],
            }
        )

    for raw in read_csv_rows(SOURCE_BUNDLE / "education_spending.csv"):
        code = raw["country_code"]
        if code not in code_to_entity:
            continue
        year = int(raw["fiscal_year"])
        if year not in YEARS:
            continue
        rows.append(
            {
                "entity": code_to_entity[code],
                "entity_type": "country",
                "indicator": "education_spending_pct_gdp",
                "year": year,
                "value": round2(float(raw["education_spending_pct_gdp"])),
                "unit": UNITS["education_spending_pct_gdp"],
            }
        )

    rows.sort(key=lambda row: (row["entity"], row["indicator"], row["year"]))
    return rows


def latest_common_year(rows: list[dict[str, object]] | None = None) -> int:
    rows = rows or canonical_rows()
    years_by_key: dict[tuple[str, str], set[int]] = {}
    for row in rows:
        key = (str(row["entity"]), str(row["indicator"]))
        years_by_key.setdefault(key, set()).add(int(row["year"]))
    common = set(YEARS)
    for entity in target_entities():
        for indicator in INDICATOR_ORDER:
            common &= years_by_key[(entity, indicator)]
    return max(common)


def table_frame(rows: list[dict[str, object]] | None = None) -> list[dict[str, object]]:
    return list(rows or canonical_rows())


def evidence_row(
    rows: list[dict[str, object]],
    *,
    entity: str,
    indicator: str,
    year: int,
) -> dict[str, object]:
    for row in rows:
        if row["entity"] == entity and row["indicator"] == indicator and row["year"] == year:
            return {
                "entity": entity,
                "indicator": indicator,
                "year": year,
                "value": round2(float(row["value"])),
            }
    raise KeyError((entity, indicator, year))


def expected_takeaway_evidence(rows: list[dict[str, object]] | None = None) -> list[list[dict[str, object]]]:
    rows = rows or canonical_rows()
    common_year = latest_common_year(rows)
    return [
        [
            evidence_row(rows, entity="Germany", indicator="mean_years_schooling", year=common_year),
            evidence_row(rows, entity="Indonesia", indicator="mean_years_schooling", year=common_year),
        ],
        [
            evidence_row(rows, entity="Uruguay", indicator="gross_upper_secondary_enrolment_pct", year=common_year),
            evidence_row(rows, entity="Thailand", indicator="gross_upper_secondary_enrolment_pct", year=common_year),
        ],
        [
            evidence_row(rows, entity="South Africa", indicator="education_spending_pct_gdp", year=common_year),
            evidence_row(rows, entity="Indonesia", indicator="education_spending_pct_gdp", year=common_year),
        ],
    ]


def expected_summary(rows: list[dict[str, object]] | None = None) -> dict[str, object]:
    rows = rows or canonical_rows()
    common_year = latest_common_year(rows)
    return {
        "lesson_topic": lesson_topic(),
        "target_audience": target_audience(),
        "latest_common_year": common_year,
        "entities_covered": target_entities(),
        "takeaway_evidence_sets": expected_takeaway_evidence(rows),
        "caveat_markers": [
            "gross enrolment",
            "latest common year",
            "2018-2022",
        ],
    }


def load_chart_requirements() -> dict[str, object]:
    return json.loads((SOURCE_BUNDLE / "chart_requirements.json").read_text(encoding="utf-8"))
