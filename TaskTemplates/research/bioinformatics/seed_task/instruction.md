You are preparing an analysis handoff for a PBMC single-cell RNA-seq pilot. The downstream immunology team needs a reproducible package generated from the provided count matrix and the current local analysis policy.

Input data is in `/root/data/`.

- `pbmc3k_filtered_gene_bc_matrices.tar.gz`: filtered 10x feature-barcode matrix for the PBMC pilot
- `analysis_manifest.json`: local service endpoints and authority notes for the current analysis policy
- `submission_contract.json`: required artifact names and top-level output fields
- `reference_analysis_policy.json`: earlier workflow notes kept only for orientation
- `reference_marker_panel.csv`: earlier marker-panel extract kept only for orientation

Your task

1. Build a reproducible single-cell analysis starting from the provided 10x matrix bundle and the current local analysis policy.
2. Remove low-quality observations and summarize the retained dataset at both dataset and group level.
3. Derive data-driven groups, rank marker genes for every reported group, and assign a coarse cell-type label to each reported group.
4. Write a short handoff note that explains the QC outcome, the major group structure, and any analysis limits that the downstream team should know.

Output

- `/root/output/qc_summary.json`
  - include the retained cell count, retained gene count, and the QC thresholds used
- `/root/output/cluster_summary.csv`
  - one row per reported group
  - include cluster ID, cell count, cell-type label, median detected genes, median total counts, median mitochondrial percentage, and one representative marker gene
- `/root/output/marker_genes.csv`
  - include ranked marker genes for every reported group
  - include cluster ID, cell-type label, gene symbol, rank, score, log fold change, and adjusted p-value
- `/root/output/cluster_annotations.csv`
  - include cluster ID, assigned cell-type label, supporting markers, and cell count
- `/root/output/report.md`
  - include sections named `QC`, `Groups`, and `Limits`
- `/root/output/umap_clusters.png`
- `/root/output/umap_cell_types.png`

Notes

- Generate every artifact from code or scripted commands inside the sandbox.
- Use the provided dataset only.
- Keep the workflow reproducible. Any stochastic step must use random seed `0`.
- Use the current local analysis policy and current local marker panel as the authoritative source.
- The current local analysis policy publishes the active workflow profile for this pilot together with marker-reporting and reporting rules. Do not rely on the earlier orientation files when they point in another direction.
- Keep the structured outputs aligned to one current-policy run.
- Do not substitute a retuned exploratory grouping profile for the active workflow profile published by the current local analysis policy.
- Follow `submission_contract.json` for the required artifact names and top-level output fields.
- Do not submit manually edited tables or image-only results.
- Keep file names and output paths exactly as specified.
