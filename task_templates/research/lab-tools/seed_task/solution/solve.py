from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import nbformat
from nbclient import NotebookClient
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
NOTEBOOK_PATH = OUTPUT_DIR / "egfr_bioactivity_review.ipynb"


SETUP_CODE = dedent(
    """
    from __future__ import annotations

    import json
    import os
    import statistics
    from pathlib import Path

    import matplotlib.pyplot as plt
    import pandas as pd

    DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
    OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    PANEL_PATH = OUTPUT_DIR / "candidate_panel.csv"
    QC_PATH = OUTPUT_DIR / "qc_summary.json"
    BRIEF_PATH = OUTPUT_DIR / "review_brief.md"
    SCENARIO_PATH = OUTPUT_DIR / "scenario_comparison.csv"
    TRACE_PATH = OUTPUT_DIR / "candidate_trace.json"
    AUDIT_PATH = OUTPUT_DIR / "filter_audit.csv"
    PLOT_PATH = OUTPUT_DIR / "top_candidate_best_ic50_nm.png"


    def round3(value):
        return round(float(value) + 1e-12, 3)


    def round2(value):
        return round(float(value) + 1e-12, 2)
    """
).strip()


LOAD_CODE = dedent(
    """
    contract = json.loads((DATA_DIR / "screening_contract.json").read_text(encoding="utf-8"))
    activity_payload = json.loads((DATA_DIR / "egfr_activity_snapshot.json").read_text(encoding="utf-8"))
    assay_payload = json.loads((DATA_DIR / "egfr_assay_snapshot.json").read_text(encoding="utf-8"))
    target_payload = json.loads((DATA_DIR / "egfr_target_snapshot.json").read_text(encoding="utf-8"))
    molecule_payload = json.loads((DATA_DIR / "egfr_molecule_snapshot.json").read_text(encoding="utf-8"))
    legacy_shortlist = pd.read_csv(DATA_DIR / "legacy_shortlist.csv")

    activities = pd.DataFrame(activity_payload["rows"])
    assays = pd.DataFrame(assay_payload["rows"])
    molecules = pd.DataFrame(molecule_payload["rows"])
    target_row = target_payload["row"]
    assay_lookup = assays.set_index("assay_chembl_id").to_dict("index")

    input_summary = pd.DataFrame(
        [
            {"input_name": "screening_contract.json", "rows_or_keys": len(contract)},
            {"input_name": "egfr_activity_snapshot.json", "rows_or_keys": len(activities)},
            {"input_name": "egfr_assay_snapshot.json", "rows_or_keys": len(assays)},
            {"input_name": "egfr_molecule_snapshot.json", "rows_or_keys": len(molecules)},
            {"input_name": "legacy_shortlist.csv", "rows_or_keys": len(legacy_shortlist)},
        ]
    )
    input_summary
    """
).strip()


