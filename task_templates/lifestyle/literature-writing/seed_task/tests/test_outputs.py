from __future__ import annotations

from common import (
    BANNED_PHRASES_PATH,
    DELIVERABLE_FIELDS,
    EDITORIAL_CONSTRAINTS_PATH,
    OUTPUT_PATH,
    REJECTED_COPY_PATH,
    SOURCE_INDEX_PATH,
    USED_IN_FIELDS,
    WORK_ORDER_PATH,
    allowed_source_refs,
    load_json,
    package_text,
    post_json,
    word_count,
)


def test_output_exists_and_top_level_contract_is_valid() -> None:
    payload = load_json(OUTPUT_PATH)
    work_order = load_json(WORK_ORDER_PATH)
    assert payload["campaign_id"] == work_order["campaign_id"]
    assert isinstance(payload["source_trace"], list) and len(payload["source_trace"]) >= 8
    assert isinstance(payload["fact_ledger"], list) and payload["fact_ledger"]
    assert isinstance(payload["revision_notes"], list) and payload["revision_notes"]
    assert isinstance(payload["quality_report"], dict)


def test_source_trace_covers_required_inputs_and_documents() -> None:
    payload = load_json(OUTPUT_PATH)
    allowed = allowed_source_refs()
    sources = [entry["source"] for entry in payload["source_trace"]]
    assert "/workspace/work_order.json" in sources
    assert "/workspace/drafts/rejected_copy.json" in sources
    assert any(source.endswith("/api/tone-examples") for source in sources)
    assert any(source.endswith("/api/editorial-constraints") for source in sources)
    assert any(source.endswith("/api/rejected-draft") for source in sources)
    doc_sources = [source for source in sources if "/api/document/" in source]
    assert len(set(doc_sources)) >= 4, "source_trace must include at least four document endpoints"
    for entry in payload["source_trace"]:
        assert entry["source"] in allowed
        assert entry["purpose"].strip()


def test_deliverables_have_required_shape_and_word_ranges() -> None:
    payload = load_json(OUTPUT_PATH)
    work_order = load_json(WORK_ORDER_PATH)
    deliverables = payload["deliverables"]

    for key, fields in DELIVERABLE_FIELDS.items():
        assert key in deliverables
        for field in fields:
            value = deliverables[key][field]
            assert isinstance(value, str) and value.strip(), f"{key}.{field} must be non-empty"

    hero = deliverables["homepage_hero"]
    hero_limits = work_order["word_limits"]["homepage_hero"]
    assert word_count(hero["headline"]) <= hero_limits["headline_max_words"]
    assert hero_limits["subheadline_min_words"] <= word_count(hero["subheadline"]) <= hero_limits["subheadline_max_words"]
    assert hero_limits["body_min_words"] <= word_count(hero["body"]) <= hero_limits["body_max_words"]

    feature_limits = work_order["word_limits"]["feature_page_section"]
    assert feature_limits["body_min_words"] <= word_count(deliverables["feature_page_section"]["body"]) <= feature_limits["body_max_words"]

    docs_limits = work_order["word_limits"]["docs_intro"]
    assert docs_limits["body_min_words"] <= word_count(deliverables["docs_intro"]["body"]) <= docs_limits["body_max_words"]

    release_limits = work_order["word_limits"]["release_note"]
    for field in ["what_changed", "how_it_works", "why_it_matters"]:
        count = word_count(deliverables["release_note"][field])
        assert release_limits["section_min_words"] <= count <= release_limits["section_max_words"]

    short_limits = work_order["word_limits"]["short_update"]
    assert short_limits["body_min_words"] <= word_count(deliverables["short_update"]["body"]) <= short_limits["body_max_words"]


def test_deliverables_cover_required_topics_without_generic_hype() -> None:
    payload = load_json(OUTPUT_PATH)
    text = package_text(payload).lower()
    banned = load_json(BANNED_PHRASES_PATH)["phrases"]
    constraints = load_json(EDITORIAL_CONSTRAINTS_PATH)

    assert "parallel agents" in text
    assert "threads sidebar" in text
    assert "codex" in text or "agent client protocol" in text or "acp" in text
    assert "open source" in text or "rust" in text or "gpu-accelerated" in text
    assert "worktree" in payload["deliverables"]["feature_page_section"]["body"].lower()
    docs_intro = payload["deliverables"]["docs_intro"]["body"].lower()
    assert "agent client protocol" in docs_intro or "acp" in docs_intro
    release_body = payload["deliverables"]["release_note"]["how_it_works"].lower()
    assert "context" in release_body
    assert "conversation history" in release_body
    for phrase in banned:
        assert phrase.lower() not in text
    for phrase in constraints["terms_to_avoid"]:
        assert phrase.lower() not in text


def test_fact_ledger_is_complete_and_grounded() -> None:
    payload = load_json(OUTPUT_PATH)
    work_order = load_json(WORK_ORDER_PATH)
    allowed = allowed_source_refs()
    ledger = payload["fact_ledger"]

    claim_ids = [entry["claim_id"] for entry in ledger]
    assert len(set(claim_ids)) == len(claim_ids), "claim_id values must be unique"
    for required_fact_id in work_order["required_fact_ids"]:
        assert required_fact_id in claim_ids, f"missing required fact id {required_fact_id}"

    doc_sources = set()
    used_in = set()
    for entry in ledger:
        assert entry["claim"].strip()
        assert entry["source"] in allowed
        if "/api/document/" in entry["source"]:
            doc_sources.add(entry["source"].split("#", 1)[0])
        assert isinstance(entry["used_in"], list) and entry["used_in"]
        for target in entry["used_in"]:
            assert target in USED_IN_FIELDS, f"unknown used_in target {target}"
            used_in.add(target)

    assert len(doc_sources) >= 4, "fact_ledger must draw from at least four source documents"
    assert len(used_in) >= 7, "fact_ledger must cover multiple deliverable fields"


def test_revision_notes_address_rejected_draft_failures() -> None:
    payload = load_json(OUTPUT_PATH)
    rejected = load_json(REJECTED_COPY_PATH)
    revision_blob = " ".join(
        f"{note['issue']} {note['change']}".lower() for note in payload["revision_notes"]
    )
    assert len(payload["revision_notes"]) >= 4
    assert "hype" in revision_blob or "superlative" in revision_blob
    assert "threads sidebar" in revision_blob
    assert "acp" in revision_blob or "codex" in revision_blob
    assert "source" in revision_blob or "ledger" in revision_blob
    assert len(rejected["rejection_reasons"]) >= 4


def test_quality_report_matches_service_validation() -> None:
    payload = load_json(OUTPUT_PATH)
    expected = post_json("/api/quality-gate", payload)
    quality_report = payload["quality_report"]
    assert quality_report == expected, "Embedded quality_report must match the live service validation response"
    assert set(quality_report["scorecard"]) == {
        "Technical Grounding",
        "Natural Syntax",
        "Quiet Confidence",
        "Developer Respect",
        "Information Priority",
        "Specificity",
        "Voice Consistency",
        "Earned Claims",
    }
    for score in quality_report["scorecard"].values():
        assert isinstance(score, int) and 4 <= score <= 5
    assert quality_report["banned_phrase_scan"] == []
    assert quality_report["final_gate"]["passed"] is True
    assert "passed" in quality_report["final_gate"]["details"].lower()


def test_output_does_not_reference_tests_or_placeholder_text() -> None:
    text = OUTPUT_PATH.read_text(encoding="utf-8").lower()
    assert "placeholder" not in text
    assert "todo" not in text
    assert "verifier" not in text
    assert "/tests" not in text
