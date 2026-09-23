#!/bin/bash
set -euo pipefail

cat > /app/workspace/build_packet.py <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}
SOURCE_LABELS = ["Other renewables", "Bioenergy", "Solar", "Wind", "Hydropower", "Nuclear", "Oil", "Gas", "Coal"]
COUNTRY_ORDER = ["CAN", "MEX", "USA"]
COUNTRY_NAMES = {"CAN": "Canada", "MEX": "Mexico", "USA": "United States"}

for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the North America energy briefing packet.")
    parser.add_argument("--briefing-root", default="/app/briefing")
    parser.add_argument("--output-root", default="/app/output")
    return parser.parse_args()


def load_contract(briefing_root: Path) -> dict:
    return json.loads((briefing_root / "contracts" / "briefing_contract.json").read_text(encoding="utf-8"))


def load_country_profile(briefing_root: Path) -> dict[str, dict]:
    payload = json.loads((briefing_root / "data" / "country_profile.json").read_text(encoding="utf-8"))[1]
    return {row["id"]: row for row in payload}


def load_world_bank_series(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))[1]


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def latest_common_world_bank_year(rows: list[dict], codes: Iterable[str]) -> tuple[int, dict[str, float]]:
    wanted = set(codes)
    filtered = [row for row in rows if row["countryiso3code"] in wanted and row["value"] is not None]
    years = sorted({int(row["date"]) for row in filtered}, reverse=True)
    for year in years:
        sample = {row["countryiso3code"]: float(row["value"]) for row in filtered if int(row["date"]) == year}
        if set(sample) == wanted:
            return year, sample
    raise ValueError("No common year found for World Bank series")


def latest_common_csv_year(rows: list[dict[str, str]], codes: Iterable[str], value_columns: list[str]) -> tuple[int, dict[str, dict[str, float]]]:
    wanted = set(codes)
    years = sorted({int(row["Year"]) for row in rows if row["Code"] in wanted}, reverse=True)
    for year in years:
        yearly: dict[str, dict[str, float]] = {}
        for row in rows:
            if row["Code"] not in wanted or int(row["Year"]) != year:
                continue
            values = {}
            for column in value_columns:
                raw = row.get(column, "")
                if raw in ("", None):
                    continue
                values[column] = float(raw)
            if values:
                yearly[row["Code"]] = values
        if set(yearly) == wanted:
            return year, yearly
    raise ValueError("No common year found for CSV series")


def recent_common_window(rows: list[dict[str, str]], codes: Iterable[str], value_column: str, years_count: int) -> list[tuple[int, dict[str, float]]]:
    wanted = set(codes)
    years = sorted({int(row["Year"]) for row in rows if row["Code"] in wanted})
    samples: list[tuple[int, dict[str, float]]] = []
    for year in years:
        yearly = {
            row["Code"]: float(row[value_column])
            for row in rows
            if row["Code"] in wanted and int(row["Year"]) == year and row.get(value_column) not in ("", None)
        }
        if set(yearly) == wanted:
            samples.append((year, yearly))
    if len(samples) < years_count:
        raise ValueError("Not enough common years for trend window")
    return samples[-years_count:]


def top_source(values: dict[str, float]) -> tuple[str, float]:
    ranked = sorted(((source, values.get(source, 0.0)) for source in SOURCE_LABELS), key=lambda item: item[1], reverse=True)
    return ranked[0]


def fmt_millions(value: float) -> str:
    return f"{value / 1_000_000:.1f}"


def fmt_trillions(value: float) -> str:
    return f"{value / 1_000_000_000_000:.2f}"


def fmt_megatonnes(value: float) -> str:
    return f"{value / 1_000_000:.1f}"


