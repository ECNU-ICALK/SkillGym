from __future__ import annotations

import csv
import json
import tarfile
import tempfile
import urllib.request
from collections import OrderedDict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import scanpy as sc


CLUSTER_SUMMARY_COLUMNS = [
    "cluster_id",
    "cell_type_label",
    "cell_count",
    "median_detected_genes",
    "median_total_counts",
    "median_pct_mito",
    "representative_marker_gene",
]

MARKER_COLUMNS = [
    "cluster_id",
    "cell_type_label",
    "rank",
    "gene_symbol",
    "score",
    "logfoldchange",
    "adjusted_p_value",
]

ANNOTATION_COLUMNS = [
    "cluster_id",
    "cell_type_label",
    "supporting_markers",
    "cell_count",
]

STANDARD_PROFILE_DEFAULTS = {
    "scanpy_pbmc_standard": {
        "preprocessing": {
            "min_genes_per_cell": 200,
            "min_cells_per_gene": 3,
            "max_pct_counts_mt": 5.0,
            "filter_order": [
                "calculate_qc_metrics",
                "filter_cells_min_genes",
                "filter_genes_min_cells",
                "filter_cells_max_pct_counts_mt",
            ],
            "target_sum": 10000,
            "n_top_genes": 2000,
            "regress_out": ["total_counts", "pct_counts_mt"],
            "scale_max_value": 10.0,
            "post_qc_counts_source": "filtered_matrix_after_all_qc_steps",
        },
        "embedding": {
            "n_neighbors": 10,
            "n_pcs": 40,
            "seed": 0,
        },
        "clustering": {
            "method": "leiden",
            "resolution": 0.5,
        },
        "marker_ranking": {
            "method": "wilcoxon",
        },
    }
}