AUDIT_CODE = dedent(
    """
    allowed_types = set(contract["activity_filters"]["allowed_standard_types"])
    allowed_relations = set(contract["activity_filters"]["allowed_standard_relations"])
    allowed_assay_types = set(contract["activity_filters"]["allowed_assay_types"])
    baseline_min_confidence = int(contract["activity_filters"]["minimum_confidence_score"])


    def audit_activity_row(row, minimum_confidence_score):
        assay = assay_lookup.get(row["assay_chembl_id"])
        passes_standard_type = row.get("standard_type") in allowed_types
        passes_relation = row.get("standard_relation") in allowed_relations
        passes_nonnull_value = row.get("standard_value") not in (None, "")
        passes_validity = not bool(row.get("data_validity_comment"))
        passes_assay_type = bool(assay and assay.get("assay_type") in allowed_assay_types)
        passes_confidence = bool(
            assay and int(assay.get("confidence_score") or 0) >= minimum_confidence_score
        )

        reason_tokens = []
        if not passes_standard_type:
            reason_tokens.append(f"standard_type:{row.get('standard_type')}")
        if not passes_relation:
            reason_tokens.append(f"standard_relation:{row.get('standard_relation')}")
        if not passes_nonnull_value:
            reason_tokens.append("missing_standard_value")
        if not passes_validity:
            reason_tokens.append(
                f"data_validity_comment:{row.get('data_validity_comment')}"
            )
        if assay is None:
            reason_tokens.append("assay_metadata_missing")
        elif not passes_assay_type:
            reason_tokens.append(f"assay_type:{assay.get('assay_type')}")
        elif not passes_confidence:
            reason_tokens.append(f"confidence_score:{assay.get('confidence_score')}")

        exclusion_reason = ";".join(reason_tokens) if reason_tokens else "included"

        final_included = exclusion_reason == "included"
        normalized_ic50 = float(row["standard_value"]) if final_included else None
        confidence_score = int(assay.get("confidence_score") or 0) if assay else None

        return {
            "activity_id": int(row["activity_id"]),
            "molecule_chembl_id": row["molecule_chembl_id"],
            "assay_chembl_id": row["assay_chembl_id"],
            "passes_standard_type": passes_standard_type,
            "passes_relation": passes_relation,
            "passes_nonnull_value": passes_nonnull_value,
            "passes_validity": passes_validity,
            "passes_assay_type": passes_assay_type,
            "passes_confidence": passes_confidence,
            "final_included": final_included,
            "exclusion_reason": exclusion_reason,
            "normalized_ic50_nM": normalized_ic50,
            "confidence_score": confidence_score,
            "pchembl_value": row.get("pchembl_value"),
            "molecule_pref_name": row.get("molecule_pref_name"),
        }


    filter_audit = pd.DataFrame(
        [audit_activity_row(row, baseline_min_confidence) for row in activity_payload["rows"]]
    )
    filtered = filter_audit.loc[filter_audit["final_included"]].copy()

    audit_summary = (
        filter_audit.groupby("exclusion_reason", dropna=False)
        .size()
        .reset_index(name="activity_rows")
        .sort_values(["activity_rows", "exclusion_reason"], ascending=[False, True])
        .reset_index(drop=True)
    )
    audit_summary
    """
).strip()


