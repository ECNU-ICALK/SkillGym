from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ANSWER_DIR = Path(__import__("os").environ.get("ANSWER_DIR", "/root/answer"))
DATA_DIR = Path(__import__("os").environ.get("DATA_DIR", "/root/environment/data"))

EXPECTED_INCLUDES = {
    "2201.11903",
    "2203.11171",
    "2205.10625",
    "2205.11916",
    "2210.03350",
    "2210.03493",
    "2211.10435",
    "2211.12588",
    "2301.13379",
    "2305.04091",
    "2305.10601",
    "2308.09687",
}
EXPECTED_EXCLUDES = {
    "2203.14465",
    "2210.03629",
    "2302.04761",
    "2303.03103",
    "2303.09014",
    "2304.07919",
    "2305.02317",
    "2307.02477",
    "2307.15337",
}
EXPECTED_TITLES_INCLUDED = {
    "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
    "Self-Consistency Improves Chain of Thought Reasoning in Language Models",
    "Large Language Models are Zero-Shot Reasoners",
    "Least-to-Most Prompting Enables Complex Reasoning in Large Language Models",
    "Measuring and Narrowing the Compositionality Gap in Language Models",
    "Automatic Chain of Thought Prompting in Large Language Models",
    "PAL: Program-aided Language Models",
    "Program of Thoughts Prompting: Disentangling Computation from Reasoning for Numerical Reasoning Tasks",
    "Faithful Chain-of-Thought Reasoning",
    "Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning by Large Language Models",
    "Tree of Thoughts: Deliberate Problem Solving with Large Language Models",
    "Graph of Thoughts: Solving Elaborate Problems with Large Language Models",
}
EXPECTED_TITLES_EXCLUDED = {
    "STaR: Bootstrapping Reasoning With Reasoning",
    "ReAct: Synergizing Reasoning and Acting in Language Models",
    "Toolformer: Language Models Can Teach Themselves to Use Tools",
    "Towards Zero-Shot Functional Compositionality of Language Models",
    "ART: Automatic multi-step reasoning and tool-use for large language models",
    "Chain of Thought Prompt Tuning in Vision Language Models",
    "Visual Chain of Thought: Bridging Logical Gaps with Multimodal Infillings",
    "Reasoning or Reciting? Exploring the Capabilities and Limitations of Language Models Through Counterfactual Tasks",
    "Skeleton-of-Thought: Prompting LLMs for Efficient Parallel Generation",
}


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_theme_map_uses_only_included_ids_and_covers_all_of_them_once():
    payload = json.loads((ANSWER_DIR / "theme_map.json").read_text(encoding="utf-8"))
    assert set(payload) == {"themes", "research_gaps", "disagreements"}
    assert 3 <= len(payload["themes"]) <= 7

    themed_ids = []
    for item in payload["themes"]:
        label = item.get("label") or item.get("theme_id") or item.get("name") or ""
        assert label.strip()
        assert 1 <= len(item["paper_ids"]) <= 6
        assert set(item["paper_ids"]).issubset(EXPECTED_INCLUDES)
        assert len(item["synthesis"].strip()) >= 40
        themed_ids.extend(item["paper_ids"])

    assert set(themed_ids) == EXPECTED_INCLUDES

    for item in payload["research_gaps"]:
        ids = item.get("evidence_paper_ids") or item.get("paper_ids") or []
        assert set(ids).issubset(EXPECTED_INCLUDES)
        assert len(item["why_it_remains_open"].strip()) >= 40
    assert len(payload["research_gaps"]) >= 2

    for item in payload["disagreements"]:
        assert set(item["paper_ids"]).issubset(EXPECTED_INCLUDES)
        text = item.get("synthesis") or item.get("summary") or ""
        assert len(text.strip()) >= 40
    assert len(payload["disagreements"]) >= 2


def test_review_has_required_sections_and_mentions_every_included_paper():
    review_text = (ANSWER_DIR / "literature_review.md").read_text(encoding="utf-8")
    for section in [
        "## Review Question",
        "## Scope and Selection",
        "## Method Families",
        "## Cross-Paper Synthesis",
        "## Research Gaps",
        "## References",
    ]:
        assert section in review_text

    expected_traces = {
        "2201.11903": ["Wei et al. (2022)"],
        "2203.11171": ["Wang et al. (2022)"],
        "2205.11916": ["Kojima et al. (2022)"],
        "2205.10625": ["Zhou et al. (2022)"],
        "2210.03350": ["Press et al. (2022)"],
        "2210.03493": ["Zhang et al. (2022)"],
        "2211.10435": ["Gao et al. (2022)"],
        "2211.12588": ["Chen et al. (2022)"],
        "2301.13379": ["Lyu et al. (2023)"],
        "2305.04091": ["Wang et al. (2023b)", "Plan-and-Solve Prompting", "Wang et al. (2023)"],
        "2305.10601": ["Yao et al. (2023)"],
        "2308.09687": ["Besta et al. (2023)"],
    }
    for paper_id, markers in expected_traces.items():
        assert paper_id in review_text or any(marker in review_text for marker in markers)


def test_references_only_contain_included_papers():
    bib_text = (ANSWER_DIR / "references.bib").read_text(encoding="utf-8")
    keys = set(re.findall(r"@\w+\{([^,]+),", bib_text))
    assert len(keys) == len(EXPECTED_INCLUDES)
    for title in EXPECTED_TITLES_INCLUDED:
        assert title in bib_text
    for title in EXPECTED_TITLES_EXCLUDED:
        assert title not in bib_text
    for paper_id in EXPECTED_EXCLUDES:
        assert paper_id not in bib_text


def test_cross_file_consistency_between_screening_included_and_evidence():
    screening = _read_tsv(ANSWER_DIR / "screening_decisions.tsv")
    included = _read_tsv(ANSWER_DIR / "included_papers.tsv")
    evidence = _read_tsv(ANSWER_DIR / "evidence_table.tsv")
    screening_included_ids = {row["paper_id"] for row in screening if row["decision"] == "include"}
    included_ids = {row["paper_id"] for row in included}
    evidence_ids = {row["paper_id"] for row in evidence}
    assert screening_included_ids == included_ids == evidence_ids == EXPECTED_INCLUDES


def test_known_legacy_mistakes_are_corrected():
    screening_rows = {row["paper_id"]: row for row in _read_tsv(ANSWER_DIR / "screening_decisions.tsv")}
    legacy_rows = {
        row["paper_id"]: row
        for row in _read_tsv(DATA_DIR / "metadata" / "legacy_screening_notes.tsv")
    }

    for paper_id in [
        "2205.11916",
        "2210.03350",
        "2211.10435",
        "2301.13379",
        "2303.03103",
        "2307.15337",
        "2210.03629",
    ]:
        assert screening_rows[paper_id]["decision"] != legacy_rows[paper_id]["legacy_decision"]

    included_rows = {row["paper_id"]: row for row in _read_tsv(ANSWER_DIR / "included_papers.tsv")}
    assert included_rows["2305.04091"]["reasoning_family"] != "zero_shot_cot"
    assert included_rows["2308.09687"]["reasoning_family"] != "tree_search"
