from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ANSWER_DIR = Path(__import__("os").environ.get("ANSWER_DIR", "/root/answer"))
DATA_DIR = Path(__import__("os").environ.get("DATA_DIR", "/root/environment/data"))

EXPECTED = {
    "2201.11903": {
        "decision": "include",
        "exclusion_reason": "in_scope",
        "family": "cot",
        "prompting_mode": "few_shot",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "year": "2022",
        "benchmark_token": "GSM8K",
    },
    "2203.11171": {
        "decision": "include",
        "exclusion_reason": "in_scope",
        "family": "self_consistency",
        "prompting_mode": "few_shot",
        "uses_sampling": "true",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "year": "2022",
        "benchmark_token": "StrategyQA",
    },
    "2203.14465": {
        "decision": "exclude",
        "exclusion_reason": "requires_parameter_update",
    },
    "2205.10625": {
        "decision": "include",
        "exclusion_reason": "in_scope",
        "family": "decomposition",
        "prompting_mode": "few_shot",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "year": "2022",
        "benchmark_token": "SCAN",
    },
    "2205.11916": {
        "decision": "include",
        "exclusion_reason": "in_scope",
        "family": "zero_shot_cot",
        "prompting_mode": "zero_shot",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "year": "2022",
        "benchmark_token": "MultiArith",
    },
    "2210.03350": {
        "decision": "include",
        "exclusion_reason": "in_scope",
        "family": "decomposition",
        "prompting_mode": "mixed",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "year": "2022",
        "benchmark_token": "multi-hop questions",
    },
    "2210.03493": {
        "decision": "include",
        "exclusion_reason": "in_scope",
        "family": "automatic_demonstration",
        "prompting_mode": "mixed",
        "uses_sampling": "true",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "year": "2022",
        "benchmark_token": "ten public benchmark reasoning tasks",
    },
    "2210.03629": {
        "decision": "exclude",
        "exclusion_reason": "tool_or_agent_orchestration",
    },
    "2211.10435": {
        "decision": "include",
        "exclusion_reason": "in_scope",
        "family": "program_of_thought",
        "prompting_mode": "few_shot",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "true",
        "year": "2022",
        "benchmark_token": "BIG-Bench Hard",
    },
    "2211.12588": {
        "decision": "include",
        "exclusion_reason": "in_scope",
        "family": "program_of_thought",
        "prompting_mode": "mixed",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "true",
        "year": "2022",
        "benchmark_token": "FinQA",
    },
    "2301.13379": {
        "decision": "include",
        "exclusion_reason": "in_scope",
        "family": "program_of_thought",
        "prompting_mode": "few_shot",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "true",
        "year": "2023",
        "benchmark_token": "9 of 10 benchmarks",
    },
    "2302.04761": {
        "decision": "exclude",
        "exclusion_reason": "requires_parameter_update",
    },
    "2303.03103": {
        "decision": "exclude",
        "exclusion_reason": "outside_topic",
    },
    "2303.09014": {
        "decision": "exclude",
        "exclusion_reason": "tool_or_agent_orchestration",
    },
    "2304.07919": {
        "decision": "exclude",
        "exclusion_reason": "outside_scope_modality",
    },
    "2305.02317": {
        "decision": "exclude",
        "exclusion_reason": "outside_scope_modality",
    },
    "2305.04091": {
        "decision": "include",
        "exclusion_reason": "in_scope",
        "family": "decomposition",
        "prompting_mode": "zero_shot",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "year": "2023",
        "benchmark_token": "ten datasets",
    },
    "2305.10601": {
        "decision": "include",
        "exclusion_reason": "in_scope",
        "family": "tree_search",
        "prompting_mode": "mixed",
        "uses_sampling": "false",
        "uses_search_tree": "true",
        "uses_program_execution": "false",
        "year": "2023",
        "benchmark_token": "Game of 24",
    },
    "2307.02477": {
        "decision": "exclude",
        "exclusion_reason": "diagnostic_only",
    },
    "2307.15337": {
        "decision": "exclude",
        "exclusion_reason": "outside_topic",
    },
    "2308.09687": {
        "decision": "include",
        "exclusion_reason": "in_scope",
        "family": "graph_search",
        "prompting_mode": "mixed",
        "uses_sampling": "false",
        "uses_search_tree": "true",
        "uses_program_execution": "false",
        "year": "2023",
        "benchmark_token": "sorting",
    },
}


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _normalize_for_grounding(text: str) -> str:
    text = text.replace("\\%", "%")
    text = text.replace("\\", "")
    for token in ['"', "'", "`", "“", "”", "’", ".", ",", ":", ";", "!", "?", "(", ")", "[", "]", "{", "}"]:
        text = text.replace(token, "")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _normalize_bool(text: str) -> str:
    value = text.strip().lower()
    mapping = {
        "true": "true",
        "yes": "true",
        "1": "true",
        "false": "false",
        "no": "false",
        "0": "false",
    }
    return mapping[value]