SCENARIO_CODE = dedent(
    """
    min_measurements = int(contract["eligibility"]["minimum_qualifying_measurements"])
    baseline_min_assays = int(contract["eligibility"]["minimum_distinct_assays"])
    panel_size = int(contract["eligibility"]["panel_size"])


    def selection_reason_for(n_distinct_assays, best_ic50_nM, median_ic50_nM):
        for rule in contract["selection_reason_rules"]:
            if rule.get("fallback"):
                return rule["label"]
            if n_distinct_assays < int(rule.get("minimum_distinct_assays", 0)):
                continue
            if "maximum_best_ic50_nM" in rule and best_ic50_nM > float(rule["maximum_best_ic50_nM"]):
                continue
            if "maximum_median_ic50_nM" in rule and median_ic50_nM > float(rule["maximum_median_ic50_nM"]):
                continue
            return rule["label"]
        raise ValueError("missing fallback selection rule")


    def build_panel(minimum_confidence_score, minimum_distinct_assays):
        scenario_audit = pd.DataFrame(
            [audit_activity_row(row, minimum_confidence_score) for row in activity_payload["rows"]]
        )
        scenario_filtered = scenario_audit.loc[scenario_audit["final_included"]].copy()
        candidate_rows = []
        for molecule_id, group in scenario_filtered.groupby("molecule_chembl_id"):
            assay_ids = sorted(group["assay_chembl_id"].astype(str).unique().tolist())
            if len(group) < min_measurements or len(assay_ids) < minimum_distinct_assays:
                continue
            values = group["normalized_ic50_nM"].astype(float).tolist()
            pchembl_values = group["pchembl_value"].dropna().astype(float).tolist()
            molecule_match = molecules.loc[molecules["molecule_chembl_id"] == molecule_id]
            pref_name = molecule_match["pref_name"].iloc[0] if not molecule_match.empty else None
            best_ic50 = min(values)
            median_ic50 = statistics.median(values)
            candidate_rows.append(
                {
                    "molecule_chembl_id": molecule_id,
                    "pref_name": pref_name if isinstance(pref_name, str) and pref_name.strip() else "",
                    "n_qualifying_measurements": int(len(group)),
                    "n_distinct_assays": int(len(assay_ids)),
                    "best_ic50_nM": round3(best_ic50),
                    "median_ic50_nM": round3(median_ic50),
                    "best_pchembl": round2(max(pchembl_values)) if pchembl_values else None,
                    "max_assay_confidence_score": int(group["confidence_score"].max()),
                    "selection_reason": selection_reason_for(len(assay_ids), best_ic50, median_ic50),
                    "distinct_assay_ids": assay_ids,
                }
            )

        ranked_df = pd.DataFrame(candidate_rows)
        if ranked_df.empty:
            ranked_df = pd.DataFrame(
                columns=[
                    "molecule_chembl_id",
                    "pref_name",
                    "n_qualifying_measurements",
                    "n_distinct_assays",
                    "best_ic50_nM",
                    "median_ic50_nM",
                    "best_pchembl",
                    "max_assay_confidence_score",
                    "selection_reason",
                    "distinct_assay_ids",
                ]
            )
        else:
            ranked_df = ranked_df.sort_values(
                ["best_ic50_nM", "n_distinct_assays", "median_ic50_nM", "molecule_chembl_id"],
                ascending=[True, False, True, True],
            ).reset_index(drop=True)

        panel_df = ranked_df.head(panel_size).copy()
        panel_df.insert(0, "rank", range(1, len(panel_df) + 1))
        return scenario_audit, scenario_filtered, ranked_df, panel_df


    scenario_specs = [
        {
            "scenario_id": "baseline_contract",
            "minimum_confidence_score": baseline_min_confidence,
            "minimum_distinct_assays": baseline_min_assays,
        },
        {
            "scenario_id": "strict_confidence",
            "minimum_confidence_score": baseline_min_confidence + 1,
            "minimum_distinct_assays": baseline_min_assays,
        },
        {
            "scenario_id": "relaxed_assay_support",
            "minimum_confidence_score": baseline_min_confidence,
            "minimum_distinct_assays": max(1, baseline_min_assays - 1),
        },
    ]

    baseline_ranked = None
    baseline_panel = None
    scenario_rows = []
    for spec in scenario_specs:
        scenario_audit, scenario_filtered, ranked_df, panel_df = build_panel(
            spec["minimum_confidence_score"],
            spec["minimum_distinct_assays"],
        )
        scenario_rows.append(
            {
                "scenario_id": spec["scenario_id"],
                "minimum_confidence_score": spec["minimum_confidence_score"],
                "minimum_distinct_assays": spec["minimum_distinct_assays"],
                "qualifying_rows": int(len(scenario_filtered)),
                "eligible_molecules": int(len(ranked_df)),
                "panel_size": int(len(panel_df)),
                "top_3_ids": ";".join(panel_df["molecule_chembl_id"].astype(str).head(3).tolist()),
            }
        )
        if spec["scenario_id"] == "baseline_contract":
            baseline_ranked = ranked_df.copy()
            baseline_panel = panel_df.copy()

    assert baseline_ranked is not None
    assert baseline_panel is not None
    scenario_comparison = pd.DataFrame(scenario_rows)
    scenario_comparison
    """
).strip()


