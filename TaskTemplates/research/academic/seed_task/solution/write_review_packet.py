from __future__ import annotations

import csv
import json
import os
import unicodedata
from pathlib import Path


EXPECTED = {
    "2201.11903": {
        "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
        "decision": "include",
        "exclusion_reason": "in_scope",
        "short_citation": "Wei et al. (2022)",
        "reasoning_family": "cot",
        "prompting_mode": "few_shot",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "evaluation_domains": "arithmetic; commonsense; symbolic",
        "research_question": "Can a few chain-of-thought exemplars unlock stronger reasoning in large language models?",
        "method_summary": "Uses few-shot prompting with intermediate reasoning demonstrations before the final answer.",
        "benchmark_evidence": "Reports gains on arithmetic, commonsense, and symbolic reasoning, including GSM8K.",
        "main_claim": "Intermediate reasoning demonstrations can improve inference-time reasoning without changing model weights.",
        "supporting_text_snippet": "a few chain of thought demonstrations are provided as exemplars in prompting",
        "scope_anchor": "a few chain of thought demonstrations are provided as exemplars in prompting",
    },
    "2203.11171": {
        "title": "Self-Consistency Improves Chain of Thought Reasoning in Language Models",
        "decision": "include",
        "exclusion_reason": "in_scope",
        "short_citation": "Wang et al. (2022)",
        "reasoning_family": "self_consistency",
        "prompting_mode": "few_shot",
        "uses_sampling": "true",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "evaluation_domains": "arithmetic; commonsense",
        "research_question": "Does aggregating multiple reasoning paths improve chain-of-thought inference?",
        "method_summary": "Samples diverse reasoning paths and chooses the answer that is most consistent across them.",
        "benchmark_evidence": "Shows gains on StrategyQA, GSM8K, SVAMP, AQuA, and ARC-challenge.",
        "main_claim": "Inference improves when chain-of-thought decoding considers multiple candidate paths instead of a single greedy path.",
        "supporting_text_snippet": "It first samples a diverse set of reasoning paths instead of only taking the greedy one",
        "scope_anchor": "It first samples a diverse set of reasoning paths instead of only taking the greedy one",
    },
    "2203.14465": {
        "title": "STaR: Bootstrapping Reasoning With Reasoning",
        "decision": "exclude",
        "exclusion_reason": "requires_parameter_update",
        "scope_anchor": "fine-tune on all the rationales that ultimately yielded correct answers; repeat",
    },
    "2205.10625": {
        "title": "Least-to-Most Prompting Enables Complex Reasoning in Large Language Models",
        "decision": "include",
        "exclusion_reason": "in_scope",
        "short_citation": "Zhou et al. (2022)",
        "reasoning_family": "decomposition",
        "prompting_mode": "few_shot",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "evaluation_domains": "symbolic; compositional; math",
        "research_question": "Can decomposing a hard problem into simpler subproblems improve inference-time reasoning?",
        "method_summary": "Breaks a complex problem into simpler subproblems and solves them in sequence.",
        "benchmark_evidence": "Reports strong gains on SCAN, symbolic manipulation, compositional generalization, and math reasoning.",
        "main_claim": "Problem decomposition at inference time helps models solve harder tasks than the prompt exemplars alone support.",
        "supporting_text_snippet": "break down a complex problem into a series of simpler subproblems and then solve them in sequence",
        "scope_anchor": "break down a complex problem into a series of simpler subproblems and then solve them in sequence",
    },
    "2205.11916": {
        "title": "Large Language Models are Zero-Shot Reasoners",
        "decision": "include",
        "exclusion_reason": "in_scope",
        "short_citation": "Kojima et al. (2022)",
        "reasoning_family": "zero_shot_cot",
        "prompting_mode": "zero_shot",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "evaluation_domains": "arithmetic; symbolic; logical",
        "research_question": "Can a single zero-shot instruction elicit multi-step reasoning without demonstrations?",
        "method_summary": "Appends a step-by-step instruction to the prompt so the model produces reasoning without few-shot exemplars.",
        "benchmark_evidence": "The abstract highlights gains on MultiArith, GSM8K, AQUA-RAT, SVAMP, and logical reasoning tasks.",
        "main_claim": "A simple zero-shot step-by-step instruction can improve reasoning benchmarks without handcrafted examples.",
        "supporting_text_snippet": "by simply adding \"Let's think step by step\" before each answer",
        "scope_anchor": "by simply adding \"Let's think step by step\" before each answer",
    },
    "2210.03350": {
        "title": "Measuring and Narrowing the Compositionality Gap in Language Models",
        "decision": "include",
        "exclusion_reason": "in_scope",
        "short_citation": "Press et al. (2022)",
        "reasoning_family": "decomposition",
        "prompting_mode": "mixed",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "evaluation_domains": "multi-hop question answering; compositional reasoning",
        "research_question": "Can explicitly asking and answering sub-questions reduce the compositionality gap in language models?",
        "method_summary": "Measures compositional failures and introduces self-ask, where the model generates follow-up questions before answering.",
        "benchmark_evidence": "The abstract centers on multi-hop questions and shows that self-ask narrows the compositionality gap.",
        "main_claim": "Explicitly decomposing a question into follow-up questions can improve compositional reasoning beyond standard chain-of-thought prompting.",
        "supporting_text_snippet": "We present a new method, self-ask, that further improves on chain of thought",
        "scope_anchor": "We present a new method, self-ask, that further improves on chain of thought",
    },
    "2210.03493": {
        "title": "Automatic Chain of Thought Prompting in Large Language Models",
        "decision": "include",
        "exclusion_reason": "in_scope",
        "short_citation": "Zhang et al. (2022)",
        "reasoning_family": "automatic_demonstration",
        "prompting_mode": "mixed",
        "uses_sampling": "true",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "evaluation_domains": "reasoning benchmarks",
        "research_question": "Can chain-of-thought demonstrations be constructed automatically instead of by hand?",
        "method_summary": "Uses a step-by-step prompt to generate reasoning chains and automatically build demonstrations with diverse sampled questions.",
        "benchmark_evidence": "It reports results on ten public benchmark reasoning tasks with GPT-3.",
        "main_claim": "Automatic construction of demonstrations can recover much of the benefit of manual chain-of-thought prompting.",
        "supporting_text_snippet": "We propose an automatic CoT prompting method: Auto-CoT",
        "scope_anchor": "We propose an automatic CoT prompting method: Auto-CoT",
    },
    "2210.03629": {
        "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
        "decision": "exclude",
        "exclusion_reason": "tool_or_agent_orchestration",
        "scope_anchor": "actions allow it to interface with external sources, such as knowledge bases or environments",
    },
    "2211.10435": {
        "title": "PAL: Program-aided Language Models",
        "decision": "include",
        "exclusion_reason": "in_scope",
        "short_citation": "Gao et al. (2022)",
        "reasoning_family": "program_of_thought",
        "prompting_mode": "few_shot",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "true",
        "evaluation_domains": "math; symbolic; algorithmic",
        "research_question": "Can an interpreter handle the solution step more reliably than a language-only reasoning trace?",
        "method_summary": "Generates programs as intermediate reasoning steps and delegates execution to a Python interpreter.",
        "benchmark_evidence": "It reports results across 13 tasks from BIG-Bench Hard, GSM8K, and related reasoning settings.",
        "main_claim": "Offloading computation to an interpreter can improve reasoning accuracy when decomposition is still handled by the model.",
        "supporting_text_snippet": "generate programs as the intermediate reasoning steps, but offloads the solution step to a runtime such as a Python interpreter",
        "scope_anchor": "generate programs as the intermediate reasoning steps, but offloads the solution step to a runtime such as a Python interpreter",
    },
    "2211.12588": {
        "title": "Program of Thoughts Prompting: Disentangling Computation from Reasoning for Numerical Reasoning Tasks",
        "decision": "include",
        "exclusion_reason": "in_scope",
        "short_citation": "Chen et al. (2022)",
        "reasoning_family": "program_of_thought",
        "prompting_mode": "mixed",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "true",
        "evaluation_domains": "math; finance",
        "research_question": "Does moving computation into executable programs improve numerical reasoning at inference time?",
        "method_summary": "Represents reasoning as a program and lets an external computer execute the computation.",
        "benchmark_evidence": "It evaluates FinQA, ConvFinQA, TATQA, GSM, AQuA, SVAMP, TabMWP, and MultiArith.",
        "main_claim": "Separating computation from language-only reasoning can improve numerical reasoning benchmarks.",
        "supporting_text_snippet": "uses language models (mainly Codex) to express the reasoning process as a program",
        "scope_anchor": "uses language models (mainly Codex) to express the reasoning process as a program",
    },
    "2301.13379": {
        "title": "Faithful Chain-of-Thought Reasoning",
        "decision": "include",
        "exclusion_reason": "in_scope",
        "short_citation": "Lyu et al. (2023)",
        "reasoning_family": "program_of_thought",
        "prompting_mode": "few_shot",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "true",
        "evaluation_domains": "math; planning; multi-hop qa; relational inference",
        "research_question": "Can a symbolic solver make chain-of-thought traces more faithful while also improving accuracy?",
        "method_summary": "Translates the problem into a symbolic reasoning chain and uses a deterministic solver for the final answer.",
        "benchmark_evidence": "The abstract reports gains on 9 of 10 benchmarks across math word problems, planning, multi-hop QA, and relational inference.",
        "main_claim": "A faithful reasoning chain paired with a deterministic solver can improve both interpretability and benchmark performance.",
        "supporting_text_snippet": "a reasoning framework involving two stages: Translation (Natural Language query $\\rightarrow$ symbolic reasoning chain) and Problem Solving",
        "scope_anchor": "a reasoning framework involving two stages: Translation (Natural Language query $\\rightarrow$ symbolic reasoning chain) and Problem Solving",
    },
    "2302.04761": {
        "title": "Toolformer: Language Models Can Teach Themselves to Use Tools",
        "decision": "exclude",
        "exclusion_reason": "requires_parameter_update",
        "scope_anchor": "Toolformer, a model trained to decide which APIs to call, when to call them",
    },
    "2303.03103": {
        "title": "Towards Zero-Shot Functional Compositionality of Language Models",
        "decision": "exclude",
        "exclusion_reason": "outside_topic",
        "scope_anchor": "we suggest several research directions that could push the field towards zero-shot functional compositionality",
    },
    "2303.09014": {
        "title": "ART: Automatic multi-step reasoning and tool-use for large language models",
        "decision": "exclude",
        "exclusion_reason": "tool_or_agent_orchestration",
        "scope_anchor": "At test time, ART seamlessly pauses generation whenever external tools are called",
    },
    "2304.07919": {
        "title": "Chain of Thought Prompt Tuning in Vision Language Models",
        "decision": "exclude",
        "exclusion_reason": "outside_scope_modality",
        "scope_anchor": "we propose a novel chain of thought prompt tuning for vision-language modeling",
    },
    "2305.02317": {
        "title": "Visual Chain of Thought: Bridging Logical Gaps with Multimodal Infillings",
        "decision": "exclude",
        "exclusion_reason": "outside_scope_modality",
        "scope_anchor": "we introduce VCoT, a novel method that leverages chain-of-thought prompting with vision-language grounding",
    },
    "2305.04091": {
        "title": "Plan-and-Solve Prompting: Improving Zero-Shot Chain-of-Thought Reasoning by Large Language Models",
        "decision": "include",
        "exclusion_reason": "in_scope",
        "short_citation": "Wang et al. (2023b)",
        "reasoning_family": "decomposition",
        "prompting_mode": "zero_shot",
        "uses_sampling": "false",
        "uses_search_tree": "false",
        "uses_program_execution": "false",
        "evaluation_domains": "math; commonsense; symbolic",
        "research_question": "Can zero-shot reasoning improve if the model first writes a plan and then executes it?",
        "method_summary": "Splits zero-shot reasoning into a planning stage followed by stepwise execution of subtasks.",
        "benchmark_evidence": "It evaluates the method on ten datasets across three reasoning problems.",
        "main_claim": "Planning before solving reduces missing-step errors that remain in zero-shot chain-of-thought prompting.",
        "supporting_text_snippet": "first, devising a plan to divide the entire task into smaller subtasks, and then carrying out the subtasks according to the plan",
        "scope_anchor": "first, devising a plan to divide the entire task into smaller subtasks, and then carrying out the subtasks according to the plan",
    },
    "2305.10601": {
        "title": "Tree of Thoughts: Deliberate Problem Solving with Large Language Models",
        "decision": "include",
        "exclusion_reason": "in_scope",
        "short_citation": "Yao et al. (2023)",
        "reasoning_family": "tree_search",
        "prompting_mode": "mixed",
        "uses_sampling": "false",
        "uses_search_tree": "true",
        "uses_program_execution": "false",
        "evaluation_domains": "planning; creative writing; puzzles",
        "research_question": "Can search over multiple candidate thoughts improve inference-time problem solving?",
        "method_summary": "Generalizes chain-of-thought prompting into a tree search over coherent intermediate thoughts.",
        "benchmark_evidence": "The abstract highlights Game of 24, Creative Writing, and Mini Crosswords.",
        "main_claim": "Inference can benefit from deliberate search over multiple reasoning branches rather than a single left-to-right path.",
        "supporting_text_snippet": "enables exploration over coherent units of text (thoughts) that serve as intermediate steps toward problem solving",
        "scope_anchor": "enables exploration over coherent units of text (thoughts) that serve as intermediate steps toward problem solving",
    },
    "2307.02477": {
        "title": "Reasoning or Reciting? Exploring the Capabilities and Limitations of Language Models Through Counterfactual Tasks",
        "decision": "exclude",
        "exclusion_reason": "diagnostic_only",
        "scope_anchor": "we propose an evaluation framework based on \"counterfactual\" task variants",
    },
    "2307.15337": {
        "title": "Skeleton-of-Thought: Prompting LLMs for Efficient Parallel Generation",
        "decision": "exclude",
        "exclusion_reason": "outside_topic",
        "scope_anchor": "This work aims at decreasing the end-to-end generation latency of large language models",
    },
    "2308.09687": {
        "title": "Graph of Thoughts: Solving Elaborate Problems with Large Language Models",
        "decision": "include",
        "exclusion_reason": "in_scope",
        "short_citation": "Besta et al. (2023)",
        "reasoning_family": "graph_search",
        "prompting_mode": "mixed",
        "uses_sampling": "false",
        "uses_search_tree": "true",
        "uses_program_execution": "false",
        "evaluation_domains": "sorting; set operations; planning",
        "research_question": "Can graph-structured reasoning outperform linear or tree-structured thought organization?",
        "method_summary": "Models intermediate thoughts as graph vertices with explicit dependencies and feedback edges.",
        "benchmark_evidence": "The abstract reports better sorting quality and lower cost on sorting and related tasks.",
        "main_claim": "Allowing arbitrary graph structure over thoughts can improve quality and cost relative to tree-structured prompting baselines.",
        "supporting_text_snippet": "model the information generated by an LLM as an arbitrary graph, where units of information (\"LLM thoughts\") are vertices",
        "scope_anchor": "model the information generated by an LLM as an arbitrary graph, where units of information (\"LLM thoughts\") are vertices",
    },
}

