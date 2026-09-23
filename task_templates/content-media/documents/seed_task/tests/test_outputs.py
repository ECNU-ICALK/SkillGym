from __future__ import annotations

from pathlib import Path

from docx import Document

from conftest import (
    BRIEFING_ROOT,
    CONTRACT_PATH,
    DRAFT_PATH,
    OUTPUT_ROOT,
    assert_docx_opens,
    document_markdown,
    expected_context,
    list_media,
    load_json,
    make_alternate_briefing_copy,
    run_packet,
    unzip_part,
)


def normalize_markdown(markdown: str) -> str:
    return markdown.replace("\\$", "$").replace("\\`", "`")


def collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def document_paragraphs(docx_path: Path) -> list[str]:
    document = Document(str(docx_path))
    return [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]


def section_slice(paragraphs: list[str], heading: str, next_heading: str | None) -> list[str]:
    start = len(paragraphs) - 1 - paragraphs[::-1].index(heading)
    if next_heading is None:
        end = len(paragraphs)
    else:
        end = paragraphs.index(next_heading, start + 1)
    return paragraphs[start + 1:end]


def test_formal_build_produces_required_outputs() -> None:
    result = run_packet()
    assert result.returncode == 0, result.stderr or result.stdout

    output_docx = OUTPUT_ROOT / "north_america_energy_briefing.docx"
    output_manifest = OUTPUT_ROOT / "briefing_manifest.json"
    assert output_docx.exists()
    assert output_manifest.exists()
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == {"north_america_energy_briefing.docx", "briefing_manifest.json"}
    assert_docx_opens(output_docx)


def test_manifest_and_document_match_expected_metrics() -> None:
    result = run_packet()
    assert result.returncode == 0, result.stderr or result.stdout

    context = expected_context()
    manifest = load_json(OUTPUT_ROOT / "briefing_manifest.json")
    output_docx = OUTPUT_ROOT / "north_america_energy_briefing.docx"
    markdown = normalize_markdown(document_markdown(output_docx))
    paragraphs = document_paragraphs(output_docx)

    assert manifest["document_path"] == "north_america_energy_briefing.docx"
    assert manifest["countries"] == context["contract"]["countries"]
    assert manifest["source_files"] == context["contract"]["source_files"]
    assert manifest["key_metrics"] == {
        "population_year": context["population_year"],
        "gdp_year": context["gdp_year"],
        "co2_year": context["co2_year"],
        "electricity_year": context["electricity_year"],
    }
    assert [section["title"] for section in manifest["sections"]] == [
        section["title"] for section in context["contract"]["required_sections"]
    ]

    for section in context["contract"]["required_sections"]:
        assert section["title"] in markdown
    for row in context["snapshot_rows"]:
        assert row["country"] in markdown
        assert row["population_m"] in markdown
        assert row["gdp_t"] in markdown
        assert row["co2_mt"] in markdown
        assert row["top_source"] in markdown
        assert row["top_source_twh"] in markdown
    for row in context["appendix_rows"]:
        assert row["capital"] in markdown
        assert row["income"] in markdown
        assert row["region"] in markdown
    for note in context["note_lines"]:
        _, url = note.split(": ", 1)
        assert url in markdown

    executive_summary = section_slice(paragraphs, "1. Executive Summary", "2. Country Snapshot")
    summary_text = collapse_whitespace(" ".join(executive_summary))
    assert context["snapshot_rows"][-1]["country"] in summary_text
    assert str(context["gdp_year"]) in summary_text
    assert str(context["co2_year"]) in summary_text
    assert (
        context["snapshot_rows"][-1]["gdp_t"] in summary_text
        or "trillion" in summary_text.lower()
        or "output" in summary_text.lower()
        or "gdp" in summary_text.lower()
    )

    snapshot_section = section_slice(paragraphs, "2. Country Snapshot", "3. Electricity Mix")
    snapshot_text = collapse_whitespace(" ".join(snapshot_section))
    assert "population" in snapshot_text.lower()
    assert "gdp" in snapshot_text.lower()
    assert "co2" in snapshot_text.lower()
    assert (
        any(
            str(year) in snapshot_text
            for year in [
                context["population_year"],
                context["gdp_year"],
                context["co2_year"],
                context["electricity_year"],
            ]
        )
        or any(
            marker in snapshot_text.lower()
            for marker in ["combined", "three-country", "regional baseline", "accounts for", "%"]
        )
    )

    electricity_section = section_slice(paragraphs, "3. Electricity Mix", "4. CO2 Trend")
    electricity_text = collapse_whitespace(" ".join(electricity_section))
    assert context["contract"]["chart_contract"]["electricity_mix_latest"]["title"] in electricity_text
    assert "Latest common electricity year across all three countries" in electricity_text
    for row in context["snapshot_rows"]:
        assert row["country"] in electricity_text
        assert row["top_source"].lower() in electricity_text.lower()

    co2_section = section_slice(paragraphs, "4. CO2 Trend", "5. Source Notes")
    co2_text = collapse_whitespace(" ".join(co2_section))
    assert context["contract"]["chart_contract"]["co2_trend_recent"]["title"] in co2_text
    assert "Most recent common 10-year window across all three countries" in co2_text
    trend_start = context["co2_trend"][0][0]
    trend_end = context["co2_trend"][-1][0]
    assert (
        f"{trend_start}-{trend_end}" in co2_text
        or (str(trend_start) in co2_text and str(trend_end) in co2_text)
    )
    assert (
        "decline" in co2_text.lower()
        or "fell" in co2_text.lower()
        or "below" in co2_text.lower()
        or "(-" in co2_text
        or ("(-" in co2_text and "shift" in co2_text.lower())
    )

    source_notes = section_slice(paragraphs, "5. Source Notes", "Appendix A. Country Profile Notes")
    source_notes_text = collapse_whitespace(" ".join(source_notes))
    assert "population" in source_notes_text.lower()
    assert "gdp" in source_notes_text.lower()
    assert "co2" in source_notes_text.lower()
    assert str(context["population_year"]) in source_notes_text
    assert str(context["electricity_year"]) in source_notes_text