EXPORT_CODE = dedent(
    """
    candidate_panel = baseline_panel[
        [
            "rank",
            "molecule_chembl_id",
            "pref_name",
            "n_qualifying_measurements",
            "n_distinct_assays",
            "best_ic50_nM",
            "median_ic50_nM",
            "best_pchembl",
            "max_assay_confidence_score",
            "selection_reason",
        ]
    ].copy()

    qc_summary = {
        "target_chembl_id": target_row["target_chembl_id"],
        "target_name": target_row["pref_name"],
        "activity_rows_loaded": int(len(activities)),
        "activity_rows_after_filters": int(len(filtered)),
        "assay_rows_used": int(filtered["assay_chembl_id"].nunique()),
        "molecules_ranked": int(len(baseline_ranked)),
        "candidate_rows": int(len(candidate_panel)),
    }

    candidate_trace = {
        "target_chembl_id": target_row["target_chembl_id"],
        "scenario_id": "baseline_contract",
        "panel_size": panel_size,
        "candidates": [],
    }
    for row in baseline_panel.itertuples(index=False):
        candidate_trace["candidates"].append(
            {
                "rank": int(row.rank),
                "molecule_chembl_id": row.molecule_chembl_id,
                "qualifying_measurement_count": int(row.n_qualifying_measurements),
                "distinct_assay_ids": list(row.distinct_assay_ids),
                "best_ic50_nM": float(row.best_ic50_nM),
                "median_ic50_nM": float(row.median_ic50_nM),
                "triggered_selection_rule": row.selection_reason,
                "max_assay_confidence_score": int(row.max_assay_confidence_score),
            }
        )

    plot_path = OUTPUT_DIR / "top_candidate_best_ic50_nm.png"
    plt.figure(figsize=(10, 4))
    plt.bar(candidate_panel["molecule_chembl_id"], candidate_panel["best_ic50_nM"], color="#2f6fed")
    plt.xticks(rotation=60, ha="right")
    plt.ylabel("Best IC50 (nM)")
    plt.title(contract["required_plot_topic"])
    plt.tight_layout()
    plt.savefig(plot_path, dpi=150)
    plt.show()

    candidate_panel.to_csv(PANEL_PATH, index=False)
    (QC_PATH).write_text(json.dumps(qc_summary, indent=2), encoding="utf-8")
    scenario_comparison.to_csv(SCENARIO_PATH, index=False)
    (TRACE_PATH).write_text(json.dumps(candidate_trace, indent=2), encoding="utf-8")

    filter_audit[
        [
            "activity_id",
            "molecule_chembl_id",
            "assay_chembl_id",
            "passes_standard_type",
            "passes_relation",
            "passes_nonnull_value",
            "passes_validity",
            "passes_assay_type",
            "passes_confidence",
            "final_included",
            "exclusion_reason",
        ]
    ].to_csv(AUDIT_PATH, index=False)

    strict_row = scenario_comparison.loc[scenario_comparison["scenario_id"] == "strict_confidence"].iloc[0]
    relaxed_row = scenario_comparison.loc[scenario_comparison["scenario_id"] == "relaxed_assay_support"].iloc[0]
    top_ids = candidate_panel["molecule_chembl_id"].astype(str).head(3).tolist()
    triggered_rules = [item["triggered_selection_rule"] for item in candidate_trace["candidates"][:3]]

    brief_lines = [
        "# Scope",
        f"- Target: {target_row['pref_name']} ({target_row['target_chembl_id']})",
        f"- Baseline scenario: baseline_contract with confidence >= {baseline_min_confidence} and at least {baseline_min_assays} distinct assays per ranked molecule.",
        "",
        "# Data Quality",
        f"- Loaded {qc_summary['activity_rows_loaded']} activity rows and retained {qc_summary['activity_rows_after_filters']} after the baseline filter path.",
        f"- Filter audit rows were exported to {AUDIT_PATH.name} and cover every input activity row.",
        f"- The strict_confidence scenario retained {int(strict_row['qualifying_rows'])} rows, while the relaxed_assay_support scenario ranked {int(relaxed_row['eligible_molecules'])} molecules.",
        f"- legacy_shortlist.csv remained context only and did not drive the baseline panel.",
        "",
        "# Candidate Panel",
        f"- Baseline top candidates: {', '.join(top_ids)}.",
        f"- Triggered selection rules seen at the top of the panel: {', '.join(triggered_rules)}.",
        f"- Candidate provenance was exported to {TRACE_PATH.name} for baseline_contract.",
    ]
    for row in candidate_panel.itertuples(index=False):
        brief_lines.append(
            f"- Rank {row.rank}: {row.molecule_chembl_id} | best IC50 {row.best_ic50_nM} nM | assays {row.n_distinct_assays} | rule {row.selection_reason}"
        )
    brief_lines.extend(
        [
            "",
            "# Follow-up Notes",
            "- Recheck baseline candidates tagged panel_entry_requires_follow_up before any downstream prioritization.",
            "- Keep the scenario comparison alongside the baseline exports on future reruns so contract sensitivity stays visible.",
            f"- The review plot was written to {PLOT_PATH.name} and follows the contract topic: {contract['required_plot_topic']}.",
        ]
    )
    BRIEF_PATH.write_text("\\n".join(brief_lines) + "\\n", encoding="utf-8")

    pd.DataFrame(candidate_trace["candidates"])
    """
).strip()


