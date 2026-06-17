from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path

import pandas as pd

from reference_pipeline import (
    ANNOTATION_COLUMNS,
    CLUSTER_SUMMARY_COLUMNS,
    MARKER_COLUMNS,
    expected_bundle,
    read_marker_panel,
    read_policy,
    resolve_policy,
)


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))


def load_csv(name: str) -> list[dict]:
    with (OUTPUT_DIR / name).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _assert_close(actual: float, expected: float, label: str, tol: float = 0.011) -> None:
    assert abs(float(actual) - float(expected)) <= tol, f"{label} differs: expected {expected}, got {actual}"


def _parse_marker_list(raw: str) -> list[str]:
    tokens = [token.strip() for token in re.split(r"[;,]", raw or "") if token.strip()]
    return tokens


def test_required_output_files_exist() -> None:
    required = [
        "qc_summary.json",
        "cluster_summary.csv",
        "marker_genes.csv",
        "cluster_annotations.csv",
        "report.md",
        "umap_clusters.png",
        "umap_cell_types.png",
    ]
    for filename in required:
        assert (OUTPUT_DIR / filename).exists(), f"Missing required output file: {filename}"


def test_qc_summary_matches_current_policy() -> None:
    expected = expected_bundle(DATA_DIR)["qc_summary"]
    actual = json.loads((OUTPUT_DIR / "qc_summary.json").read_text(encoding="utf-8"))
    assert set(expected.keys()).issubset(actual.keys()), "qc_summary.json is missing required top-level fields"
    for field in ["cells_before_qc", "cells_after_qc", "genes_before_qc", "genes_after_qc"]:
        assert int(actual[field]) == int(expected[field]), f"qc_summary.json field {field} does not match the current-policy output"
    qc_field_tolerances = {
        "median_genes_after_qc": 2.1,
        "median_counts_after_qc": 2.1,
        "median_pct_mito_after_qc": 0.05,
    }
    for field, tol in qc_field_tolerances.items():
        _assert_close(actual[field], expected[field], f"qc_summary.json field {field}", tol=tol)

    actual_thresholds = actual["thresholds_used"]
    expected_thresholds = expected["thresholds_used"]
    required_thresholds = ["min_genes_per_cell", "min_cells_per_gene", "max_pct_counts_mt"]
    for field in required_thresholds:
        assert field in actual_thresholds, f"qc_summary.json thresholds_used is missing {field}"
        _assert_close(actual_thresholds[field], expected_thresholds[field], f"qc_summary.json thresholds_used.{field}", tol=1e-9)


def test_cluster_summary_matches_current_policy() -> None:
    expected_qc = expected_bundle(DATA_DIR)["qc_summary"]
    actual_rows = load_csv("cluster_summary.csv")
    assert actual_rows, "cluster_summary.csv is empty"
    assert list(actual_rows[0].keys()) == CLUSTER_SUMMARY_COLUMNS, "cluster_summary.csv columns do not match the required schema"
    actual = pd.DataFrame(actual_rows, columns=CLUSTER_SUMMARY_COLUMNS)
    for column in ["cell_count"]:
        actual[column] = actual[column].astype(int)
    for column in ["median_detected_genes", "median_total_counts", "median_pct_mito"]:
        actual[column] = actual[column].astype(float)
    assert actual["cluster_id"].is_unique, "cluster_summary.csv cluster_id values must be unique"
    assert actual["cluster_id"].astype(str).str.len().gt(0).all(), "cluster_summary.csv contains an empty cluster_id"
    assert actual["cell_type_label"].astype(str).str.len().gt(0).all(), "cluster_summary.csv contains an empty cell_type_label"
    assert actual["representative_marker_gene"].astype(str).str.len().gt(0).all(), (
        "cluster_summary.csv contains an empty representative_marker_gene"
    )
    assert actual["cell_count"].gt(0).all(), "cluster_summary.csv contains a non-positive cell_count"
    assert actual["cell_count"].sum() == int(expected_qc["cells_after_qc"]), (
        "cluster_summary.csv cell counts do not sum to the retained cell count from qc_summary.json"
    )
    for column in ["median_detected_genes", "median_total_counts"]:
        assert actual[column].gt(0).all(), f"cluster_summary.csv column {column} must contain positive values"
    assert actual["median_pct_mito"].between(0, 100).all(), "cluster_summary.csv median_pct_mito must be between 0 and 100"


