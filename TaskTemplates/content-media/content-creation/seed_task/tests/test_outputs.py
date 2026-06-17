from __future__ import annotations

import re
from pathlib import Path

from conftest import (
    CAMPAIGN_ROOT,
    CLAIM_BANK_PATH,
    CONTRACT_PATH,
    OUTPUT_ROOT,
    SOURCE_MANIFEST_PATH,
    load_json,
    make_alternate_campaign_copy,
    parse_thread_posts,
    parse_video_scenes,
    read_text,
    run_build,
    word_count,
)


STOPWORDS = {
    "about",
    "after",
    "between",
    "closer",
    "current",
    "deliver",
    "delivered",
    "global",
    "government",
    "growth",
    "points",
    "power",
    "reached",
    "renewable",
    "renewables",
    "still",
    "their",
    "total",
    "which",
    "would",
    "year",
}


def evidence_supports_claim(evidence: str, claim: dict) -> bool:
    source_extracts = {
        extract
        for item in load_json(CAMPAIGN_ROOT / "data" / "source_extracts.json")["extracts"]
        if item["source_id"] == claim["source_id"]
        for extract in item["supported_points"]
    }

    if claim["statement"] in evidence:
        return True
    if evidence in source_extracts:
        return True

    evidence_lower = evidence.lower()
    evidence_tokens = set(re.findall(r"[a-z0-9]+", evidence_lower))
    claim_tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", claim["statement"].lower())
        if len(token) >= 4 and token not in STOPWORDS
    }
    keyword_overlap = claim_tokens & evidence_tokens

    value_hits = 0
    for value in claim.get("data", {}).values():
        if isinstance(value, (int, float)):
            plain = str(value).lower()
            grouped = f"{value:,}".lower()
            if plain in evidence_lower or grouped in evidence_lower:
                value_hits += 1
        elif isinstance(value, str):
            lowered = value.lower()
            if len(lowered) >= 4 and lowered in evidence_lower:
                value_hits += 1
        elif isinstance(value, list):
            for item in value:
                lowered = str(item).lower()
                if len(lowered) >= 4 and lowered in evidence_lower:
                    value_hits += 1

    return len(keyword_overlap) >= 2 or (len(keyword_overlap) >= 1 and value_hits >= 1) or value_hits >= 2


def test_formal_build_produces_required_outputs() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == {
        "newsletter_intro.md",
        "linkedin_post.md",
        "thread.md",
        "video_script.md",
        "content_manifest.json",
    }


def test_manifest_contract_and_support_notes_are_complete() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    contract = load_json(CONTRACT_PATH)
    manifest = load_json(OUTPUT_ROOT / "content_manifest.json")
    claims = {item["id"]: item for item in load_json(CLAIM_BANK_PATH)["claims"]}
    sources = {item["id"] for item in load_json(SOURCE_MANIFEST_PATH)["sources"]}

    assert list(manifest.keys()) == contract["manifest_required_keys"]
    assert manifest["campaign_title"] == contract["campaign_title"]
    assert manifest["audience"] == contract["audience"]
    assert len(manifest["core_messages"]) == len(contract["core_messages"])
    for message in manifest["core_messages"]:
        assert isinstance(message, str)
        assert len(message.strip()) >= 40
    assert [item["file"] for item in manifest["deliverables"]] == [
        "newsletter_intro.md",
        "linkedin_post.md",
        "thread.md",
        "video_script.md",
    ]
    assert sorted(manifest["sources_used"]) == sorted(sources)

    deliverable_files = {item["file"] for item in manifest["deliverables"]}
    for note in manifest["claim_support_notes"]:
        assert note["file"] in deliverable_files
        assert note["claim_id"] in claims
        assert note["source_id"] == claims[note["claim_id"]]["source_id"]
        assert note["source_id"] in sources
        assert evidence_supports_claim(note["evidence"], claims[note["claim_id"]])

    noted_pairs = {(note["file"], note["claim_id"]) for note in manifest["claim_support_notes"]}
    for deliverable in manifest["deliverables"]:
        for claim_id in deliverable["claims_used"]:
            assert (deliverable["file"], claim_id) in noted_pairs


def test_outputs_are_grounded_and_channel_specific() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    claims = {item["id"]: item for item in load_json(CLAIM_BANK_PATH)["claims"]}
    c01 = claims["C01"]["data"]
    c02 = claims["C02"]["data"]
    c03 = claims["C03"]["data"]
    c04 = claims["C04"]["data"]
    c05 = claims["C05"]["data"]
    c09 = claims["C09"]["data"]

    newsletter = read_text(OUTPUT_ROOT / "newsletter_intro.md")
    linkedin = read_text(OUTPUT_ROOT / "linkedin_post.md")
    thread = read_text(OUTPUT_ROOT / "thread.md")
    video = read_text(OUTPUT_ROOT / "video_script.md")

    assert f"{c01['capacity_gw']:,} GW" in newsletter
    assert f"{c01['annual_addition_gw']:,} GW" in newsletter
    assert f"{c03['benchmark_gw']:,} GW" in newsletter
    assert f"{c04['ambition_gw']:,} GW" in newsletter
    assert 220 <= word_count(newsletter) <= 320

    assert f"{c01['capacity_gw']:,} GW" in linkedin
    assert f"{c03['benchmark_gw']:,} GW" in linkedin
    assert f"{c04['ambition_gw']:,} GW" in linkedin
    assert 120 <= word_count(linkedin) <= 220
    assert not linkedin.strip().endswith("?")

    posts = parse_thread_posts(thread)
    assert len(posts) == 6
    for index, post in enumerate(posts, start=1):
        assert post.startswith(f"{index}.")
        assert len(post) < 280
    assert f"{c01['capacity_gw']:,} GW" in posts[0]
    assert f"{c02['expansion_share_pct']:.1f}%" in posts[1]
    assert "solar" in posts[2].lower()
    assert c05["share_text"] in posts[2].lower() or "main engine" in posts[2].lower()
    assert c09["country"] in posts[3]
    assert f"{c09['solar_twh']:,} TWh" in posts[3]
    assert f"{c09['wind_twh']:,} TWh" in posts[3]
    assert f"{c03['benchmark_gw']:,} GW" in posts[4]

    scenes = parse_video_scenes(video)
    assert len(scenes) == 6
    for index, scene in enumerate(scenes, start=1):
        assert scene.startswith(f"Scene {index}") or scene.startswith(f"Scene: {index}")
        assert "Voiceover:" in scene
        assert "On-screen text:" in scene
    assert f"{c01['capacity_gw']:,} GW" in video
    assert f"{c04['ambition_gw']:,} GW" in video