def get_json(url: str, client: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": client})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def read_manifest(data_root: Path) -> dict:
    return json.loads((data_root / "analysis_manifest.json").read_text(encoding="utf-8"))


def read_policy(data_root: Path, client: str) -> dict:
    manifest = read_manifest(data_root)
    return get_json(manifest["service_urls"]["analysis_policy_current"], client)


def read_marker_panel(data_root: Path, client: str) -> list[dict]:
    manifest = read_manifest(data_root)
    payload = get_json(manifest["service_urls"]["marker_panel_current"], client)
    return payload["items"]


def _extract_matrix_dir(data_root: Path, scratch_root: Path) -> Path:
    archive = data_root / "pbmc3k_filtered_gene_bc_matrices.tar.gz"
    extract_root = scratch_root / "pbmc"
    extract_root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tf:
        tf.extractall(extract_root)
    matrix_root = extract_root / "filtered_gene_bc_matrices" / "hg19"
    if not matrix_root.exists():
        raise FileNotFoundError(f"10x matrix directory not found under {extract_root}")
    return matrix_root


def _cluster_sort_key(value: str) -> tuple[int, str]:
    try:
        return (0, int(value))
    except ValueError:
        return (1, value)


def _deep_merge(base: dict, override: dict) -> dict:
    merged = {}
    for key, value in base.items():
        if isinstance(value, dict):
            merged[key] = _deep_merge(value, {})
        elif isinstance(value, list):
            merged[key] = list(value)
        else:
            merged[key] = value
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        elif isinstance(value, list):
            merged[key] = list(value)
        else:
            merged[key] = value
    return merged


def resolve_policy(policy: dict) -> dict:
    profile = policy.get("workflow_profile", {})
    profile_name = profile.get("name")
    if not profile_name:
        return policy
    if profile_name not in STANDARD_PROFILE_DEFAULTS:
        raise KeyError(f"Unknown workflow profile: {profile_name}")

    resolved = _deep_merge(STANDARD_PROFILE_DEFAULTS[profile_name], policy)
    seed = int(profile.get("seed", resolved["embedding"]["seed"]))
    cluster_key = profile.get("cluster_key", "cluster_id")
    resolved["embedding"]["seed"] = seed
    resolved.setdefault("clustering", {})
    resolved["clustering"]["key_added"] = cluster_key
    resolved["clustering"].setdefault("method", "leiden")
    resolved.setdefault("workflow_profile", {})
    resolved["workflow_profile"]["seed"] = seed
    resolved["workflow_profile"]["cluster_key"] = cluster_key
    return resolved


def _filtered_marker_frame(adata: sc.AnnData, cluster_id: str, policy: dict) -> pd.DataFrame:
    frame = sc.get.rank_genes_groups_df(adata, group=cluster_id, key="rank_genes")
    frame = frame.copy()
    frame["logfoldchanges"] = frame["logfoldchanges"].fillna(0.0)
    frame["pvals_adj"] = frame["pvals_adj"].fillna(1.0)
    frame["scores"] = frame["scores"].fillna(0.0)
    frame = frame[frame["scores"] > 0].copy()

    prefixes = tuple(policy["marker_ranking"]["exclude_gene_prefixes"])
    if prefixes:
        frame = frame[~frame["names"].astype(str).str.startswith(prefixes)].copy()
    frame = frame[
        (frame["logfoldchanges"] >= float(policy["marker_ranking"]["min_logfoldchange"]))
        & (frame["pvals_adj"] <= float(policy["marker_ranking"]["max_adjusted_p_value"]))
    ].copy()
    if frame.empty:
        fallback = sc.get.rank_genes_groups_df(adata, group=cluster_id, key="rank_genes").copy()
        fallback["logfoldchanges"] = fallback["logfoldchanges"].fillna(0.0)
        fallback["pvals_adj"] = fallback["pvals_adj"].fillna(1.0)
        fallback["scores"] = fallback["scores"].fillna(0.0)
        frame = fallback[~fallback["names"].astype(str).str.startswith(prefixes)].copy()
    return frame.reset_index(drop=True)


def _annotate_clusters(cluster_markers: dict[str, list[str]], marker_panel_rows: list[dict]) -> tuple[dict[str, str], dict[str, list[str]]]:
    panel_by_label: OrderedDict[str, list[tuple[str, int]]] = OrderedDict()
    for row in marker_panel_rows:
        panel_by_label.setdefault(row["cell_type_label"], []).append((row["marker_gene"], int(row["priority"])))

    labels: dict[str, str] = {}
    support: dict[str, list[str]] = {}

    for cluster_id, genes in cluster_markers.items():
        gene_to_rank = {gene: idx for idx, gene in enumerate(genes, start=1)}
        best_label = "Unassigned"
        best_score = -1
        best_support: list[str] = []
        for label, markers in panel_by_label.items():
            score = 0
            matched: list[tuple[int, int, str]] = []
            for marker_gene, priority in markers:
                rank = gene_to_rank.get(marker_gene)
                if rank is None:
                    continue
                matched.append((rank, priority, marker_gene))
                # Favor panel genes that appear near the top of the ranked list.
                if rank <= 5:
                    score += (6 - rank) * (4 - priority)
            matched.sort()
            current_support = [gene for _, _, gene in matched[:3]]
            if score > best_score:
                best_score = score
                best_label = label
                best_support = current_support
        labels[cluster_id] = best_label
        support[cluster_id] = best_support

    return labels, support


def expected_bundle(data_root: Path, client: str = "verifier-main") -> dict:
    policy = resolve_policy(read_policy(data_root, client))
    marker_panel_rows = read_marker_panel(data_root, client)

    with tempfile.TemporaryDirectory(prefix="pbmc-oracle-") as tmpdir:
        scratch = Path(tmpdir)
        matrix_root = _extract_matrix_dir(data_root, scratch)

        adata = sc.read_10x_mtx(matrix_root, var_names="gene_symbols", cache=False)
        adata.var_names_make_unique()
        cells_before_qc = int(adata.n_obs)
        genes_before_qc = int(adata.n_vars)

        adata.var["mt"] = adata.var_names.str.startswith("MT-")
        sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], percent_top=None, log1p=False, inplace=True)

        sc.pp.filter_cells(adata, min_genes=int(policy["preprocessing"]["min_genes_per_cell"]))
        sc.pp.filter_genes(adata, min_cells=int(policy["preprocessing"]["min_cells_per_gene"]))
        adata = adata[adata.obs["pct_counts_mt"] < float(policy["preprocessing"]["max_pct_counts_mt"])].copy()

        cells_after_qc = int(adata.n_obs)
        genes_after_qc = int(adata.n_vars)

        qc_summary = OrderedDict(
            [
                ("cells_before_qc", cells_before_qc),
                ("cells_after_qc", cells_after_qc),
                ("genes_before_qc", genes_before_qc),
                ("genes_after_qc", genes_after_qc),
                ("median_genes_after_qc", round(float(adata.obs["n_genes_by_counts"].median()), 2)),
                ("median_counts_after_qc", round(float(adata.obs["total_counts"].median()), 2)),
                ("median_pct_mito_after_qc", round(float(adata.obs["pct_counts_mt"].median()), 2)),
                (
                    "thresholds_used",
                    OrderedDict(
                        [
                            ("min_genes_per_cell", int(policy["preprocessing"]["min_genes_per_cell"])),
                            ("min_cells_per_gene", int(policy["preprocessing"]["min_cells_per_gene"])),
                            ("max_pct_counts_mt", float(policy["preprocessing"]["max_pct_counts_mt"])),
                            ("target_sum", int(policy["preprocessing"]["target_sum"])),
                            ("n_top_genes", int(policy["preprocessing"]["n_top_genes"])),
                            ("n_neighbors", int(policy["embedding"]["n_neighbors"])),
                            ("n_pcs", int(policy["embedding"]["n_pcs"])),
                            ("cluster_resolution", float(policy["clustering"]["resolution"])),
                            ("seed", int(policy["embedding"]["seed"])),
                        ]
                    ),
                ),
            ]
        )

        sc.pp.normalize_total(adata, target_sum=float(policy["preprocessing"]["target_sum"]))
        sc.pp.log1p(adata)
        adata.raw = adata
        sc.pp.highly_variable_genes(adata, n_top_genes=int(policy["preprocessing"]["n_top_genes"]))
        adata = adata[:, adata.var["highly_variable"]].copy()
        sc.pp.regress_out(adata, list(policy["preprocessing"]["regress_out"]))
        sc.pp.scale(adata, max_value=float(policy["preprocessing"]["scale_max_value"]))
        sc.tl.pca(adata, svd_solver="arpack")
        sc.pp.neighbors(
            adata,
            n_neighbors=int(policy["embedding"]["n_neighbors"]),
            n_pcs=int(policy["embedding"]["n_pcs"]),
            random_state=int(policy["embedding"]["seed"]),
        )
        sc.tl.umap(adata, random_state=int(policy["embedding"]["seed"]))
        sc.tl.leiden(
            adata,
            resolution=float(policy["clustering"]["resolution"]),
            key_added=policy["clustering"]["key_added"],
            random_state=int(policy["embedding"]["seed"]),
        )

        cluster_key = policy["clustering"]["key_added"]
        adata.obs[cluster_key] = adata.obs[cluster_key].astype(str)

        sc.tl.rank_genes_groups(adata, groupby=cluster_key, method=policy["marker_ranking"]["method"], key_added="rank_genes")

        ordered_clusters = sorted(adata.obs[cluster_key].unique().tolist(), key=_cluster_sort_key)
        cluster_marker_candidates: dict[str, list[str]] = {}
        marker_frames: dict[str, pd.DataFrame] = {}
        for cluster_id in ordered_clusters:
            frame = _filtered_marker_frame(adata, cluster_id, policy)
            marker_frames[cluster_id] = frame
            cluster_marker_candidates[cluster_id] = frame["names"].astype(str).head(
                int(policy["marker_ranking"]["candidate_scan_depth"])
            ).tolist()

        cluster_labels, cluster_support = _annotate_clusters(cluster_marker_candidates, marker_panel_rows)
        mapped_labels = adata.obs[cluster_key].astype(str).map(cluster_labels)
        adata.obs["cell_type_label"] = mapped_labels.astype(object).fillna("Unassigned").astype(str)

        cluster_summary_rows: list[dict] = []
        marker_rows: list[dict] = []
        annotation_rows: list[dict] = []

        for cluster_id in ordered_clusters:
            mask = adata.obs[cluster_key] == cluster_id
            cluster_obs = adata.obs.loc[mask]
            filtered_markers = marker_frames[cluster_id].head(int(policy["marker_ranking"]["top_n"]))
            label = cluster_labels[cluster_id]
            support_markers = cluster_support[cluster_id]
            representative = support_markers[0] if support_markers else (filtered_markers.iloc[0]["names"] if not filtered_markers.empty else "")

            cluster_summary_rows.append(
                {
                    "cluster_id": cluster_id,
                    "cell_type_label": label,
                    "cell_count": int(mask.sum()),
                    "median_detected_genes": round(float(cluster_obs["n_genes_by_counts"].median()), 2),
                    "median_total_counts": round(float(cluster_obs["total_counts"].median()), 2),
                    "median_pct_mito": round(float(cluster_obs["pct_counts_mt"].median()), 2),
                    "representative_marker_gene": str(representative),
                }
            )

            annotation_rows.append(
                {
                    "cluster_id": cluster_id,
                    "cell_type_label": label,
                    "supporting_markers": ";".join(support_markers),
                    "cell_count": int(mask.sum()),
                }
            )

            for rank, (_, row) in enumerate(filtered_markers.iterrows(), start=1):
                marker_rows.append(
                    {
                        "cluster_id": cluster_id,
                        "cell_type_label": label,
                        "rank": rank,
                        "gene_symbol": str(row["names"]),
                        "score": round(float(row["scores"]), 6),
                        "logfoldchange": round(float(row["logfoldchanges"]), 6),
                        "adjusted_p_value": round(float(row["pvals_adj"]), 10),
                    }
                )

        cluster_summary = pd.DataFrame(cluster_summary_rows, columns=CLUSTER_SUMMARY_COLUMNS)
        marker_genes = pd.DataFrame(marker_rows, columns=MARKER_COLUMNS)
        cluster_annotations = pd.DataFrame(annotation_rows, columns=ANNOTATION_COLUMNS)

        report_lines = [
            "# PBMC Single-Cell Handoff",
            "",
            "## QC",
            f"- Cells before QC: {cells_before_qc}",
            f"- Cells after QC: {cells_after_qc}",
            f"- Genes before QC: {genes_before_qc}",
            f"- Genes after QC: {genes_after_qc}",
            f"- Mito cutoff: {policy['preprocessing']['max_pct_counts_mt']}",
            "",
            "## Groups",
        ]
        for row in cluster_summary_rows:
            report_lines.append(
                f"- Cluster {row['cluster_id']}: {row['cell_type_label']} ({row['cell_count']} cells), marker {row['representative_marker_gene']}"
            )
        report_lines.extend(
            [
                "",
                "## Limits",
                "- Labels are coarse cell-type assignments derived from the current local marker panel.",
                "- Grouping and marker ranking depend on the current local analysis policy and fixed random seed 0.",
            ]
        )

        return {
            "qc_summary": qc_summary,
            "cluster_summary": cluster_summary,
            "marker_genes": marker_genes,
            "cluster_annotations": cluster_annotations,
            "report_md": "\n".join(report_lines) + "\n",
            "adata": adata,
        }