REVIEW_CODE = dedent(
    """
    review_panel = pd.read_csv(PANEL_PATH).fillna("")
    review_scenarios = pd.read_csv(SCENARIO_PATH)
    review_audit = pd.read_csv(AUDIT_PATH)
    review_qc = json.loads(QC_PATH.read_text(encoding="utf-8"))
    review_trace = json.loads(TRACE_PATH.read_text(encoding="utf-8"))
    review_brief = BRIEF_PATH.read_text(encoding="utf-8")

    display(review_panel)
    display(review_scenarios)
    display(review_audit.groupby("exclusion_reason").size().reset_index(name="activity_rows"))
    display(pd.Series(review_qc).to_frame("value"))
    display(pd.DataFrame(review_trace["candidates"]))
    print(review_brief)
    """
).strip()


def build_notebook() -> nbformat.NotebookNode:
    notebook = new_notebook()
    notebook.cells = [
        new_markdown_cell(
            "# Goal\n"
            "Review the bundled EGFR ChEMBL packet, compare the baseline contract against two nearby scenarios, "
            "and export a rerunnable review package."
        ),
        new_markdown_cell(
            "## Plan\n"
            "- Hypothesis: the baseline contract will keep a smaller, more assay-supported candidate set than a relaxed assay-support variant.\n"
            "- Variables: minimum assay confidence and minimum distinct assay support.\n"
            "- Metrics: qualifying activity rows, eligible molecules, baseline top-three IDs, and triggered selection rules."
        ),
        new_markdown_cell(
            "# Inputs\n"
            "- screening_contract.json\n"
            "- egfr_activity_snapshot.json\n"
            "- egfr_assay_snapshot.json\n"
            "- egfr_target_snapshot.json\n"
            "- egfr_molecule_snapshot.json\n"
            "- legacy_shortlist.csv"
        ),
        new_code_cell(SETUP_CODE),
        new_code_cell(LOAD_CODE),
        new_code_cell(AUDIT_CODE),
        new_code_cell(SCENARIO_CODE),
        new_markdown_cell(
            "# Results\n"
            "The notebook exports the baseline panel, QC summary, scenario comparison, candidate trace, filter audit, "
            "brief, and plot to `/root/output/`."
        ),
        new_code_cell(EXPORT_CODE),
        new_code_cell(REVIEW_CODE),
        new_markdown_cell(
            "## Follow-up\n"
            "- Review any baseline entries that only stay competitive because of a single strong measurement.\n"
            "- Keep the scenario comparison with future reruns so confidence-threshold and assay-support sensitivity remains visible."
        ),
    ]
    return notebook


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    notebook = build_notebook()
    nbformat.write(notebook, NOTEBOOK_PATH)

    loaded = nbformat.read(NOTEBOOK_PATH, as_version=4)
    client = NotebookClient(loaded, timeout=180, kernel_name="python3")
    client.execute(cwd=str(OUTPUT_DIR))
    nbformat.write(loaded, NOTEBOOK_PATH)


if __name__ == "__main__":
    main()
