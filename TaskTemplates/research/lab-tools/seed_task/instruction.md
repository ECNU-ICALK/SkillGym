You need to prepare a reproducible Jupyter notebook package for an EGFR bioactivity review and a compact scenario comparison.

Input data is under `/root/data/`:

- `screening_contract.json`: review scope, selection rules, and output contract.
- `egfr_activity_snapshot.json`: ChEMBL activity records for target `CHEMBL203`.
- `egfr_assay_snapshot.json`: ChEMBL assay metadata for the same target.
- `egfr_target_snapshot.json`: ChEMBL target metadata.
- `egfr_molecule_snapshot.json`: ChEMBL molecule metadata for compounds referenced by the activity snapshot.
- `legacy_shortlist.csv`: a prior export for context only; it may be incomplete or stale.

Your task

1. Build a runnable notebook that completes the current EGFR bioactivity review from the provided snapshots and documents the review flow in compact, stepwise notebook cells.
2. Produce a baseline candidate panel, a QC summary, a filter audit, a scenario comparison, a candidate trace, and a short written brief that all stay aligned with the screening contract and the notebook output.

Output

If `/root/output/` does not exist, create it first.

1. Write `/root/output/egfr_bioactivity_review.ipynb`
   - The notebook must be valid JSON and runnable from top to bottom in the container.
   - It must include the headings `# Goal`, `# Inputs`, and `# Results` in this order.
   - It should also include a short planning section titled `## Plan` and a short follow-up section titled `## Follow-up`.
   - The planning section should state a hypothesis, the main variables, and the metrics you will inspect.
   - Keep the notebook workflow stepwise: use separate executable cells for setup, source loading and profiling, filter auditing, scenario comparison, baseline candidate ranking and export, and result review.
   - The notebook must render the review plot topic defined in `screening_contract.json`, save it as `/root/output/top_candidate_best_ic50_nm.png`, and write any generated review files into `/root/output/`.
   - If the CSV, JSON, Markdown, or plot deliverables are removed and the notebook is rerun, it must recreate them in `/root/output/`.

2. Write `/root/output/candidate_panel.csv`
   - Columns must be exactly:
     `rank,molecule_chembl_id,pref_name,n_qualifying_measurements,n_distinct_assays,best_ic50_nM,median_ic50_nM,best_pchembl,max_assay_confidence_score,selection_reason`
   - One row per selected compound.
   - All rows must be derived from the current snapshots and the baseline rules in `screening_contract.json`.

3. Write `/root/output/qc_summary.json`
   - Top-level keys must be exactly:
     `target_chembl_id`, `target_name`, `activity_rows_loaded`, `activity_rows_after_filters`, `assay_rows_used`, `molecules_ranked`, `candidate_rows`
   - Values must reflect the baseline review workflow.

4. Write `/root/output/review_brief.md`
   - It must include these headings in this exact order:
     `# Scope`
     `# Data Quality`
     `# Candidate Panel`
     `# Follow-up Notes`
   - The brief must be consistent with the notebook, the candidate panel, the QC summary, the scenario comparison, and the candidate trace.
   - The brief must mention the baseline top candidates, summarize the baseline/strict/relaxed scenario comparison, and include at least one `triggered_selection_rule` label taken from `candidate_trace.json`.
   - The brief must also state that `legacy_shortlist.csv` was treated as context only and did not define the current baseline panel.

5. Write `/root/output/scenario_comparison.csv`
   - Columns must be exactly:
     `scenario_id,minimum_confidence_score,minimum_distinct_assays,qualifying_rows,eligible_molecules,panel_size,top_3_ids`
   - Include these scenario IDs:
     `baseline_contract`
     `strict_confidence`
     `relaxed_assay_support`
   - Build `strict_confidence` by increasing the current contract `minimum_confidence_score` by `1`.
   - Build `relaxed_assay_support` by decreasing the current contract `minimum_distinct_assays` by `1`, but not below `1`.
   - `panel_size` should report how many rows are actually emitted for that scenario after ranking and truncation.
   - `top_3_ids` should be a semicolon-delimited list of the top three molecule IDs for that scenario.
   - The final candidate panel, QC summary, trace, brief, and plot must still reflect the baseline contract.

6. Write `/root/output/candidate_trace.json`
   - Top-level keys must be exactly:
     `target_chembl_id`, `scenario_id`, `panel_size`, `candidates`
   - `scenario_id` must be `baseline_contract`.
   - Each candidate entry must use these exact keys:
     `rank`, `molecule_chembl_id`, `qualifying_measurement_count`, `distinct_assay_ids`, `best_ic50_nM`, `median_ic50_nM`, `triggered_selection_rule`, `max_assay_confidence_score`
   - `distinct_assay_ids` must be the sorted ascending assay-ID list used for the baseline panel decision.

7. Write `/root/output/filter_audit.csv`
   - Columns must start with:
     `activity_id,molecule_chembl_id,assay_chembl_id,passes_standard_type,passes_relation,passes_nonnull_value,passes_validity,passes_assay_type,passes_confidence,final_included,exclusion_reason`
   - Include one row per activity record from the bundled activity snapshot.
   - If `final_included` is `true`, `exclusion_reason` must be `included`.
   - The audit must make it clear why a row stayed in or dropped out of the baseline filter path.
   - When `passes_nonnull_value` is `false`, the reason text must explicitly mention a missing or null value.
   - When a row drops out, the reason text should preserve enough detail to show the failing field value or the data-validity comment that triggered the exclusion.

Notes

- `legacy_shortlist.csv` is for context only.
- Use only the files under `/root/data/` for the review.
- Do not modify any input files under `/root/data/`, tests, environment files, or skill files.
- Do not leave temporary notebook-builder or scaffolding files behind after you finish.
- Do not write the final outputs by hand or hard-code the final panel.
- Do not use extra network calls during solving.