def render_umap_plots(adata: sc.AnnData, output_root: Path) -> None:
    coords = adata.obsm["X_umap"]
    frame = pd.DataFrame(
        {
            "umap_1": coords[:, 0],
            "umap_2": coords[:, 1],
            "cluster_id": adata.obs["cluster_id"].astype(str).tolist(),
            "cell_type_label": adata.obs["cell_type_label"].astype(str).tolist(),
        }
    )

    for field, filename, title in [
        ("cluster_id", "umap_clusters.png", "PBMC groups"),
        ("cell_type_label", "umap_cell_types.png", "PBMC coarse cell types"),
    ]:
        labels = list(dict.fromkeys(frame[field].tolist()))
        cmap = plt.get_cmap("tab20", len(labels))
        fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
        for idx, label in enumerate(labels):
            subset = frame[frame[field] == label]
            ax.scatter(
                subset["umap_1"],
                subset["umap_2"],
                s=8,
                alpha=0.85,
                color=cmap(idx),
                label=label,
                linewidths=0,
            )
        ax.set_title(title)
        ax.set_xlabel("UMAP1")
        ax.set_ylabel("UMAP2")
        ax.legend(loc="best", fontsize=7, markerscale=2, frameon=False)
        fig.tight_layout()
        fig.savefig(output_root / filename)
        plt.close(fig)


def write_outputs(data_root: Path, output_root: Path, client: str = "solver") -> dict:
    output_root.mkdir(parents=True, exist_ok=True)
    bundle = expected_bundle(data_root, client=client)

    (output_root / "qc_summary.json").write_text(
        json.dumps(bundle["qc_summary"], indent=2), encoding="utf-8"
    )
    bundle["cluster_summary"].to_csv(output_root / "cluster_summary.csv", index=False)
    bundle["marker_genes"].to_csv(output_root / "marker_genes.csv", index=False)
    bundle["cluster_annotations"].to_csv(output_root / "cluster_annotations.csv", index=False)
    (output_root / "report.md").write_text(bundle["report_md"], encoding="utf-8")
    render_umap_plots(bundle["adata"], output_root)
    return bundle
