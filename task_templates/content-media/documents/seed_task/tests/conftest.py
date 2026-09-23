from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from docx import Document


TASK_ROOT = Path("/app")
BRIEFING_ROOT = Path(os.environ.get("TASK_BRIEFING_ROOT", "/app/briefing"))
WORKSPACE_ROOT = Path(os.environ.get("TASK_WORKSPACE_ROOT", "/app/workspace"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/app/output"))
BUILD_ENTRYPOINT = WORKSPACE_ROOT / "build_packet.py"
CONTRACT_PATH = BRIEFING_ROOT / "contracts" / "briefing_contract.json"
DRAFT_PATH = BRIEFING_ROOT / "drafts" / "briefing_draft.docx"
PANDOC_BIN = os.environ.get("PANDOC_BIN", "pandoc")
SOFFICE_BIN = os.environ.get("SOFFICE_BIN", "soffice")

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}
COUNTRY_ORDER = ["CAN", "MEX", "USA"]
COUNTRY_NAMES = {"CAN": "Canada", "MEX": "Mexico", "USA": "United States"}
SOURCE_LABELS = ["Other renewables", "Bioenergy", "Solar", "Wind", "Hydropower", "Nuclear", "Oil", "Gas", "Coal"]


def run_packet(briefing_root: Path = BRIEFING_ROOT, output_root: Path = OUTPUT_ROOT) -> subprocess.CompletedProcess[str]:
    output_root.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            "python3",
            str(BUILD_ENTRYPOINT),
            "--briefing-root",
            str(briefing_root),
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


def sha256_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def briefing_integrity() -> dict[str, str]:
    return {
        "briefing_sha256": sha256_tree(BRIEFING_ROOT),
    }


def unzip_part(docx_path: Path, member: str) -> bytes:
    with zipfile.ZipFile(docx_path) as zf:
        return zf.read(member)


def list_media(docx_path: Path) -> dict[str, str]:
    media: dict[str, str] = {}
    with zipfile.ZipFile(docx_path) as zf:
        for name in zf.namelist():
            if name.startswith("word/media/"):
                media[name] = hashlib.sha256(zf.read(name)).hexdigest()
    return media


def document_markdown(docx_path: Path) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "doc.md"
        subprocess.run(
            [PANDOC_BIN, str(docx_path), "-t", "gfm", "-o", str(out)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return out.read_text(encoding="utf-8")


def assert_docx_opens(docx_path: Path) -> None:
    with zipfile.ZipFile(docx_path) as zf:
        assert zf.testzip() is None
    document = Document(str(docx_path))
    assert len(document.paragraphs) >= 1


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
            values = {}
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


def expected_context(briefing_root: Path = BRIEFING_ROOT) -> dict:
    contract = load_json(briefing_root / "contracts" / "briefing_contract.json")
    profiles = {row["id"]: row for row in load_json(briefing_root / "data" / "country_profile.json")[1]}
    pop_year, pop_values = latest_common_world_bank_year(load_json(briefing_root / "data" / "world_bank_population.json")[1], COUNTRY_ORDER)
    gdp_year, gdp_values = latest_common_world_bank_year(load_json(briefing_root / "data" / "world_bank_gdp.json")[1], COUNTRY_ORDER)
    co2_rows = load_csv_rows(briefing_root / "data" / "annual_co2_emissions.csv")
    co2_column = "Annual CO₂ emissions" if "Annual CO₂ emissions" in co2_rows[0] else "Annual CO2 emissions"
    co2_year, co2_values = latest_common_csv_year(co2_rows, COUNTRY_ORDER, [co2_column])
    co2_latest = {code: values[co2_column] for code, values in co2_values.items()}
    electricity_rows = load_csv_rows(briefing_root / "data" / "electricity_prod_source.csv")
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

    lowest_co2_code = min(co2_latest, key=co2_latest.get)
    highest_gdp_code = max(gdp_values, key=gdp_values.get)
    summary_lines = [
        f"{COUNTRY_NAMES[highest_gdp_code]} posted the largest GDP in {gdp_year} at ${fmt_trillions(gdp_values[highest_gdp_code])}T.",
        f"{COUNTRY_NAMES[lowest_co2_code]} carried the lowest annual CO2 total in {co2_year} at {fmt_megatonnes(co2_latest[lowest_co2_code])} Mt.",
        "Latest top power sources were "
        + ", ".join(
            f"{COUNTRY_NAMES[code]}: {top_source(electricity_values[code])[0]} ({top_source(electricity_values[code])[1]:.1f} TWh)"
            for code in COUNTRY_ORDER
        )
        + f" in {electricity_year}.",
    ]
    note_lines = parse_source_notes(briefing_root / "notes" / "source_notes.md")
    return {
        "contract": contract,
        "population_year": pop_year,
        "gdp_year": gdp_year,
        "co2_year": co2_year,
        "electricity_year": electricity_year,
        "snapshot_rows": snapshot_rows,
        "appendix_rows": appendix_rows,
        "summary_lines": summary_lines,
        "note_lines": note_lines,
        "co2_trend": trend,
    }


def make_alternate_briefing_copy() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmpdir = tempfile.TemporaryDirectory()
    alt_root = Path(tmpdir.name) / "briefing"
    shutil.copytree(BRIEFING_ROOT, alt_root)

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