def parse_source_notes(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    results: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "Formatting notes:":
            break
        if line.startswith("- "):
            combined = line[2:].strip()
            look_ahead = idx + 1
            while look_ahead < len(lines) and lines[look_ahead].startswith("  "):
                combined += " " + lines[look_ahead].strip()
                look_ahead += 1
            results.append(combined)
            idx = look_ahead
            continue
        idx += 1
    return results


def build_context(briefing_root: Path, contract: dict) -> dict:
    codes = contract["country_codes"]
    profiles = load_country_profile(briefing_root)
    pop_year, pop_values = latest_common_world_bank_year(load_world_bank_series(briefing_root / "data" / "world_bank_population.json"), codes)
    gdp_year, gdp_values = latest_common_world_bank_year(load_world_bank_series(briefing_root / "data" / "world_bank_gdp.json"), codes)
    co2_rows = load_csv_rows(briefing_root / "data" / "annual_co2_emissions.csv")
    co2_year, co2_values = latest_common_csv_year(co2_rows, codes, ["Annual CO2 emissions", "Annual CO₂ emissions"])
    co2_column = "Annual CO₂ emissions" if "Annual CO₂ emissions" in co2_rows[0] else "Annual CO2 emissions"
    co2_latest = {code: values[co2_column] for code, values in co2_values.items()}
    elec_rows = load_csv_rows(briefing_root / "data" / "electricity_prod_source.csv")
    elec_year, elec_values = latest_common_csv_year(elec_rows, codes, SOURCE_LABELS)
    trend = recent_common_window(co2_rows, codes, co2_column, contract["metrics_policy"]["recent_co2_window_years"])

    snapshot_rows = []
    appendix_rows = []
    for code in codes:
        source_name, source_value = top_source(elec_values[code])
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

    lowest_co2_code = min(co2_latest, key=co2_latest.get)
    highest_gdp_code = max(gdp_values, key=gdp_values.get)
    summary_lines = [
        f"{COUNTRY_NAMES[highest_gdp_code]} posted the largest GDP in {gdp_year} at ${fmt_trillions(gdp_values[highest_gdp_code])}T.",
        f"{COUNTRY_NAMES[lowest_co2_code]} carried the lowest annual CO2 total in {co2_year} at {fmt_megatonnes(co2_latest[lowest_co2_code])} Mt.",
        "Latest top power sources were "
        + ", ".join(
            f"{COUNTRY_NAMES[code]}: {top_source(elec_values[code])[0]} ({top_source(elec_values[code])[1]:.1f} TWh)"
            for code in codes
        )
        + f" in {elec_year}.",
    ]

    electricity_shares = {}
    for code in codes:
        total = sum(elec_values[code].values())
        source_name, source_value = top_source(elec_values[code])
        electricity_shares[code] = {
            "source": source_name,
            "pct": round((source_value / total) * 100),
        }

    trend_start_year = trend[0][0]
    trend_end_year = trend[-1][0]
    trend_delta_mt = {
        code: (trend[-1][1][code] - trend[0][1][code]) / 1_000_000
        for code in codes
    }
    largest_decline_code = min(trend_delta_mt, key=trend_delta_mt.get)
    remaining_codes = [code for code in codes if code != largest_decline_code]

    return {
        "appendix_rows": appendix_rows,
        "co2_trend": trend,
        "co2_commentary": (
            f"{COUNTRY_NAMES[largest_decline_code]} shows the largest absolute decline over the {trend_start_year}-{trend_end_year} window "
            f"({abs(trend_delta_mt[largest_decline_code]):.1f} Mt from {trend_start_year} to {trend_end_year}), "
            f"while {COUNTRY_NAMES[remaining_codes[0]]} and {COUNTRY_NAMES[remaining_codes[1]]} also trend below their window-start levels."
        ),
        "co2_year": co2_year,
        "electricity_commentary": (
            f"{COUNTRY_NAMES['CAN']} remains {electricity_shares['CAN']['source'].lower()}-led "
            f"({electricity_shares['CAN']['pct']}% of the displayed mix), while "
            f"{electricity_shares['MEX']['source'].lower()} is the largest source in {COUNTRY_NAMES['MEX']} "
            f"({electricity_shares['MEX']['pct']}%) and "
            f"{electricity_shares['USA']['source'].lower()} in {COUNTRY_NAMES['USA']} "
            f"({electricity_shares['USA']['pct']}%)."
        ),
        "electricity_values": elec_values,
        "electricity_year": elec_year,
        "gdp_year": gdp_year,
        "note_lines": parse_source_notes(briefing_root / "notes" / "source_notes.md"),
        "population_year": pop_year,
        "snapshot_rows": snapshot_rows,
        "summary_lines": summary_lines,
    }


def create_electricity_chart(context: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=150)
    bottoms = [0.0, 0.0, 0.0]
    for source in SOURCE_LABELS:
        values = [context["electricity_values"][code].get(source, 0.0) for code in COUNTRY_ORDER]
        ax.barh([COUNTRY_NAMES[code] for code in COUNTRY_ORDER], values, left=bottoms, label=source)
        bottoms = [left + value for left, value in zip(bottoms, values)]
    ax.set_title(f"Latest electricity mix ({context['electricity_year']})")
    ax.set_xlabel("TWh")
    ax.legend(ncol=3, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def create_co2_chart(context: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=150)
    years = [year for year, _ in context["co2_trend"]]
    for code in COUNTRY_ORDER:
        values = [sample[code] / 1_000_000 for _, sample in context["co2_trend"]]
        ax.plot(years, values, marker="o", linewidth=2, label=COUNTRY_NAMES[code])
    ax.set_title(f"Annual CO2 emissions ({years[0]}-{years[-1]})")
    ax.set_ylabel("Mt CO2")
    ax.set_xlabel("Year")
    ax.grid(alpha=0.2)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def extract_text_with_newlines(elem: ET.Element) -> str:
    parts = []
    for node in elem.iter():
        if node.tag == f"{{{NS['w']}}}t" and node.text:
            parts.append(node.text)
        elif node.tag == f"{{{NS['w']}}}tab":
            parts.append("\t")
        elif node.tag == f"{{{NS['w']}}}br":
            parts.append("\n")
    return "".join(parts)


def set_paragraph_text(paragraph: ET.Element, text: str) -> None:
    runs = paragraph.findall("w:r", NS)
    if not runs:
        run = ET.SubElement(paragraph, f"{{{NS['w']}}}r")
        text_node = ET.SubElement(run, f"{{{NS['w']}}}t")
        text_node.text = text
        return
    first_run = runs[0]
    first_text = first_run.find("w:t", NS)
    if first_text is None:
        first_text = ET.SubElement(first_run, f"{{{NS['w']}}}t")
    first_text.text = text
    for extra_run in runs[1:]:
        paragraph.remove(extra_run)


def fill_table(table: ET.Element, rows: list[list[str]]) -> None:
    tr_nodes = table.findall("w:tr", NS)
    template_source = tr_nodes[1] if len(tr_nodes) > 1 else tr_nodes[0]
    template_row = ET.fromstring(ET.tostring(template_source))
    for tr in tr_nodes[1:]:
        table.remove(tr)
    for row_values in rows:
        tr = ET.fromstring(ET.tostring(template_row))
        row_cells = tr.findall("w:tc", NS)
        for cell, value in zip(row_cells, row_values):
            paragraph = cell.find(".//w:p", NS)
            if paragraph is None:
                paragraph = ET.SubElement(cell, f"{{{NS['w']}}}p")
            set_paragraph_text(paragraph, value)
        table.append(tr)


def table_header_row(table: ET.Element) -> list[str]:
    first_row = table.find("w:tr", NS)
    if first_row is None:
        return []
    headers: list[str] = []
    for cell in first_row.findall("w:tc", NS):
        headers.append(extract_text_with_newlines(cell).strip())
    return headers


def find_parent(root: ET.Element, target: ET.Element) -> ET.Element | None:
    return next((candidate for candidate in root.iter() if target in list(candidate)), None)


def make_paragraph(text: str) -> ET.Element:
    paragraph = ET.Element(f"{{{NS['w']}}}p")
    run = ET.SubElement(paragraph, f"{{{NS['w']}}}r")
    text_node = ET.SubElement(run, f"{{{NS['w']}}}t")
    text_node.text = text
    return paragraph


def replace_placeholder_text(document_xml: Path, context: dict) -> None:
    tree = ET.parse(document_xml)
    root = tree.getroot()
    ignorable_attr = f"{{{NS['mc']}}}Ignorable"
    if ignorable_attr in root.attrib:
        del root.attrib[ignorable_attr]
    contents_paragraph: ET.Element | None = None
    electricity_caption_paragraph: ET.Element | None = None
    co2_caption_paragraph: ET.Element | None = None
    source_notes_paragraph: ET.Element | None = None

    for paragraph in root.findall(".//w:p", NS):
        text = extract_text_with_newlines(paragraph)
        if "{{SUMMARY_LINE_1}}" in text:
            set_paragraph_text(paragraph, context["summary_lines"][0])
        elif "{{SUMMARY_LINE_2}}" in text:
            set_paragraph_text(paragraph, context["summary_lines"][1])
        elif "{{SUMMARY_LINE_3}}" in text:
            set_paragraph_text(paragraph, context["summary_lines"][2])
        elif "Contents placeholder" in text:
            set_paragraph_text(paragraph, "Contents")
            contents_paragraph = paragraph
        elif "Review comment:" in text:
            set_paragraph_text(paragraph, "")
        elif "{{ELECTRICITY_CAPTION}}" in text:
            set_paragraph_text(paragraph, "Figure 1. Latest electricity mix by source. Latest common electricity year across all three countries.")
            electricity_caption_paragraph = paragraph
        elif "{{CO2_CAPTION}}" in text:
            set_paragraph_text(paragraph, "Figure 2. Annual CO2 emissions trend. Most recent common 10-year window across all three countries.")
            co2_caption_paragraph = paragraph
        elif "{{SOURCE_NOTE_LINES}}" in text:
            set_paragraph_text(paragraph, "\n".join(context["note_lines"]))
            source_notes_paragraph = paragraph
        elif "{{APPENDIX_NOTE}}" in text:
            set_paragraph_text(paragraph, f"Population year {context['population_year']}; GDP year {context['gdp_year']}; CO2 year {context['co2_year']}; electricity year {context['electricity_year']}.")

    if contents_paragraph is not None:
        parent = find_parent(root, contents_paragraph)
        if parent is not None:
            insert_at = list(parent).index(contents_paragraph) + 1
            for title in [
                "1. Executive Summary",
                "2. Country Snapshot",
                "3. Electricity Mix",
                "4. CO2 Trend",
                "5. Source Notes",
                "Appendix A. Country Profile Notes",
            ]:
                parent.insert(insert_at, make_paragraph(title))
                insert_at += 1

    if electricity_caption_paragraph is not None:
        parent = find_parent(root, electricity_caption_paragraph)
        if parent is not None:
            insert_at = list(parent).index(electricity_caption_paragraph) + 1
            parent.insert(insert_at, make_paragraph(context["electricity_commentary"]))

    if co2_caption_paragraph is not None:
        parent = find_parent(root, co2_caption_paragraph)
        if parent is not None:
            insert_at = list(parent).index(co2_caption_paragraph) + 1
            parent.insert(insert_at, make_paragraph(context["co2_commentary"]))

    if source_notes_paragraph is not None:
        parent = find_parent(root, source_notes_paragraph)
        if parent is not None:
            insert_at = list(parent).index(source_notes_paragraph) + 1
            for text in [
                (
                    f"Metric-year rules applied from the delivery contract: population {context['population_year']}, "
                    f"GDP {context['gdp_year']}, CO2 {context['co2_year']}, electricity {context['electricity_year']}."
                ),
                "Population is shown in millions, GDP in trillion current USD, CO2 in megatonnes, and power-source labels use title case.",
            ]:
                parent.insert(insert_at, make_paragraph(text))
                insert_at += 1

    for table in root.findall(".//w:tbl", NS):
        headers = table_header_row(table)
        if headers == ["Country", "Population (M)", "GDP (T USD)", "CO2 (Mt)", "Top power source", "Top source TWh"]:
            fill_table(table, [
                [row["country"], row["population_m"], row["gdp_t"], row["co2_mt"], row["top_source"], row["top_source_twh"]]
                for row in context["snapshot_rows"]
            ])
            parent = find_parent(root, table)
            if parent is not None:
                insert_at = list(parent).index(table) + 1
                parent.insert(
                    insert_at,
                    make_paragraph(
                        "The snapshot table aligns the latest common non-null year available for each required metric: "
                        f"population {context['population_year']}, GDP {context['gdp_year']}, "
                        f"CO2 {context['co2_year']}, and electricity generation {context['electricity_year']}."
                    ),
                )
        elif headers == ["Country", "Capital", "Income level", "Region"]:
            fill_table(table, [
                [row["country"], row["capital"], row["income"], row["region"]]
                for row in context["appendix_rows"]
            ])

    tree.write(document_xml, encoding="utf-8", xml_declaration=True)


def strip_comment_parts(unpacked_root: Path) -> None:
    document_xml = unpacked_root / "word" / "document.xml"
    tree = ET.parse(document_xml)
    root = tree.getroot()
    for tag_name in ("commentRangeStart", "commentRangeEnd", "commentReference"):
        for elem in list(root.findall(f".//w:{tag_name}", NS)):
            parent = next((candidate for candidate in root.iter() if elem in list(candidate)), None)
            if parent is not None:
                parent.remove(elem)
    tree.write(document_xml, encoding="utf-8", xml_declaration=True)

    for name in ["comments.xml", "commentsExtended.xml", "commentsIds.xml", "people.xml", "commentsExtensible.xml"]:
        path = unpacked_root / "word" / name
        if path.exists():
            path.unlink()

    rels_path = unpacked_root / "word" / "_rels" / "document.xml.rels"
    if rels_path.exists():
        rels_tree = ET.parse(rels_path)
        rels_root = rels_tree.getroot()
        for rel in list(rels_root):
            if "comments" in rel.attrib.get("Target", ""):
                rels_root.remove(rel)
        rels_tree.write(rels_path, encoding="utf-8", xml_declaration=True)

    content_types = unpacked_root / "[Content_Types].xml"
    if content_types.exists():
        tree = ET.parse(content_types)
        root = tree.getroot()
        for child in list(root):
            part_name = child.attrib.get("PartName", "")
            if "comments" in part_name:
                root.remove(child)
        tree.write(content_types, encoding="utf-8", xml_declaration=True)


def repack_directory(unpacked_root: Path, output_docx: Path) -> None:
    output_docx.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_docx, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(unpacked_root.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(unpacked_root))


def render_output(briefing_root: Path, output_root: Path, contract: dict, context: dict) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    output_docx = output_root / contract["document_filename"]
    draft_path = briefing_root / "drafts" / "briefing_draft.docx"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        unpacked = tmp / "docx"
        with zipfile.ZipFile(draft_path) as zf:
            zf.extractall(unpacked)

        electricity_chart = tmp / "electricity.png"
        co2_chart = tmp / "co2.png"
        create_electricity_chart(context, electricity_chart)
        create_co2_chart(context, co2_chart)

        shutil.copyfile(electricity_chart, unpacked / "word" / "media" / "image2.png")
        shutil.copyfile(co2_chart, unpacked / "word" / "media" / "image3.png")

        replace_placeholder_text(unpacked / "word" / "document.xml", context)
        strip_comment_parts(unpacked)
        repack_directory(unpacked, output_docx)

    manifest = {
        "document_path": output_docx.name,
        "countries": contract["countries"],
        "source_files": contract["source_files"],
        "sections": [
            {
                "title": section["title"],
                "table_ids": section["table_ids"],
                "chart_ids": section["chart_ids"],
            }
            for section in contract["required_sections"]
        ],
        "key_metrics": {
            "population_year": context["population_year"],
            "gdp_year": context["gdp_year"],
            "co2_year": context["co2_year"],
            "electricity_year": context["electricity_year"],
        },
        "notes": context["summary_lines"],
    }
    (output_root / contract["manifest_filename"]).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    briefing_root = Path(args.briefing_root)
    output_root = Path(args.output_root)
    contract = load_contract(briefing_root)
    context = build_context(briefing_root, contract)
    render_output(briefing_root, output_root, contract, context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod 755 /app/workspace/build_packet.py
python3 /app/workspace/build_packet.py --briefing-root /app/briefing --output-root /app/output
