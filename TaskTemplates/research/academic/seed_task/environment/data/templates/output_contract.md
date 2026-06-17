# Output Contract

The final packet must contain:
- `screening_decisions.tsv`
- `included_papers.tsv`
- `evidence_table.tsv`
- `theme_map.json`
- `literature_review.md`
- `review_summary.json`
- `references.bib`

Use the local abstract snapshots and the scope document as the source material for all decisions and claims.
Keep screening decisions, included-paper metadata, evidence snippets, citations, and bibliography entries internally consistent.
Copy `scope_anchor` and `supporting_text_snippet` as short verbatim substrings from the bundled paper text.
Use `few_shot`, `zero_shot`, or `mixed` for `prompting_mode`.
Have `benchmark_evidence` name at least one benchmark, task, or evaluation setting mentioned in the bundled paper text.
Use this `theme_map.json` shape:
- `themes`: objects with `label`, `paper_ids`, `synthesis`
- `research_gaps`: objects with `label`, `evidence_paper_ids`, `why_it_remains_open`
- `disagreements`: objects with `label`, `paper_ids`, `synthesis`
