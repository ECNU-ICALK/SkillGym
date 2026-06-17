#!/bin/bash
set -euo pipefail

cat > /app/workspace/build_site.py <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path


COUNTRY_ORDER = ["CAN", "MEX", "USA"]
COUNTRY_NAMES = {"CAN": "Canada", "MEX": "Mexico", "USA": "United States"}
SOURCE_LABELS = ["Other renewables", "Bioenergy", "Solar", "Wind", "Hydropower", "Nuclear", "Oil", "Gas", "Coal"]
CLEAN_SOURCES = ["Other renewables", "Bioenergy", "Solar", "Wind", "Hydropower", "Nuclear"]
SOURCE_COLORS = {
    "Other renewables": "#7fc8a9",
    "Bioenergy": "#9dd39d",
    "Solar": "#f6bd60",
    "Wind": "#84a59d",
    "Hydropower": "#5fa8d3",
    "Nuclear": "#b8c0ff",
    "Oil": "#c08457",
    "Gas": "#4a6fa5",
    "Coal": "#495057",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the North America power mix briefing site.")
    parser.add_argument("--brief-root", default="/app/power_brief")
    parser.add_argument("--output-root", default="/app/output")
    return parser.parse_args()


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


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def build_context(brief_root: Path) -> dict:
    contract = load_json(brief_root / "contracts" / "layout_contract.json")
    outlines = load_json(brief_root / "outlines" / "slide_outline.json")
    tokens = load_json(brief_root / "assets" / "brand_tokens.json")
    brand_mark = (brief_root / "assets" / "brand_mark.svg").read_text(encoding="utf-8")
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
            "code": code,
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
            "body": f"{COUNTRY_NAMES[highest_gdp_code]} had the largest GDP in {gdp_year} at ${fmt_trillions(gdp_values[highest_gdp_code])}T."
        },
        {
            "title": "Lowest latest annual CO2 total",
            "body": f"{COUNTRY_NAMES[lowest_co2_code]} posted the lowest annual CO2 total in {co2_year} at {fmt_megatonnes(co2_latest[lowest_co2_code])} Mt."
        },
        {
            "title": "Latest clean-generation lead",
            "body": f"{COUNTRY_NAMES[clean_leader_code]} led the latest clean-power stack in {electricity_year} with {clean_total(electricity_values[clean_leader_code]):.1f} TWh across renewables and nuclear."
        },
    ]

    return {
        "contract": contract,
        "outlines": outlines,
        "tokens": tokens,
        "brand_mark": brand_mark,
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


def render_mix_chart(context: dict) -> str:
    year = context["electricity_year"]
    values = context["electricity_values"]
    totals = {code: sum(values[code].get(source, 0.0) for source in SOURCE_LABELS) for code in COUNTRY_ORDER}
    max_total = max(totals.values())
    y_positions = {"CAN": 48, "MEX": 120, "USA": 192}
    bar_height = 34
    usable_width = 620
    rows = []
    for code in COUNTRY_ORDER:
        x = 160.0
        rows.append(f'<text x="18" y="{y_positions[code] + 22}" font-size="18" fill="#1d2731">{COUNTRY_NAMES[code]}</text>')
        for source in SOURCE_LABELS:
            value = values[code].get(source, 0.0)
            width = 0.0 if max_total == 0 else usable_width * (value / max_total)
            rows.append(
                f'<rect x="{x:.2f}" y="{y_positions[code]}" width="{width:.2f}" height="{bar_height}" fill="{SOURCE_COLORS[source]}" />'
            )
            x += width
        rows.append(f'<text x="{800}" y="{y_positions[code] + 22}" font-size="16" fill="#1d2731">{totals[code]:.1f} TWh</text>')
    return f'''
    <svg data-chart-id="power-mix-latest-common-year" viewBox="0 0 900 250" role="img" aria-label="Power mix comparison for {year}">
      <text x="18" y="22" font-size="18" fill="#1d2731">Latest common electricity year: {year}</text>
      {"".join(rows)}
    </svg>
    '''


def render_co2_chart(context: dict) -> str:
    trend = context["co2_trend"]
    years = [year for year, _ in trend]
    value_range = [yearly[code] for _, yearly in trend for code in COUNTRY_ORDER]
    min_value = min(value_range)
    max_value = max(value_range)
    span = max(max_value - min_value, 1.0)
    colors = {"CAN": "#0f766e", "MEX": "#8a3b12", "USA": "#4a6fa5"}
    chart_width = 760
    chart_height = 240
    left = 70
    top = 24
    step_x = chart_width / max(len(years) - 1, 1)

    def point(year_index: int, value: float) -> tuple[float, float]:
        x = left + step_x * year_index
        y = top + chart_height - ((value - min_value) / span) * chart_height
        return x, y

    parts = [f'<text x="16" y="18" font-size="18" fill="#1d2731">Recent common CO2 window: {years[0]}-{years[-1]}</text>']
    for i, year in enumerate(years):
        x = left + step_x * i
        parts.append(f'<text x="{x:.1f}" y="{top + chart_height + 24:.1f}" font-size="12" text-anchor="middle" fill="#53616f">{year}</text>')
    for code in COUNTRY_ORDER:
        d = []
        for i, (_, yearly) in enumerate(trend):
            x, y = point(i, yearly[code])
            d.append(f"{'M' if i == 0 else 'L'} {x:.1f} {y:.1f}")
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.8" fill="{colors[code]}" />')
        parts.append(f'<path d="{" ".join(d)}" fill="none" stroke="{colors[code]}" stroke-width="3" />')
    legend_y = top + chart_height + 54
    legend_x = 70
    for code in COUNTRY_ORDER:
        parts.append(f'<rect x="{legend_x}" y="{legend_y}" width="14" height="14" fill="{colors[code]}" />')
        parts.append(f'<text x="{legend_x + 20}" y="{legend_y + 12}" font-size="14" fill="#1d2731">{COUNTRY_NAMES[code]}</text>')
        legend_x += 180
    return f'<svg data-chart-id="co2-recent-window" viewBox="0 0 900 360" role="img" aria-label="Recent CO2 trend window">{"".join(parts)}</svg>'


def render_pages(context: dict) -> str:
    snapshot_rows_html = "".join(
        f"<tr><td>{esc(row['country'])}</td><td>{row['population_m']}</td><td>{row['gdp_t']}</td><td>{row['co2_mt']}</td><td>{esc(row['top_source'])} ({row['top_source_twh']} TWh)</td></tr>"
        for row in context["snapshot_rows"]
    )
    legend_html = "".join(
        f'<li><span class="swatch" style="background:{SOURCE_COLORS[source]}"></span>{esc(source)}</li>'
        for source in SOURCE_LABELS
    )
    appendix_rows_html = "".join(
        f"<tr><td>{esc(row['country'])}</td><td>{esc(row['capital'])}</td><td>{esc(row['income'])}</td><td>{esc(row['region'])}</td></tr>"
        for row in context["appendix_rows"]
    )
    implication_cards = "".join(
        f'<article class="implication-card"><h3>{esc(card["title"])}</h3><p>{esc(card["body"])}</p></article>'
        for card in context["implications"]
    )
    top_sources_line = ", ".join(
        f"{row['country']}: {row['top_source']} ({row['top_source_twh']} TWh)"
        for row in context["snapshot_rows"]
    )
    co2_start = context["co2_trend"][0][0]
    co2_end = context["co2_trend"][-1][0]

    return f"""
      <section class="page is-active" data-page-id="cover">
        <div class="module hero" data-module-id="hero">
          <p class="eyebrow">Internal review briefing</p>
        </div>
        <div class="module title-block" data-module-id="title-block">
          <h1>{esc(context["contract"]["site_title"])}</h1>
          <p class="subtitle">Canada, Mexico, and the United States across common-year population, GDP, power mix, and emissions snapshots.</p>
        </div>
        <div class="module year-chip" data-module-id="year-chip">
          Population/GDP {context["population_year"]}/{context["gdp_year"]} • Electricity {context["electricity_year"]} • CO2 {context["co2_year"]}
        </div>
        <div class="module brand-mark" data-module-id="brand-mark">{context["brand_mark"]}</div>
      </section>

      <section class="page" data-page-id="agenda" hidden>
        <div class="module section-title" data-module-id="section-title"><h2>Agenda</h2></div>
        <div class="module agenda-list" data-module-id="agenda-list">
          <ol>
            <li>Country Snapshot</li>
            <li>Power Mix Comparison</li>
            <li>Emissions Trend</li>
            <li>Implications</li>
            <li>Appendix</li>
          </ol>
        </div>
        <div class="module agenda-context" data-module-id="agenda-context">
          <p>This site uses the latest common-year snapshots across the bundled data files whenever the series supports it.</p>
        </div>
      </section>

      <section class="page" data-page-id="snapshot" hidden>
        <div class="module section-title" data-module-id="section-title"><h2>Country Snapshot</h2></div>
        <div class="module snapshot-table" data-module-id="snapshot-table">
          <table>
            <thead>
              <tr><th>Country</th><th>Population (M)</th><th>GDP ($T)</th><th>CO2 (Mt)</th><th>Top latest source</th></tr>
            </thead>
            <tbody>{snapshot_rows_html}</tbody>
          </table>
        </div>
        <div class="module snapshot-explainer" data-module-id="snapshot-explainer">
          <p>The latest common-year snapshot shows a wide scale gap across the three countries, while the dominant generation source remains different in each market. GDP and emissions do not move in lockstep across the region, which makes the power mix comparison worth reading alongside the country table.</p>
        </div>
      </section>

      <section class="page" data-page-id="power-mix" hidden>
        <div class="module section-title" data-module-id="section-title"><h2>Power Mix Comparison</h2></div>
        <div class="power-grid">
          <div class="module mix-chart" data-module-id="mix-chart">{render_mix_chart(context)}</div>
          <div class="module mix-legend" data-module-id="mix-legend">
            <ul class="legend">{legend_html}</ul>
          </div>
        </div>
        <div class="module mix-explainer" data-module-id="mix-explainer">
          <p>In {context["electricity_year"]}, the latest dominant sources were {esc(top_sources_line)}. The chart shows how the total stack differs even when all three countries are viewed in the same electricity year.</p>
        </div>
      </section>

      <section class="page" data-page-id="emissions" hidden>
        <div class="module section-title" data-module-id="section-title"><h2>Emissions Trend</h2></div>
        <div class="module co2-chart" data-module-id="co2-chart">{render_co2_chart(context)}</div>
        <div class="module co2-explainer" data-module-id="co2-explainer">
          <p>The recent common CO2 window spans {co2_start} to {co2_end}. Reading the three series together shows how the regional emissions picture shifts over time rather than in a single-year snapshot.</p>
        </div>
      </section>

      <section class="page" data-page-id="implications" hidden>
        <div class="module section-title" data-module-id="section-title"><h2>Implications</h2></div>
        <div class="module implication-cards" data-module-id="implication-cards">
          <div class="implication-grid">{implication_cards}</div>
        </div>
        <div class="module source-note-callout" data-module-id="source-note-callout">
          <p>Bundled inputs draw from World Bank country, population, and GDP snapshots together with Our World in Data emissions and electricity generation files.</p>
        </div>
      </section>

      <section class="page" data-page-id="appendix" hidden>
        <div class="module section-title" data-module-id="section-title"><h2>Appendix</h2></div>
        <div class="module appendix-table" data-module-id="appendix-table">
          <table>
            <thead>
              <tr><th>Country</th><th>Capital</th><th>Income level</th><th>Region</th></tr>
            </thead>
            <tbody>{appendix_rows_html}</tbody>
          </table>
        </div>
        <div class="module method-note" data-module-id="method-note">
          <p>Method note: the site uses the latest common available year for each data family, and the emissions chart uses the recent {len(context["co2_trend"])}-year common window shared by all three countries.</p>
        </div>
      </section>
    """


def render_html(context: dict) -> str:
    colors = context["tokens"]["colors"]
    type_tokens = context["tokens"]["type"]
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{esc(context["contract"]["site_title"])}</title>
    <style>
      :root {{
        --bg: {colors["bg"]};
        --panel: {colors["panel"]};
        --ink: {colors["ink"]};
        --muted: {colors["muted"]};
        --accent: {colors["accent"]};
        --accent-soft: {colors["accent_soft"]};
        --line: {colors["line"]};
        --warn: {colors["warn"]};
        --heading-font: {type_tokens["heading"]};
        --body-font: {type_tokens["body"]};
        --mono-font: {type_tokens["mono"]};
      }}
      * {{ box-sizing: border-box; }}
      html, body {{ height: 100%; }}
      body {{
        margin: 0;
        display: grid;
        grid-template-rows: 56px 1fr 56px;
        min-height: 100vh;
        background: radial-gradient(circle at top left, #fff7dd, var(--bg) 40%, #e8f1ef 100%);
        color: var(--ink);
        font-family: var(--body-font);
        overflow: hidden;
      }}
      .topbar, .nav {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 18px;
        background: rgba(255, 253, 248, 0.78);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--line);
      }}
      .nav {{
        border-top: 1px solid var(--line);
        border-bottom: none;
      }}
      .shell-label {{
        font-family: var(--mono-font);
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
      }}
      [data-role="progress"] {{
        font-family: var(--mono-font);
        font-size: 13px;
        color: var(--muted);
      }}
      #deck {{
        min-height: 0;
        padding: 12px;
      }}
      .page {{
        height: 100%;
        min-height: 0;
        background: rgba(255, 253, 248, 0.96);
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: clamp(14px, 2.6vw, 30px);
        overflow: hidden;
        display: none;
        gap: clamp(10px, 2vw, 18px);
      }}
      .page.is-active {{
        display: grid;
      }}
      .module {{
        min-width: 0;
      }}
      h1, h2, h3, p, ol, ul, table {{
        margin: 0;
      }}
      h1, h2, h3 {{
        font-family: var(--heading-font);
      }}
      h1 {{ font-size: clamp(30px, 4vw, 54px); line-height: 1; max-width: 12ch; }}
      h2 {{ font-size: clamp(24px, 3vw, 38px); line-height: 1.05; }}
      h3 {{ font-size: clamp(15px, 1.7vw, 20px); }}
      p, li, td, th {{
        font-size: clamp(11px, 1.35vw, 15px);
        line-height: 1.35;
      }}
      .eyebrow {{
        font-family: var(--mono-font);
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--accent);
      }}
      .subtitle {{ max-width: 58ch; color: var(--muted); }}
      .year-chip {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 14px;
        border-radius: 999px;
        background: var(--accent-soft);
        color: var(--accent);
        font-family: var(--mono-font);
        font-size: 12px;
      }}
      .brand-mark svg {{ width: clamp(120px, 18vw, 180px); height: auto; }}
      .page[data-page-id="cover"] {{
        grid-template-columns: 1.3fr 0.7fr;
        grid-template-rows: auto auto 1fr;
        align-items: start;
      }}
      .page[data-page-id="cover"] .hero,
      .page[data-page-id="cover"] .title-block,
      .page[data-page-id="cover"] .year-chip {{ grid-column: 1; }}
      .page[data-page-id="cover"] .brand-mark {{
        grid-column: 2;
        grid-row: 1 / span 3;
        justify-self: end;
        align-self: start;
      }}
      .page[data-page-id="agenda"] {{
        grid-template-columns: 1.2fr 0.8fr;
        align-content: start;
      }}
      .agenda-list ol {{
        padding-left: 22px;
        display: grid;
        gap: 8px;
      }}
      .agenda-context {{
        padding: 14px 16px;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: #f6faf9;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
      }}
      th, td {{
        padding: 8px 9px;
        border-bottom: 1px solid var(--line);
        text-align: left;
        vertical-align: top;
      }}
      th {{
        color: var(--muted);
        font-size: clamp(10px, 1.1vw, 13px);
      }}
      .snapshot-explainer,
      .mix-explainer,
      .co2-explainer,
      .method-note,
      .source-note-callout {{
        padding: 12px 14px;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: #fbfaf6;
      }}
      .power-grid {{
        display: grid;
        grid-template-columns: minmax(0, 1.8fr) minmax(220px, 0.9fr);
        gap: 16px;
        min-height: 0;
      }}
      .mix-chart svg, .co2-chart svg {{
        width: 100%;
        height: auto;
        display: block;
        background: white;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 8px;
      }}
      .legend {{
        list-style: none;
        padding: 0;
        display: grid;
        grid-template-columns: 1fr;
        gap: 8px;
      }}
      .legend li {{
        display: flex;
        align-items: center;
        gap: 8px;
      }}
      .swatch {{
        width: 12px;
        height: 12px;
        border-radius: 999px;
        display: inline-block;
      }}
      .implication-grid {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
      }}
      .implication-card {{
        padding: 16px;
        border-radius: 18px;
        background: linear-gradient(180deg, #fff 0%, #f4fbfa 100%);
        border: 1px solid var(--line);
        display: grid;
        gap: 10px;
      }}
      .nav button {{
        appearance: none;
        border: none;
        border-radius: 999px;
        padding: 10px 16px;
        font: inherit;
        background: var(--accent);
        color: white;
        cursor: pointer;
      }}
      .nav button[disabled] {{
        opacity: 0.4;
        cursor: default;
      }}
      .nav-actions {{
        display: flex;
        gap: 10px;
      }}
      @media (max-width: 900px) {{
        .page[data-page-id="cover"],
        .page[data-page-id="agenda"],
        .power-grid {{
          grid-template-columns: 1fr;
        }}
        .page[data-page-id="cover"] .brand-mark {{
          grid-column: 1;
          grid-row: auto;
          justify-self: start;
        }}
      }}
      @media (max-width: 700px) {{
        .implication-grid {{
          grid-template-columns: 1fr;
        }}
      }}
      @media (max-height: 420px) and (orientation: landscape) {{
        body {{
          grid-template-rows: 44px 1fr 44px;
        }}
        .topbar, .nav {{
          padding: 6px 12px;
        }}
        #deck {{
          padding: 6px;
        }}
        .page {{
          padding: 10px 12px;
          gap: 8px;
          border-radius: 18px;
        }}
        h1 {{
          font-size: 24px;
          line-height: 0.96;
          max-width: 11ch;
        }}
        h2 {{
          font-size: 18px;
        }}
        h3 {{
          font-size: 13px;
        }}
        p, li, td, th {{
          font-size: 10px;
          line-height: 1.2;
        }}
        th, td {{
          padding: 5px 6px;
        }}
        .brand-mark svg {{
          width: 92px;
        }}
        .year-chip {{
          padding: 6px 10px;
          font-size: 10px;
        }}
        .snapshot-explainer,
        .mix-explainer,
        .co2-explainer,
        .method-note,
        .source-note-callout,
        .implication-card,
        .agenda-context {{
          padding: 10px 12px;
        }}
        .page[data-page-id="cover"] {{
          grid-template-columns: 1.25fr 0.75fr;
        }}
        .page[data-page-id="cover"] .brand-mark {{
          grid-column: 2;
          grid-row: 1 / span 3;
          justify-self: end;
        }}
        .page[data-page-id="agenda"] {{
          grid-template-columns: 1.2fr 0.8fr;
        }}
        .power-grid {{
          grid-template-columns: minmax(0, 1.7fr) minmax(150px, 0.8fr);
          gap: 10px;
        }}
        .mix-chart svg, .co2-chart svg {{
          max-height: 132px;
          width: auto;
          max-width: 100%;
          margin: 0 auto;
        }}
        .legend {{
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 6px 8px;
        }}
        .implication-grid {{
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 10px;
        }}
      }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <div class="shell-label">North America Power Mix Brief</div>
      <div data-role="progress">1 / 7</div>
    </header>
    <main id="deck">
{render_pages(context)}
    </main>
    <nav class="nav">
      <div class="shell-label">Local-file deck</div>
      <div class="nav-actions">
        <button id="nav-prev" type="button">Previous</button>
        <button id="nav-next" type="button">Next</button>
      </div>
    </nav>
    <script>
      const pages = Array.from(document.querySelectorAll('.page'));
      const progress = document.querySelector('[data-role="progress"]');
      const prevButton = document.getElementById('nav-prev');
      const nextButton = document.getElementById('nav-next');
      let activeIndex = 0;

      function applyPageState() {{
        pages.forEach((page, index) => {{
          const active = index === activeIndex;
          page.hidden = !active;
          page.classList.toggle('is-active', active);
        }});
        progress.textContent = `${{activeIndex + 1}} / ${{pages.length}}`;
        prevButton.disabled = activeIndex === 0;
        nextButton.disabled = activeIndex === pages.length - 1;
      }}

      window.goToPage = (index) => {{
        if (index < 0 || index >= pages.length) return;
        activeIndex = index;
        applyPageState();
      }};

      prevButton.addEventListener('click', () => window.goToPage(activeIndex - 1));
      nextButton.addEventListener('click', () => window.goToPage(activeIndex + 1));
      window.addEventListener('keydown', (event) => {{
        if (event.key === 'ArrowRight') window.goToPage(activeIndex + 1);
        if (event.key === 'ArrowLeft') window.goToPage(activeIndex - 1);
      }});
      applyPageState();
    </script>
  </body>