def test_document_shell_is_preserved_and_cleanup_is_complete() -> None:
    result = run_packet()
    assert result.returncode == 0, result.stderr or result.stdout

    output_docx = OUTPUT_ROOT / "north_america_energy_briefing.docx"
    markdown = document_markdown(output_docx)
    assert "{{" not in markdown
    assert "}}" not in markdown
    assert "TODO" not in markdown
    assert "TBD" not in markdown
    assert "Review comment:" not in markdown

    paragraphs = document_paragraphs(output_docx)
    contents_index = paragraphs.index("Contents")
    expected_contents = [
        "1. Executive Summary",
        "2. Country Snapshot",
        "3. Electricity Mix",
        "4. CO2 Trend",
        "5. Source Notes",
        "Appendix A. Country Profile Notes",
    ]
    contents_block = collapse_whitespace(" ".join(paragraphs[contents_index + 1: contents_index + 7]))
    cursor = 0
    for heading in expected_contents:
        found_at = contents_block.find(heading, cursor)
        if found_at == -1:
            plain_heading = heading.split(". ", 1)[-1].replace(": ", ". ")
            found_at = contents_block.find(plain_heading, cursor)
        assert found_at != -1
        cursor = found_at + len(heading)

    for part in ["word/header1.xml", "word/footer1.xml", "word/styles.xml"]:
        assert unzip_part(output_docx, part) == unzip_part(DRAFT_PATH, part)

    members = list_media(output_docx)
    draft_members = list_media(DRAFT_PATH)
    assert draft_members["word/media/image1.png"] in members.values()
    assert len(members) >= 3

    with_comments = unzip_part(DRAFT_PATH, "word/document.xml").decode("utf-8")
    cleaned = unzip_part(output_docx, "word/document.xml").decode("utf-8")
    assert "commentRangeStart" in with_comments
    assert "commentReference" in with_comments
    assert "commentRangeStart" not in cleaned
    assert "commentReference" not in cleaned

    import zipfile

    with zipfile.ZipFile(output_docx) as zf:
        assert "word/comments.xml" not in zf.namelist()


def test_alternate_fixture_rerun_changes_metrics_and_chart_media() -> None:
    result = run_packet()
    assert result.returncode == 0, result.stderr or result.stdout

    baseline_manifest = load_json(OUTPUT_ROOT / "briefing_manifest.json")
    baseline_media = list_media(OUTPUT_ROOT / "north_america_energy_briefing.docx")

    tmpdir, alt_briefing = make_alternate_briefing_copy()
    try:
        alt_output = Path(tmpdir.name) / "output"
        alt_result = run_packet(briefing_root=alt_briefing, output_root=alt_output)
        assert alt_result.returncode == 0, alt_result.stderr or alt_result.stdout

        alt_manifest = load_json(alt_output / "briefing_manifest.json")
        alt_context = expected_context(alt_briefing)
        alt_docx = alt_output / "north_america_energy_briefing.docx"
        alt_markdown = normalize_markdown(document_markdown(alt_docx))
        alt_paragraphs = document_paragraphs(alt_docx)
        alt_media = list_media(alt_output / "north_america_energy_briefing.docx")

        assert alt_manifest["key_metrics"] == {
            "population_year": alt_context["population_year"],
            "gdp_year": alt_context["gdp_year"],
            "co2_year": alt_context["co2_year"],
            "electricity_year": alt_context["electricity_year"],
        }
        compact_alt_markdown = collapse_whitespace(alt_markdown)
        assert alt_context["snapshot_rows"][0]["gdp_t"] in compact_alt_markdown
        assert alt_context["snapshot_rows"][-1]["top_source"] in compact_alt_markdown
        assert alt_context["snapshot_rows"][-1]["top_source_twh"] in compact_alt_markdown

        alt_exec = collapse_whitespace(" ".join(section_slice(alt_paragraphs, "1. Executive Summary", "2. Country Snapshot")))
        assert alt_context["snapshot_rows"][0]["country"] in alt_exec or alt_context["snapshot_rows"][-1]["country"] in alt_exec
        assert (
            alt_context["snapshot_rows"][0]["gdp_t"] in alt_exec
            or alt_context["snapshot_rows"][-1]["gdp_t"] in alt_exec
            or "trillion" in alt_exec.lower()
            or "output" in alt_exec.lower()
            or "gdp" in alt_exec.lower()
        )

        baseline_chart_hashes = {name: digest for name, digest in baseline_media.items() if name != "word/media/image1.png"}
        alt_chart_hashes = {name: digest for name, digest in alt_media.items() if name != "word/media/image1.png"}
        assert baseline_chart_hashes != alt_chart_hashes
    finally:
        tmpdir.cleanup()