def test_channel_contract_detail_and_banned_phrases() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    contract = load_json(CONTRACT_PATH)
    newsletter = read_text(OUTPUT_ROOT / "newsletter_intro.md")
    linkedin = read_text(OUTPUT_ROOT / "linkedin_post.md")
    thread = read_text(OUTPUT_ROOT / "thread.md")
    video = read_text(OUTPUT_ROOT / "video_script.md")

    for text in [newsletter, linkedin, thread, video]:
        lower = text.lower()
        for phrase in contract["banned_phrases"]:
            assert phrase not in lower

    posts = parse_thread_posts(thread)
    assert max(len(post) for post in posts) <= 250

    scenes = parse_video_scenes(video)
    for scene in scenes:
        voiceover = ""
        onscreen = ""
        for line in scene.splitlines():
            if line.startswith("Voiceover:"):
                voiceover = line.split("Voiceover:", 1)[1].strip()
            if line.startswith("On-screen text:"):
                onscreen = line.split("On-screen text:", 1)[1].strip()
        assert voiceover
        assert onscreen
        assert len(onscreen) < len(voiceover)


def test_newsletter_uses_supplied_house_style() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    style_samples = read_text(CAMPAIGN_ROOT / "voice" / "house_style_samples.md")
    newsletter = read_text(OUTPUT_ROOT / "newsletter_intro.md")
    lower = newsletter.lower()

    anchor_hits = sum(
        phrase in lower
        for phrase in [
            "the shift is already visible in the numbers",
            "one chart can show the scale",
            "the next decision sits",
            "the headline number is not the whole story",
        ]
    )
    assert anchor_hits >= 1 or shingle_overlap(style_samples, newsletter, size=4) >= 0.02


def test_newsletter_stays_on_global_briefing_arc() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout

    claims = {item["id"]: item for item in load_json(CLAIM_BANK_PATH)["claims"]}
    newsletter = read_text(OUTPUT_ROOT / "newsletter_intro.md")
    assert f"{claims['C01']['data']['capacity_gw']:,} GW" in newsletter
    assert f"{claims['C04']['data']['ambition_gw']:,} GW" in newsletter
    assert "permitting" in newsletter.lower()
    assert "grid" in newsletter.lower()
    assert "financing" in newsletter.lower()


def test_linkedin_uses_business_reader_operating_contrast() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    linkedin = read_text(OUTPUT_ROOT / "linkedin_post.md").lower()
    assert any(token in linkedin for token in ["business", "strategy", "operational", "operating", "market"])
    assert "permitting" in linkedin
    assert "grid" in linkedin
    assert "financing" in linkedin


def test_thread_claim_arc_stays_on_global_argument() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    posts = parse_thread_posts(read_text(OUTPUT_ROOT / "thread.md"))
    manifest = load_json(OUTPUT_ROOT / "content_manifest.json")
    first_post = posts[0].lower()
    assert (
        "renewable power capacity" in first_post
        or "renewable capacity" in first_post
        or ("renewables" in first_post and "capacity" in first_post)
    )
    assert "total power capacity expansion" in posts[1].lower()
    assert "two-thirds" in posts[2].lower() or "main engine" in posts[2].lower()
    assert "china" in posts[3].lower()
    assert "2030" in posts[4]
    assert "permitting" in posts[5].lower()
    assert any(
        note["file"] == "thread.md" and note["section"] == "post_3" and note["claim_id"] == "C05"
        for note in manifest["claim_support_notes"]
    )


def test_alternate_fixture_rerun_updates_outputs() -> None:
    baseline = run_build()
    assert baseline.returncode == 0, baseline.stderr or baseline.stdout
    baseline_newsletter = read_text(OUTPUT_ROOT / "newsletter_intro.md")
    baseline_manifest = read_text(OUTPUT_ROOT / "content_manifest.json")
    baseline_video = read_text(OUTPUT_ROOT / "video_script.md")

    tmpdir, alt_root = make_alternate_campaign_copy()
    try:
        alt_output = Path(tmpdir.name) / "output"
        alt_result = run_build(campaign_root=alt_root, output_root=alt_output)
        assert alt_result.returncode == 0, alt_result.stderr or alt_result.stdout

        alt_newsletter = read_text(alt_output / "newsletter_intro.md")
        alt_manifest = read_text(alt_output / "content_manifest.json")
        alt_video = read_text(alt_output / "video_script.md")

        assert "board-ready public summary" in alt_manifest
        assert baseline_newsletter != alt_newsletter
        assert baseline_manifest != alt_manifest
        assert baseline_video != alt_video
        assert "4,520 GW" in alt_newsletter
        assert "612 GW" in alt_newsletter
        assert "8,600 GW" in alt_newsletter or "8,600 GW" in alt_video
        assert "610 TWh" in alt_video
    finally:
        tmpdir.cleanup()
