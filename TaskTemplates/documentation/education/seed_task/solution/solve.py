from __future__ import annotations

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
NOTEBOOK_PATH = OUTPUT_DIR / "global_education_tutorial.ipynb"


def build_notebook() -> nbformat.NotebookNode:
    cells = [
        new_markdown_cell(
            """# Global Education Cohort Workshop

This tutorial notebook shows how to rebuild one compact lesson packet into a rerunnable teaching workflow.

Audience: early-career education policy analysts  
Use this notebook from top to bottom to regenerate the exported cohort table and lesson summary.
"""
        ),
        new_markdown_cell(
            """## Prerequisites And Learning Goals

Prerequisites:
- Read CSV files and basic charts.
- Follow a pandas workflow from loading to export.

Learning goals:
- Harmonize three indicator extracts into one long-format cohort table.
- Identify the latest common comparison year.
- Turn aligned evidence into charts, takeaways, and reusable teaching outputs.
"""
        ),
        new_markdown_cell(
            """## Outline

1. Load the lesson packet and confirm the included cohort.
2. Standardize the three indicator extracts.
3. Align the cohort to one latest common year.
4. Build the required charts and short interpretations.
5. Leave an exercise scaffold, then export the CSV and JSON outputs.
"""
        ),
        new_code_cell(
            """import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

SOURCE_BUNDLE = Path(os.environ.get("SOURCE_BUNDLE_DIR", "/root/workspace/source_bundle"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2018, 2023))
REQUIRED_INDICATORS = [
    "mean_years_schooling",
    "gross_upper_secondary_enrolment_pct",
    "education_spending_pct_gdp",
]
"""
        ),
        new_markdown_cell(
            """## Step 1: Load The Lesson Packet

Start by reading the three CSV extracts together with the lesson brief, metric notes, chart requirements, and analysis rules.
"""
        ),
        new_code_cell(
            """lesson_brief = (SOURCE_BUNDLE / "lesson_brief.md").read_text(encoding="utf-8")
metric_notes = (SOURCE_BUNDLE / "metric_notes.md").read_text(encoding="utf-8")
analysis_rules = (SOURCE_BUNDLE / "analysis_rules.md").read_text(encoding="utf-8")
chart_requirements = json.loads((SOURCE_BUNDLE / "chart_requirements.json").read_text(encoding="utf-8"))

cohort_raw = pd.read_csv(SOURCE_BUNDLE / "country_cohort.csv")
years_raw = pd.read_csv(SOURCE_BUNDLE / "years_of_schooling.csv")
enrolment_raw = pd.read_csv(SOURCE_BUNDLE / "school_enrolment.csv")
spending_raw = pd.read_csv(SOURCE_BUNDLE / "education_spending.csv")

print("Chart topics:", [item["chart_id"] for item in chart_requirements["required_chart_topics"]])
print("Analysis rules preview:", analysis_rules.splitlines()[:4])
print("Lesson brief preview:", lesson_brief.splitlines()[:4])
"""
        ),
        new_markdown_cell(
            """## Step 2: Confirm The Included Cohort

Only rows with `include_in_lesson = yes` belong in the final lesson outputs.
"""
        ),
        new_code_cell(
            """cohort_included = cohort_raw.loc[
    cohort_raw["include_in_lesson"].str.lower().eq("yes"),
    ["entity", "code", "entity_type", "region_group", "peer_group"],
].copy()

print("Included entities:", cohort_included["entity"].tolist())
cohort_included
"""
        ),
        new_markdown_cell(
            """## Step 3: Standardize Mean Years Of Schooling

The schooling extract uses `entity_name` and `iso3_code`, so we rename those fields into the shared schema first.
"""
        ),
        new_code_cell(
            """schooling = years_raw.rename(columns={"entity_name": "entity", "iso3_code": "code"}).copy()
schooling = schooling[schooling["code"].isin(cohort_included["code"])]
schooling = schooling[schooling["year"].between(2018, 2022)].copy()
schooling["indicator"] = "mean_years_schooling"
schooling["value"] = schooling["mean_years_schooling"].astype(float).round(2)
schooling["unit"] = "years"
schooling["entity_type"] = schooling["entity"].map(cohort_included.set_index("entity")["entity_type"])
schooling = schooling[["entity", "entity_type", "indicator", "year", "value", "unit"]]
schooling.head()
"""
        ),
        new_markdown_cell(
            """## Step 4: Standardize Gross Upper-Secondary Enrolment

This extract already uses `entity`, `code`, and `year`, so the main work is filtering the cohort and assigning the canonical indicator label.
"""
        ),
        new_code_cell(
            """enrolment = enrolment_raw[enrolment_raw["code"].isin(cohort_included["code"])].copy()
enrolment = enrolment[enrolment["year"].between(2018, 2022)].copy()
enrolment["indicator"] = "gross_upper_secondary_enrolment_pct"
enrolment["value"] = enrolment["gross_upper_secondary_enrolment_pct"].astype(float).round(2)
enrolment["unit"] = "percent"
enrolment["entity_type"] = enrolment["entity"].map(cohort_included.set_index("entity")["entity_type"])
enrolment = enrolment[["entity", "entity_type", "indicator", "year", "value", "unit"]]
enrolment.head()
"""
        ),
        new_markdown_cell(
            """## Step 5: Standardize Education Spending And Combine

The spending extract uses `country_name`, `country_code`, and `fiscal_year`, so we rename those fields before concatenating all three indicators.
"""
        ),
        new_code_cell(
            """spending = spending_raw.rename(
    columns={"country_name": "entity", "country_code": "code", "fiscal_year": "year"}
).copy()
spending = spending[spending["code"].isin(cohort_included["code"])]
spending = spending[spending["year"].between(2018, 2022)].copy()
spending["indicator"] = "education_spending_pct_gdp"
spending["value"] = spending["education_spending_pct_gdp"].astype(float).round(2)
spending["unit"] = "percent of GDP"
spending["entity_type"] = spending["entity"].map(cohort_included.set_index("entity")["entity_type"])
spending = spending[["entity", "entity_type", "indicator", "year", "value", "unit"]]

cohort_table = pd.concat([schooling, enrolment, spending], ignore_index=True)
cohort_table = cohort_table.sort_values(["entity", "indicator", "year"]).reset_index(drop=True)
print("Rows in cohort table:", len(cohort_table))
cohort_table.head(12)
"""
        ),
        new_markdown_cell(
            """## Step 6: Align The Latest Common Year

Same-year comparisons must use the maximum year shared by every included entity across all three indicators.
"""
        ),
        new_code_cell(
            """years_by_key = {}
for row in cohort_table.itertuples(index=False):
    years_by_key.setdefault((row.entity, row.indicator), set()).add(int(row.year))

common_years = set(YEARS)
for entity in cohort_included["entity"]:
    for indicator in REQUIRED_INDICATORS:
        common_years &= years_by_key[(entity, indicator)]

latest_common_year = max(common_years)
latest_view = cohort_table[cohort_table["year"] == latest_common_year].copy()
print("Common years:", sorted(common_years))
print("latest_common_year =", latest_common_year)
latest_view.pivot(index="entity", columns="indicator", values="value").round(2)
"""
        ),
        new_markdown_cell(
            """## Chart 1: Schooling Trend In 2018-2022

This chart covers the required trend topic for `mean_years_schooling`.
"""
        ),
        new_code_cell(
            """schooling_trend = cohort_table[cohort_table["indicator"] == "mean_years_schooling"].copy()
pivot_schooling = schooling_trend.pivot(index="year", columns="entity", values="value").sort_index()
ax = pivot_schooling.plot(marker="o", figsize=(10, 5), title="Mean years of schooling, 2018-2022")
ax.set_ylabel("Years")
ax.set_xlabel("Year")
ax.legend(title="Entity", bbox_to_anchor=(1.02, 1), loc="upper left")
plt.tight_layout()
plt.show()
"""
        ),
        new_code_cell(
            """schooling_change = (pivot_schooling.loc[2022] - pivot_schooling.loc[2018]).sort_values(ascending=False)
print(
    f"Interpretation: {schooling_change.index[0]} posts the largest 2018-2022 gain "
    f"at {schooling_change.iloc[0]:.2f} years."
)
"""
        ),
        new_markdown_cell(
            """## Chart 2: Latest-Year Enrolment Comparison

This chart covers the required latest-common-year comparison for `gross_upper_secondary_enrolment_pct`.
"""
        ),
        new_code_cell(
            """latest_enrolment = latest_view[latest_view["indicator"] == "gross_upper_secondary_enrolment_pct"]
latest_enrolment = latest_enrolment.sort_values("value", ascending=False)
ax = latest_enrolment.plot(
    kind="bar",
    x="entity",
    y="value",
    figsize=(10, 5),
    color="#2c7fb8",
    legend=False,
    title=f"Gross upper-secondary enrolment in {latest_common_year}",
)
ax.set_ylabel("Percent")
ax.set_xlabel("Entity")
plt.xticks(rotation=25, ha="right")
plt.tight_layout()
plt.show()
"""
        ),
        new_code_cell(
            """highest_enrolment = latest_enrolment.iloc[0]
lowest_enrolment = latest_enrolment.iloc[-1]
print(
    f"Interpretation: {highest_enrolment['entity']} leads the latest-year enrolment "
    f"comparison at {highest_enrolment['value']:.2f}, while {lowest_enrolment['entity']} "
    f"is lowest at {lowest_enrolment['value']:.2f}."
)
"""
        ),
        new_markdown_cell(
            """## Chart 3: Spending Versus Enrolment

This chart compares `education_spending_pct_gdp` and `gross_upper_secondary_enrolment_pct` in the same latest common year.
"""
        ),
        new_code_cell(
            """spending_latest = latest_view[latest_view["indicator"] == "education_spending_pct_gdp"][["entity", "value"]]
enrolment_latest = latest_view[latest_view["indicator"] == "gross_upper_secondary_enrolment_pct"][["entity", "value"]]
scatter = spending_latest.rename(columns={"value": "spending"}).merge(
    enrolment_latest.rename(columns={"value": "enrolment"}), on="entity", how="inner"
)

fig, ax = plt.subplots(figsize=(8, 6))
ax.scatter(scatter["spending"], scatter["enrolment"], s=80, color="#d95f0e")
for row in scatter.itertuples(index=False):
    ax.annotate(row.entity, (row.spending, row.enrolment), textcoords="offset points", xytext=(5, 5))
ax.set_title(f"Education spending vs upper-secondary enrolment in {latest_common_year}")
ax.set_xlabel("Education spending (% of GDP)")
ax.set_ylabel("Gross upper-secondary enrolment (%)")
plt.tight_layout()
plt.show()
"""
        ),
        new_code_cell(
            """highest_spending = scatter.sort_values("spending", ascending=False).iloc[0]
highest_enrolment_scatter = scatter.sort_values("enrolment", ascending=False).iloc[0]
print(
    f"Interpretation: {highest_spending['entity']} has the highest spending share, "
    f"but {highest_enrolment_scatter['entity']} has the highest enrolment ratio."
)
"""
        ),
        new_markdown_cell(
            """## Exercise

Try one extra same-year comparison of your own. A simple starting point is to rank the cohort on one indicator and describe the gap between two neighboring entities.
"""
        ),
        new_code_cell(
            """# TODO: replace this sample scaffold with your own classroom prompt.
practice_indicator = "mean_years_schooling"
practice_table = latest_view[latest_view["indicator"] == practice_indicator].sort_values("value", ascending=False)
print("Starter scaffold:")
practice_table[["entity", "value"]]
"""
        ),
        new_markdown_cell(
            """## Pitfalls And Extensions

Pitfall:
- Gross enrolment can exceed 100, so values above 100 are not automatically errors.

Extension:
- Reuse the same harmonization pattern on a different cohort, but check the shared year set again before making same-year claims.
"""
        ),
        new_markdown_cell(
            """## Wrap-Up

The final two cells export the long-format cohort table and a concise lesson summary so the same evidence can be reused outside the notebook.
"""
        ),
        new_code_cell(
            """cohort_csv_path = OUTPUT_DIR / "cohort_indicator_table.csv"
cohort_table.to_csv(cohort_csv_path, index=False)

def evidence_row(entity: str, indicator: str, year: int) -> dict[str, object]:
    row = cohort_table[
        (cohort_table["entity"] == entity)
        & (cohort_table["indicator"] == indicator)
        & (cohort_table["year"] == year)
    ].iloc[0]
    return {
        "entity": row["entity"],
        "indicator": row["indicator"],
        "year": int(row["year"]),
        "value": round(float(row["value"]), 2),
    }

print(f"Wrote {cohort_csv_path}")
cohort_table.head(10)
"""
        ),
        new_code_cell(
            """takeaways = [
    {
        "rank": 1,
        "title": "Attainment depth is highest in Germany and the United States within the latest-year cohort view.",
        "detail": "The same-year comparison shows Germany and the United States at the top of mean years of schooling, while Indonesia and Thailand remain lower in the 2022 distribution.",
        "evidence": [
            evidence_row("Germany", "mean_years_schooling", latest_common_year),
            evidence_row("United States", "mean_years_schooling", latest_common_year),
            evidence_row("Thailand", "mean_years_schooling", latest_common_year),
            evidence_row("Indonesia", "mean_years_schooling", latest_common_year),
        ],
    },
    {
        "rank": 2,
        "title": "Uruguay leads the latest-year enrolment comparison, and several cohort members exceed 100.",
        "detail": "Gross upper-secondary enrolment is highest in Uruguay in 2022, with South Africa and Germany also above 100 under the gross-ratio definition.",
        "evidence": [
            evidence_row("Uruguay", "gross_upper_secondary_enrolment_pct", latest_common_year),
            evidence_row("South Africa", "gross_upper_secondary_enrolment_pct", latest_common_year),
            evidence_row("Germany", "gross_upper_secondary_enrolment_pct", latest_common_year),
            evidence_row("Thailand", "gross_upper_secondary_enrolment_pct", latest_common_year),
        ],
    },
    {
        "rank": 3,
        "title": "Higher spending effort does not map one-to-one onto latest-year enrolment outcomes.",
        "detail": "South Africa has the highest education spending share of GDP in the latest common year, yet Uruguay records the highest gross upper-secondary enrolment ratio.",
        "evidence": [
            evidence_row("South Africa", "education_spending_pct_gdp", latest_common_year),
            evidence_row("South Africa", "gross_upper_secondary_enrolment_pct", latest_common_year),
            evidence_row("Uruguay", "education_spending_pct_gdp", latest_common_year),
            evidence_row("Uruguay", "gross_upper_secondary_enrolment_pct", latest_common_year),
        ],
    },
]

takeaways
"""
        ),
        new_code_cell(
            """lesson_summary = {
    "lesson_topic": "Comparing a global education cohort across attainment, enrolment, and spending",
    "target_audience": "Early-career education policy analysts practicing descriptive indicator analysis",
    "latest_common_year": int(latest_common_year),
    "entities_covered": sorted(cohort_table["entity"].unique().tolist()),
    "takeaways": takeaways,
    "caveats": [
        "Same-year comparisons use 2022, the latest common year shared by every included entity across all three indicators.",
        "Gross enrolment can exceed 100, so cross-sectional comparisons should respect the ratio definition.",
        "The lesson remains descriptive and stays inside the 2018-2022 window and the included cohort only.",
    ],
}

summary_path = OUTPUT_DIR / "lesson_summary.json"
summary_path.write_text(json.dumps(lesson_summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote {summary_path}")
lesson_summary
"""
        ),
    ]
    return new_notebook(cells=cells)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    notebook = build_notebook()
    with NOTEBOOK_PATH.open("w", encoding="utf-8") as fh:
        nbformat.write(notebook, fh)

    client = NotebookClient(notebook, timeout=300, kernel_name="python3")
    executed = client.execute(cwd=str(OUTPUT_DIR))
    with NOTEBOOK_PATH.open("w", encoding="utf-8") as fh:
        nbformat.write(executed, fh)


if __name__ == "__main__":
    main()