THEME_MAP = {
    "themes": [
        {
            "theme_id": "theme_01",
            "label": "Prompted linear reasoning traces",
            "paper_ids": ["2201.11903", "2205.11916", "2210.03493"],
            "synthesis": "These papers keep reasoning in natural language and focus on how prompting alone can elicit or automate stronger stepwise traces at inference time.",
        },
        {
            "theme_id": "theme_02",
            "label": "Question decomposition before execution",
            "paper_ids": ["2205.10625", "2210.03350", "2305.04091"],
            "synthesis": "These methods improve reasoning by explicitly decomposing a problem into subquestions, subproblems, or plans before finishing the answer.",
        },
        {
            "theme_id": "theme_03",
            "label": "Executable or solver-backed reasoning",
            "paper_ids": ["2211.10435", "2211.12588", "2301.13379"],
            "synthesis": "These papers move part of the reasoning process into programs or symbolic solvers so the language model no longer performs all computation in free-form text.",
        },
        {
            "theme_id": "theme_04",
            "label": "Extra inference-time search over alternatives",
            "paper_ids": ["2203.11171", "2305.10601"],
            "synthesis": "Both methods spend additional inference-time compute on alternatives, either by sampling many reasoning paths or by explicitly searching over thought branches.",
        },
        {
            "theme_id": "theme_05",
            "label": "Graph-structured reasoning state",
            "paper_ids": ["2308.09687"],
            "synthesis": "Graph of Thoughts extends beyond linear and tree-structured reasoning by allowing arbitrary dependencies and feedback loops between intermediate thoughts.",
        },
    ],
    "research_gaps": [
        {
            "gap_id": "gap_01",
            "label": "Cost-quality tradeoffs remain unsettled",
            "evidence_paper_ids": ["2203.11171", "2305.10601", "2308.09687"],
            "why_it_remains_open": "The bundled papers show that extra inference-time search can improve answers, but they do not settle how much additional compute is justified across broader task distributions.",
        },
        {
            "gap_id": "gap_02",
            "label": "Boundary between reasoning and delegated execution",
            "evidence_paper_ids": ["2211.10435", "2211.12588", "2301.13379"],
            "why_it_remains_open": "Program-backed methods improve reliability, yet the packet still leaves open how much of a solution should stay inside the language model versus move to an interpreter or solver.",
        },
        {
            "gap_id": "gap_03",
            "label": "Transfer beyond the benchmark mixes in the abstracts",
            "evidence_paper_ids": ["2201.11903", "2205.11916", "2210.03493", "2305.04091"],
            "why_it_remains_open": "Many abstracts report gains on familiar benchmark suites, but they say less about robustness under shifted tasks or different evaluation settings.",
        },
    ],
    "disagreements": [
        {
            "label": "Single-trace prompting versus explicit search",
            "paper_ids": ["2201.11903", "2203.11171", "2305.10601", "2308.09687"],
            "synthesis": "The packet reveals a design split between methods that refine one reasoning trace and methods that spend more compute exploring multiple candidates before choosing an answer.",
        },
        {
            "label": "Language-only reasoning versus executable reasoning",
            "paper_ids": ["2201.11903", "2211.10435", "2211.12588", "2301.13379"],
            "synthesis": "Some methods keep every intermediate step in text, while PAL, Program of Thoughts, and Faithful CoT move important parts of the reasoning workflow into executable or symbolic machinery.",
        },
    ],
}


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _load_manifest(data_dir: Path) -> dict[str, dict]:
    manifest_path = data_dir / "metadata" / "paper_manifest.json"
    records = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {record["paper_id"]: record for record in records}


