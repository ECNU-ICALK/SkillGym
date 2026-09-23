You are preparing a compact review packet about inference-time reasoning methods for text-only language models.

Input data is in:
- `/root/environment/data/metadata/arxiv_id_feed.xml`
- `/root/environment/data/metadata/candidate_manifest.tsv`
- `/root/environment/data/metadata/legacy_screening_notes.tsv`
- `/root/environment/data/text/`
- `/root/environment/data/scope/review_scope.md`
- `/root/environment/data/templates/output_contract.md`

Your tasks
1. Produce the complete review packet for the bundled candidate set.
2. Use the scope document and bundled paper text to decide which papers belong in the packet.
3. Keep screening decisions, evidence anchors, summary counts, citations, and bibliography entries internally consistent.

Outputs:
- `/root/answer/screening_decisions.tsv`
  - One row per candidate paper
  - Columns: `paper_id`, `title`, `decision`, `exclusion_reason`, `citation_source`, `scope_anchor`
  - `decision` must be `include` or `exclude`
  - `exclusion_reason` must be one of: `in_scope`, `outside_scope_modality`, `requires_parameter_update`, `tool_or_agent_orchestration`, `diagnostic_only`, `outside_topic`
  - `scope_anchor` should be a short verbatim quote copied from the bundled paper text

- `/root/answer/included_papers.tsv`
  - One row per included paper
  - Columns: `paper_id`, `short_citation`, `year`, `reasoning_family`, `prompting_mode`, `uses_sampling`, `uses_search_tree`, `uses_program_execution`, `evaluation_domains`
  - `prompting_mode` should use `few_shot`, `zero_shot`, or `mixed`

- `/root/answer/evidence_table.tsv`
  - One row per included paper
  - Columns: `paper_id`, `research_question`, `method_summary`, `benchmark_evidence`, `main_claim`, `supporting_text_snippet`
  - `benchmark_evidence` should name at least one benchmark, task, or evaluation setting mentioned in the bundled paper text
  - `supporting_text_snippet` should be a short verbatim quote copied from the bundled paper text

- `/root/answer/theme_map.json`
  - Top-level keys: `themes`, `research_gaps`, `disagreements`
  - `themes`: list of objects with `label`, `paper_ids`, `synthesis`
  - `research_gaps`: list of objects with `label`, `evidence_paper_ids`, `why_it_remains_open`
  - `disagreements`: list of objects with `label`, `paper_ids`, `synthesis`

- `/root/answer/literature_review.md`
  - Must include sections: `## Review Question`, `## Scope and Selection`, `## Method Families`, `## Cross-Paper Synthesis`, `## Research Gaps`, `## References`

- `/root/answer/review_summary.json`
  - Keys: `topic`, `n_candidates`, `n_included`, `n_excluded`, `included_paper_ids`, `reasoning_family_counts`, `exclusion_counts`, `notes`

- `/root/answer/references.bib`
  - One BibTeX entry for each included paper

Notes:
- Use only the bundled data for screening, extraction, and writing.
- Keep paper IDs and citations aligned across files.
- Do not add papers that are not in the candidate manifest.
- Do not invent scope anchors, evidence snippets, benchmark claims, or citation entries.