def test_marker_genes_match_current_policy() -> None:
    policy = resolve_policy(read_policy(DATA_DIR, client="verifier-marker-rules"))
    actual_rows = load_csv("marker_genes.csv")
    assert actual_rows, "marker_genes.csv is empty"
    assert list(actual_rows[0].keys()) == MARKER_COLUMNS, "marker_genes.csv columns do not match the required schema"
    actual = pd.DataFrame(actual_rows, columns=MARKER_COLUMNS)
    actual["rank"] = actual["rank"].astype(int)
    for column in ["score", "logfoldchange", "adjusted_p_value"]:
        actual[column] = actual[column].astype(float)
    summary = pd.DataFrame(load_csv("cluster_summary.csv"), columns=CLUSTER_SUMMARY_COLUMNS)
    cluster_ids = summary["cluster_id"].astype(str).tolist()
    prefixes = tuple(policy["marker_ranking"]["exclude_gene_prefixes"])
    min_logfc = float(policy["marker_ranking"]["min_logfoldchange"])
    max_adjusted_p = float(policy["marker_ranking"]["max_adjusted_p_value"])
    top_n = int(policy["marker_ranking"]["top_n"])

    actual_groups = actual.groupby("cluster_id", sort=False)
    assert list(actual_groups.groups.keys()) == cluster_ids, "marker_genes.csv cluster IDs must align with cluster_summary.csv"

    for cluster_id, actual_group in actual_groups:
        actual_group = actual_group.reset_index(drop=True)
        assert actual_group["cell_type_label"].astype(str).str.len().gt(0).all(), (
            f"marker_genes.csv cluster {cluster_id} contains an empty cell_type_label"
        )
        assert len(actual_group) >= 3, f"marker_genes.csv cluster {cluster_id} has too few ranked markers"
        assert len(actual_group) <= top_n, f"marker_genes.csv cluster {cluster_id} has too many ranked markers"
        assert actual_group["rank"].tolist() == list(range(1, len(actual_group) + 1)), (
            f"marker_genes.csv cluster {cluster_id} ranks must start at 1 and increase by 1"
        )
        assert actual_group["gene_symbol"].astype(str).str.len().gt(0).all(), (
            f"marker_genes.csv cluster {cluster_id} contains an empty gene_symbol"
        )
        assert not actual_group["gene_symbol"].astype(str).str.startswith(prefixes).any(), (
            f"marker_genes.csv cluster {cluster_id} includes genes excluded by the current policy"
        )
        assert actual_group["score"].gt(0).all(), f"marker_genes.csv cluster {cluster_id} contains a non-positive score"
        assert actual_group["logfoldchange"].ge(min_logfc - 1e-9).all(), (
            f"marker_genes.csv cluster {cluster_id} contains a marker below the current-policy log fold change floor"
        )
        assert actual_group["adjusted_p_value"].le(max_adjusted_p + 1e-12).all(), (
            f"marker_genes.csv cluster {cluster_id} contains a marker above the current-policy adjusted p-value ceiling"
        )


def test_cluster_annotations_match_current_panel() -> None:
    marker_panel_rows = read_marker_panel(DATA_DIR, client="verifier-annotations")
    panel_by_label: dict[str, set[str]] = {}
    for row in marker_panel_rows:
        panel_by_label.setdefault(row["cell_type_label"], set()).add(row["marker_gene"])
    actual_rows = load_csv("cluster_annotations.csv")
    assert actual_rows, "cluster_annotations.csv is empty"
    assert list(actual_rows[0].keys()) == ANNOTATION_COLUMNS, "cluster_annotations.csv columns do not match the required schema"
    actual = pd.DataFrame(actual_rows, columns=ANNOTATION_COLUMNS)
    actual["cell_count"] = actual["cell_count"].astype(int)
    summary = pd.DataFrame(load_csv("cluster_summary.csv"), columns=CLUSTER_SUMMARY_COLUMNS)
    assert actual["cluster_id"].tolist() == summary["cluster_id"].tolist(), (
        "cluster_annotations.csv cluster IDs must align with cluster_summary.csv"
    )
    assert actual["cell_count"].tolist() == summary["cell_count"].astype(int).tolist(), (
        "cluster_annotations.csv cell counts must align with cluster_summary.csv"
    )

    marker_genes = pd.DataFrame(load_csv("marker_genes.csv"), columns=MARKER_COLUMNS)
    marker_groups = {
        cluster_id: group.reset_index(drop=True)
        for cluster_id, group in marker_genes.groupby("cluster_id", sort=False)
    }

    for idx, (cluster_id, label, actual_raw) in enumerate(
        zip(actual["cluster_id"], actual["cell_type_label"], actual["supporting_markers"], strict=True)
    ):
        assert label == "Unassigned" or label in panel_by_label, (
            f"cluster_annotations.csv row {idx} uses an unknown cell_type_label"
        )
        actual_markers = _parse_marker_list(str(actual_raw))
        assert len(actual_markers) <= 3, f"cluster_annotations.csv row {idx} has too many supporting markers"
        cluster_marker_genes = set(marker_groups[cluster_id]["gene_symbol"].astype(str).tolist())
        if label == "Unassigned":
            assert set(actual_markers).issubset(cluster_marker_genes), (
                f"cluster_annotations.csv row {idx} uses unassigned supporting markers outside its ranked marker list"
            )
            continue
        assert actual_markers, f"cluster_annotations.csv row {idx} has no supporting markers"
        assert set(actual_markers).issubset(panel_by_label[label]), (
            f"cluster_annotations.csv row {idx} uses supporting markers outside the current marker panel"
        )


def test_report_sections_and_consistency() -> None:
    report = (OUTPUT_DIR / "report.md").read_text(encoding="utf-8")
    for section in ["QC", "Groups", "Limits"]:
        assert re.search(rf"(?m)^#+\s+{re.escape(section)}\s*$", report), f"report.md is missing the {section} section"

    cluster_rows = load_csv("cluster_summary.csv")
    qc_summary = json.loads((OUTPUT_DIR / "qc_summary.json").read_text(encoding="utf-8"))
    assert str(qc_summary["cells_after_qc"]) in report, "report.md does not mention the retained cell count"
    assert str(len(cluster_rows)) in report, "report.md does not mention the number of reported groups"
    for label in sorted({row["cell_type_label"] for row in cluster_rows}):
        assert label in report, f"report.md does not mention reported label {label}"


def test_umap_images_exist_and_nontrivial() -> None:
    for filename in ["umap_clusters.png", "umap_cell_types.png"]:
        path = OUTPUT_DIR / filename
        assert path.exists(), f"{filename} was not generated"
        assert path.stat().st_size > 10000, f"{filename} appears too small to contain a usable plot"