</html>
"""


def build_manifest(context: dict) -> dict:
    required_pages = {page["page_id"]: page for page in context["contract"]["required_pages"]}
    key_files_by_page = {
        "cover": [
            "data/world_bank_population.json",
            "data/world_bank_gdp.json",
            "data/annual_co2_emissions.csv",
            "data/electricity_prod_source.csv",
        ],
        "agenda": [],
        "snapshot": [
            "data/world_bank_population.json",
            "data/world_bank_gdp.json",
            "data/annual_co2_emissions.csv",
            "data/electricity_prod_source.csv",
        ],
        "power-mix": ["data/electricity_prod_source.csv"],
        "emissions": ["data/annual_co2_emissions.csv"],
        "implications": [
            "data/world_bank_population.json",
            "data/world_bank_gdp.json",
            "data/annual_co2_emissions.csv",
            "data/electricity_prod_source.csv",
        ],
        "appendix": ["data/country_profile.json"],
    }
    pages = []
    for idx, page_id in enumerate(context["contract"]["page_order"]):
        page = required_pages[page_id]
        pages.append({
            "page_id": page_id,
            "title": page["title"],
            "source_outline_index": idx,
            "chart_ids": page["required_chart_ids"],
            "module_ids": page["required_modules"],
            "key_data_files": key_files_by_page[page_id],
        })
    return {
        "site_path": "north_america_power_mix_brief.html",
        "pages": pages,
        "source_files": [
            "data/country_profile.json",
            "data/world_bank_population.json",
            "data/world_bank_gdp.json",
            "data/annual_co2_emissions.csv",
            "data/electricity_prod_source.csv",
        ],
        "key_metrics": {
            "population_year": context["population_year"],
            "gdp_year": context["gdp_year"],
            "co2_year": context["co2_year"],
            "electricity_year": context["electricity_year"],
        },
        "embedded_assets": ["assets/brand_mark.svg", "assets/brand_tokens.json"],
        "notes": [
            "Single-file local deck output.",
            "Metric years are resolved separately for each data family using the latest common year.",
        ],
    }


def main() -> int:
    args = parse_args()
    brief_root = Path(args.brief_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    context = build_context(brief_root)
    html_text = render_html(context)
    manifest = build_manifest(context)

    (output_root / "north_america_power_mix_brief.html").write_text(html_text, encoding="utf-8")
    (output_root / "site_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod 755 /app/workspace/build_site.py
python3 /app/workspace/build_site.py --brief-root /app/power_brief --output-root /app/output