def test_expected_files_exist():
    for name in [
        "screening_decisions.tsv",
        "included_papers.tsv",
        "evidence_table.tsv",
        "theme_map.json",
        "literature_review.md",
        "review_summary.json",
        "references.bib",
    ]:
        assert (ANSWER_DIR / name).exists(), name


def test_screening_decisions_are_complete_and_grounded():
    rows = _read_tsv(ANSWER_DIR / "screening_decisions.tsv")
    assert len(rows) == len(EXPECTED)
    seen = {}
    for row in rows:
        paper_id = row["paper_id"]
        assert paper_id in EXPECTED
        assert paper_id not in seen
        seen[paper_id] = row
        assert row["decision"] == EXPECTED[paper_id]["decision"]
        if paper_id == "2303.03103":
            assert row["exclusion_reason"] in {"outside_topic", "diagnostic_only"}
        else:
            assert row["exclusion_reason"] == EXPECTED[paper_id]["exclusion_reason"]
        assert row["citation_source"] == f"arxiv_id_feed.xml::{paper_id}"
        assert len(row["scope_anchor"].strip()) >= 20
        snapshot = (DATA_DIR / "text" / f"{paper_id}.md").read_text(encoding="utf-8")
        assert _normalize_for_grounding(row["scope_anchor"]) in _normalize_for_grounding(snapshot)
    assert set(seen) == set(EXPECTED)


def test_included_papers_match_expected_core_classification():
    rows = _read_tsv(ANSWER_DIR / "included_papers.tsv")
    expected_included = {paper_id for paper_id, meta in EXPECTED.items() if meta["decision"] == "include"}
    assert len(rows) == len(expected_included)
    seen_ids = set()
    for row in rows:
        paper_id = row["paper_id"]
        seen_ids.add(paper_id)
        meta = EXPECTED[paper_id]
        assert meta["decision"] == "include"
        assert row["reasoning_family"] == meta["family"]
        assert row["prompting_mode"] in {"few_shot", "zero_shot", "mixed"}
        assert _normalize_bool(row["uses_sampling"]) in {"true", "false"}
        assert _normalize_bool(row["uses_search_tree"]) in {"true", "false"}
        assert _normalize_bool(row["uses_program_execution"]) == meta["uses_program_execution"]
        assert row["year"] == meta["year"]
        assert row["short_citation"].strip()
        assert row["evaluation_domains"].strip()
    assert seen_ids == expected_included


def test_evidence_rows_are_grounded_and_benchmark_specific():
    rows = _read_tsv(ANSWER_DIR / "evidence_table.tsv")
    expected_included = {paper_id for paper_id, meta in EXPECTED.items() if meta["decision"] == "include"}
    assert len(rows) == len(expected_included)
    for row in rows:
        paper_id = row["paper_id"]
        meta = EXPECTED[paper_id]
        assert paper_id in expected_included
        for key in ["research_question", "method_summary", "main_claim"]:
            assert len(row[key].strip()) >= 20
        assert len(row["benchmark_evidence"].strip()) >= 7
        snapshot = (DATA_DIR / "text" / f"{paper_id}.md").read_text(encoding="utf-8")
        assert _normalize_for_grounding(row["supporting_text_snippet"]) in _normalize_for_grounding(snapshot)


def test_summary_counts_and_ids_align():
    payload = json.loads((ANSWER_DIR / "review_summary.json").read_text(encoding="utf-8"))
    expected_included = sorted(
        paper_id for paper_id, meta in EXPECTED.items() if meta["decision"] == "include"
    )
    assert payload["topic"].strip().lower() == "inference-time reasoning methods for text-only language models"
    assert payload["n_candidates"] == 21
    assert payload["n_included"] == 12
    assert payload["n_excluded"] == 9
    assert payload["included_paper_ids"] == expected_included
    assert payload["reasoning_family_counts"] == {
        "cot": 1,
        "zero_shot_cot": 1,
        "self_consistency": 1,
        "decomposition": 3,
        "automatic_demonstration": 1,
        "program_of_thought": 3,
        "tree_search": 1,
        "graph_search": 1,
    }
    assert payload["exclusion_counts"] in [
        {
            "outside_scope_modality": 2,
            "requires_parameter_update": 2,
            "tool_or_agent_orchestration": 2,
            "diagnostic_only": 1,
            "outside_topic": 2,
        },
        {
            "outside_scope_modality": 2,
            "requires_parameter_update": 2,
            "tool_or_agent_orchestration": 2,
            "diagnostic_only": 2,
            "outside_topic": 1,
        },
    ]
    notes = payload["notes"]
    if isinstance(notes, list):
        assert notes
        assert all(str(item).strip() for item in notes)
    else:
        assert len(str(notes).strip()) >= 40