def _load_snapshot(data_dir: Path, paper_id: str) -> str:
    return (data_dir / "text" / f"{paper_id}.md").read_text(encoding="utf-8")


def _write_tsv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _make_bib_entry(record: dict, key: str) -> str:
    authors = " and ".join(_ascii(author) for author in record["authors"])
    title = _ascii(record["title"])
    year = record["year"]
    url = record["abs_url"]
    return (
        f"@article{{{key},\n"
        f"  title = {{{title}}},\n"
        f"  author = {{{authors}}},\n"
        f"  year = {{{year}}},\n"
        f"  journal = {{arXiv preprint arXiv:{record['paper_id']}}},\n"
        f"  url = {{{url}}}\n"
        f"}}\n"
    )


def main() -> None:
    data_dir = Path(os.environ.get("DATA_DIR", Path.cwd().joinpath("environment", "data")))
    if not data_dir.exists():
        data_dir = Path("/root/environment/data")
    answer_dir = Path(os.environ.get("ANSWER_DIR", "/root/answer"))
    try:
        answer_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        answer_dir = Path.cwd() / "answer"
        answer_dir.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest(data_dir)
    screening_rows = []
    included_rows = []
    evidence_rows = []
    included_ids = []

    for paper_id in sorted(EXPECTED):
        record = EXPECTED[paper_id]
        screening_rows.append(
            {
                "paper_id": paper_id,
                "title": record["title"],
                "decision": record["decision"],
                "exclusion_reason": record["exclusion_reason"],
                "citation_source": f"arxiv_id_feed.xml::{paper_id}",
                "scope_anchor": record["scope_anchor"],
            }
        )
        if record["decision"] != "include":
            continue

        included_ids.append(paper_id)
        included_rows.append(
            {
                "paper_id": paper_id,
                "short_citation": record["short_citation"],
                "year": manifest[paper_id]["year"],
                "reasoning_family": record["reasoning_family"],
                "prompting_mode": record["prompting_mode"],
                "uses_sampling": record["uses_sampling"],
                "uses_search_tree": record["uses_search_tree"],
                "uses_program_execution": record["uses_program_execution"],
                "evaluation_domains": record["evaluation_domains"],
            }
        )

        snapshot = _load_snapshot(data_dir, paper_id)
        snippet = record["supporting_text_snippet"]
        if snippet not in snapshot:
            raise ValueError(f"snippet missing from snapshot for {paper_id}")
        evidence_rows.append(
            {
                "paper_id": paper_id,
                "research_question": record["research_question"],
                "method_summary": record["method_summary"],
                "benchmark_evidence": record["benchmark_evidence"],
                "main_claim": record["main_claim"],
                "supporting_text_snippet": snippet,
            }
        )

    _write_tsv(
        answer_dir / "screening_decisions.tsv",
        ["paper_id", "title", "decision", "exclusion_reason", "citation_source", "scope_anchor"],
        screening_rows,
    )
    _write_tsv(
        answer_dir / "included_papers.tsv",
        [
            "paper_id",
            "short_citation",
            "year",
            "reasoning_family",
            "prompting_mode",
            "uses_sampling",
            "uses_search_tree",
            "uses_program_execution",
            "evaluation_domains",
        ],
        included_rows,
    )
    _write_tsv(
        answer_dir / "evidence_table.tsv",
        [
            "paper_id",
            "research_question",
            "method_summary",
            "benchmark_evidence",
            "main_claim",
            "supporting_text_snippet",
        ],
        evidence_rows,
    )

    family_counts: dict[str, int] = {}
    for row in included_rows:
        family_counts[row["reasoning_family"]] = family_counts.get(row["reasoning_family"], 0) + 1

    exclusion_counts: dict[str, int] = {}
    for row in screening_rows:
        if row["decision"] == "exclude":
            key = row["exclusion_reason"]
            exclusion_counts[key] = exclusion_counts.get(key, 0) + 1

    review_summary = {
        "topic": "inference-time reasoning methods for text-only language models",
        "n_candidates": len(screening_rows),
        "n_included": len(included_rows),
        "n_excluded": len(screening_rows) - len(included_rows),
        "included_paper_ids": included_ids,
        "reasoning_family_counts": family_counts,
        "exclusion_counts": exclusion_counts,
        "notes": (
            "The packet corrects several misleading draft triage entries and keeps scope decisions, evidence anchors, "
            "and citation metadata aligned across the bundled corpus."
        ),
    }

    review_lines = [
        "# Literature Review",
        "",
        "## Review Question",
        "How do recent text-only inference-time reasoning methods differ in the way they elicit, structure, or search over intermediate reasoning steps?",
        "",
        "## Scope and Selection",
        "The packet screens 21 candidate papers against the bundled scope rules and retains 12 papers whose main contribution changes reasoning behavior at inference time for text-only language models. Excluded papers fall into multimodal settings, parameter-update methods, tool or agent orchestration, diagnostic studies, or adjacent topics that are not direct reasoning-method comparisons.",
        "",
        "## Method Families",
        "The included set spans prompted natural-language traces, explicit decomposition strategies, executable reasoning pipelines, and broader search over alternative intermediate states. Zero-shot CoT and Auto-CoT extend prompt design, decomposition papers emphasize plan structure, and PAL, Program of Thoughts, and Faithful CoT move important steps into programs or symbolic solvers.",
        "",
        "## Cross-Paper Synthesis",
        "A first throughline is that stronger reasoning often comes from adding structure before the final answer is emitted, whether through demonstrations, plans, follow-up questions, or graph-structured state. A second is that some methods spend extra inference-time compute on alternatives, while others redirect computation into executable machinery to reduce arithmetic or logical failure modes. The packet also shows a widening contrast between single-trace prompting methods and search-based methods that explicitly evaluate multiple candidates before committing.",
        "",
        "## Research Gaps",
        "The bundled abstracts leave open how well these methods transfer outside their benchmark mixes, what compute budget is justified for broader search, and where the boundary should sit between language-only reasoning and delegated execution. Those gaps matter because most gains are reported on curated reasoning datasets rather than on shared out-of-distribution stress tests.",
        "",
        "## References",
    ]
    for paper_id in included_ids:
        record = EXPECTED[paper_id]
        review_lines.append(f"- {record['short_citation']}. {record['title']}.")
    (answer_dir / "literature_review.md").write_text("\n".join(review_lines) + "\n", encoding="utf-8")

    (answer_dir / "theme_map.json").write_text(
        json.dumps(THEME_MAP, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (answer_dir / "review_summary.json").write_text(
        json.dumps(review_summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    bib_entries = []
    for paper_id in included_ids:
        manifest_record = manifest[paper_id]
        key = f"{manifest_record['authors'][0].split()[-1].lower()}{manifest_record['year']}{paper_id[-4:]}"
        bib_entries.append(_make_bib_entry({**manifest_record, "paper_id": paper_id}, key))
    (answer_dir / "references.bib").write_text("\n".join(bib_entries), encoding="utf-8")


if __name__ == "__main__":
    main()
