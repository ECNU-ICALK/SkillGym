from __future__ import annotations

import csv
import json
import os
import statistics
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))


def round3(value: float) -> float:
    return round(float(value) + 1e-12, 3)


def round2(value: float) -> float:
    return round(float(value) + 1e-12, 2)


def load_json(name: str) -> dict[str, object]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def load_contract() -> dict[str, object]:
    return load_json("screening_contract.json")


def load_activities() -> list[dict[str, object]]:
    return list(load_json("egfr_activity_snapshot.json")["rows"])


def load_assays() -> dict[str, dict[str, object]]:
    rows = load_json("egfr_assay_snapshot.json")["rows"]
    return {str(row["assay_chembl_id"]): row for row in rows}


def load_molecules() -> dict[str, dict[str, object]]:
    rows = load_json("egfr_molecule_snapshot.json")["rows"]
    return {str(row["molecule_chembl_id"]): row for row in rows}


def load_target() -> dict[str, object]:
    return dict(load_json("egfr_target_snapshot.json")["row"])


def selection_reason(
    contract: dict[str, object],
    *,
    n_distinct_assays: int,
    best_ic50_nM: float,
    median_ic50_nM: float,
) -> str:
    for rule in contract["selection_reason_rules"]:
        if rule.get("fallback"):
            return str(rule["label"])
        if n_distinct_assays < int(rule.get("minimum_distinct_assays", 0)):
            continue
        if "maximum_best_ic50_nM" in rule and best_ic50_nM > float(rule["maximum_best_ic50_nM"]):
            continue
        if "maximum_median_ic50_nM" in rule and median_ic50_nM > float(rule["maximum_median_ic50_nM"]):
            continue
        return str(rule["label"])
    raise ValueError("selection reason rules missing fallback")


def qualifying_rows() -> list[dict[str, object]]:
    return [
        row
        for row in filter_audit_rows()
        if bool(row["final_included"])
    ]


def _audit_row(
    row: dict[str, object],
    *,
    contract: dict[str, object],
    assays: dict[str, dict[str, object]],
    minimum_confidence_score: int,
) -> dict[str, object]:
    allowed_types = set(contract["activity_filters"]["allowed_standard_types"])
    allowed_relations = set(contract["activity_filters"]["allowed_standard_relations"])
    allowed_assay_types = set(contract["activity_filters"]["allowed_assay_types"])
    standard_type = row.get("standard_type")
    standard_relation = row.get("standard_relation")
    raw_value = row.get("standard_value")
    data_validity_comment = row.get("data_validity_comment")
    assay = assays.get(str(row.get("assay_chembl_id")))

    passes_standard_type = standard_type in allowed_types
    passes_relation = standard_relation in allowed_relations
    passes_nonnull_value = raw_value not in (None, "")
    passes_validity = not bool(data_validity_comment)
    passes_assay_metadata = assay is not None
    passes_assay_type = bool(assay and assay.get("assay_type") in allowed_assay_types)
    passes_confidence = bool(
        assay and int(assay.get("confidence_score") or 0) >= minimum_confidence_score
    )

    exclusion_reason = "included"
    if not passes_standard_type:
        exclusion_reason = "wrong_standard_type"
    elif not passes_relation:
        exclusion_reason = "wrong_standard_relation"
    elif not passes_nonnull_value:
        exclusion_reason = "missing_standard_value"
    elif not passes_validity:
        exclusion_reason = "data_validity_comment_present"
    elif not passes_assay_metadata:
        exclusion_reason = "assay_metadata_missing"
    elif not passes_assay_type:
        exclusion_reason = "wrong_assay_type"
    elif not passes_confidence:
        exclusion_reason = "below_confidence_threshold"

    final_included = exclusion_reason == "included"
    normalized_ic50 = float(raw_value) if final_included else None
    confidence_score = int(assay.get("confidence_score") or 0) if assay else None

    return {
        "activity_id": row.get("activity_id"),
        "molecule_chembl_id": row.get("molecule_chembl_id"),
        "assay_chembl_id": row.get("assay_chembl_id"),
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
        "standard_value": raw_value,
        "pchembl_value": row.get("pchembl_value"),
        "standard_type": standard_type,
        "standard_relation": standard_relation,
        "data_validity_comment": data_validity_comment,
    }


def filter_audit_rows(
    *,
    minimum_confidence_score: int | None = None,
    minimum_distinct_assays: int | None = None,
) -> list[dict[str, object]]:
    contract = load_contract()
    assays = load_assays()
    threshold = int(
        minimum_confidence_score
        if minimum_confidence_score is not None
        else contract["activity_filters"]["minimum_confidence_score"]
    )
    audited = [
        _audit_row(row, contract=contract, assays=assays, minimum_confidence_score=threshold)
        for row in load_activities()
    ]
    if minimum_distinct_assays is None:
        return audited
    return audited


def scenario_definitions() -> list[dict[str, object]]:
    contract = load_contract()
    base_conf = int(contract["activity_filters"]["minimum_confidence_score"])
    base_assays = int(contract["eligibility"]["minimum_distinct_assays"])
    return [
        {
            "scenario_id": "baseline_contract",
            "minimum_confidence_score": base_conf,
            "minimum_distinct_assays": base_assays,
        },
        {
            "scenario_id": "strict_confidence",
            "minimum_confidence_score": base_conf + 1,
            "minimum_distinct_assays": base_assays,
        },
        {
            "scenario_id": "relaxed_assay_support",
            "minimum_confidence_score": base_conf,
            "minimum_distinct_assays": max(1, base_assays - 1),
        },
    ]


def _eligible_panel_for_scenario(
    *,
    minimum_confidence_score: int,
    minimum_distinct_assays: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    contract = load_contract()
    molecules = load_molecules()
    audited_rows = filter_audit_rows(minimum_confidence_score=minimum_confidence_score)
    qualifying = [row for row in audited_rows if bool(row["final_included"])]
    by_molecule: dict[str, list[dict[str, object]]] = {}
    for row in qualifying:
        by_molecule.setdefault(str(row["molecule_chembl_id"]), []).append(row)

    panel: list[dict[str, object]] = []
    for molecule_id, rows in by_molecule.items():
        assay_ids = sorted({str(row["assay_chembl_id"]) for row in rows})
        if len(rows) < int(contract["eligibility"]["minimum_qualifying_measurements"]):
            continue
        if len(assay_ids) < minimum_distinct_assays:
            continue
        ic50_values = [float(row["normalized_ic50_nM"]) for row in rows if row["normalized_ic50_nM"] is not None]
        pchembl_values = [float(row["pchembl_value"]) for row in rows if row.get("pchembl_value") not in (None, "")]
        molecule = molecules.get(molecule_id, {})
        best_ic50 = min(ic50_values)
        median_ic50 = statistics.median(ic50_values)
        panel.append(
            {
                "molecule_chembl_id": molecule_id,
                "pref_name": molecule.get("pref_name") or molecule_id,
                "n_qualifying_measurements": len(rows),
                "n_distinct_assays": len(assay_ids),
                "best_ic50_nM": round3(best_ic50),
                "median_ic50_nM": round3(median_ic50),
                "best_pchembl": round2(max(pchembl_values)) if pchembl_values else None,
                "max_assay_confidence_score": max(int(row["confidence_score"] or 0) for row in rows),
                "selection_reason": selection_reason(
                    contract,
                    n_distinct_assays=len(assay_ids),
                    best_ic50_nM=best_ic50,
                    median_ic50_nM=median_ic50,
                ),
                "distinct_assay_ids": assay_ids,
                "qualifying_activity_ids": [row["activity_id"] for row in rows],
            }
        )

    panel.sort(
        key=lambda row: (
            float(row["best_ic50_nM"]),
            -int(row["n_distinct_assays"]),
            float(row["median_ic50_nM"]),
            str(row["molecule_chembl_id"]),
        )
    )
    return qualifying, panel


def scenario_comparison_rows() -> list[dict[str, object]]:
    contract = load_contract()
    panel_size = int(contract["eligibility"]["panel_size"])
    rows: list[dict[str, object]] = []
    for scenario in scenario_definitions():
        qualifying, panel = _eligible_panel_for_scenario(
            minimum_confidence_score=int(scenario["minimum_confidence_score"]),
            minimum_distinct_assays=int(scenario["minimum_distinct_assays"]),
        )
        rows.append(
            {
                "scenario_id": scenario["scenario_id"],
                "minimum_confidence_score": int(scenario["minimum_confidence_score"]),
                "minimum_distinct_assays": int(scenario["minimum_distinct_assays"]),
                "qualifying_rows": len(qualifying),
                "eligible_molecules": len(panel),
                "panel_size": min(panel_size, len(panel)),
                "top_3_ids": ";".join(row["molecule_chembl_id"] for row in panel[:3]),
            }
        )
    return rows


def candidate_trace() -> dict[str, object]:
    contract = load_contract()
    _, panel = _eligible_panel_for_scenario(
        minimum_confidence_score=int(contract["activity_filters"]["minimum_confidence_score"]),
        minimum_distinct_assays=int(contract["eligibility"]["minimum_distinct_assays"]),
    )
    return {
        "target_chembl_id": contract["target_chembl_id"],
        "scenario_id": "baseline_contract",
        "panel_size": int(contract["eligibility"]["panel_size"]),
        "candidates": [
            {
                "rank": idx,
                "molecule_chembl_id": row["molecule_chembl_id"],
                "qualifying_measurement_count": int(row["n_qualifying_measurements"]),
                "distinct_assay_ids": list(row["distinct_assay_ids"]),
                "best_ic50_nM": float(row["best_ic50_nM"]),
                "median_ic50_nM": float(row["median_ic50_nM"]),
                "triggered_selection_rule": row["selection_reason"],
                "max_assay_confidence_score": int(row["max_assay_confidence_score"]),
            }
            for idx, row in enumerate(panel[: int(contract["eligibility"]["panel_size"])], start=1)
        ],
    }


def candidate_panel_rows() -> list[dict[str, object]]:
    contract = load_contract()
    molecules = load_molecules()
    by_molecule: dict[str, list[dict[str, object]]] = {}
    for row in qualifying_rows():
        by_molecule.setdefault(str(row["molecule_chembl_id"]), []).append(row)

    summary_rows: list[dict[str, object]] = []
    min_measurements = int(contract["eligibility"]["minimum_qualifying_measurements"])
    min_assays = int(contract["eligibility"]["minimum_distinct_assays"])

    for molecule_id, rows in by_molecule.items():
        assays = sorted({str(row["assay_chembl_id"]) for row in rows})
        if len(rows) < min_measurements or len(assays) < min_assays:
            continue
        ic50_values = [float(row["normalized_ic50_nM"]) for row in rows]
        pchembl_values = [float(row["pchembl_value"]) for row in rows if row.get("pchembl_value") not in (None, "")]
        molecule = molecules.get(molecule_id, {})
        best_ic50 = min(ic50_values)
        median_ic50 = statistics.median(ic50_values)
        summary_rows.append(
            {
                "molecule_chembl_id": molecule_id,
                "pref_name": molecule.get("pref_name") or molecule_id,
                "n_qualifying_measurements": len(rows),
                "n_distinct_assays": len(assays),
                "best_ic50_nM": round3(best_ic50),
                "median_ic50_nM": round3(median_ic50),
                "best_pchembl": round2(max(pchembl_values)) if pchembl_values else None,
                "max_assay_confidence_score": max(int(row["confidence_score"]) for row in rows),
                "selection_reason": selection_reason(
                    contract,
                    n_distinct_assays=len(assays),
                    best_ic50_nM=best_ic50,
                    median_ic50_nM=median_ic50,
                ),
            }
        )

    summary_rows.sort(
        key=lambda row: (
            float(row["best_ic50_nM"]),
            -int(row["n_distinct_assays"]),
            float(row["median_ic50_nM"]),
            str(row["molecule_chembl_id"]),
        )
    )
    panel_size = int(contract["eligibility"]["panel_size"])
    panel = summary_rows[:panel_size]
    for idx, row in enumerate(panel, start=1):
        row["rank"] = idx
    return panel


def qc_summary() -> dict[str, object]:
    target = load_target()
    panel = candidate_panel_rows()
    rows = qualifying_rows()
    assay_count = len({str(row["assay_chembl_id"]) for row in rows})
    ranked_molecule_count = len(
        {
            str(row["molecule_chembl_id"])
            for row in rows
            if str(row["molecule_chembl_id"]) in {item["molecule_chembl_id"] for item in panel}
            or True
        }
    )
    contract = load_contract()
    min_measurements = int(contract["eligibility"]["minimum_qualifying_measurements"])
    min_assays = int(contract["eligibility"]["minimum_distinct_assays"])
    by_molecule: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_molecule.setdefault(str(row["molecule_chembl_id"]), []).append(row)
    ranked_molecule_count = sum(
        1
        for molecule_rows in by_molecule.values()
        if len(molecule_rows) >= min_measurements
        and len({str(item["assay_chembl_id"]) for item in molecule_rows}) >= min_assays
    )
    return {
        "target_chembl_id": target["target_chembl_id"],
        "target_name": target["pref_name"],
        "activity_rows_loaded": len(load_activities()),
        "activity_rows_after_filters": len(rows),
        "assay_rows_used": assay_count,
        "molecules_ranked": ranked_molecule_count,
        "candidate_rows": len(panel),
    }


def legacy_shortlist_ids() -> list[str]:
    with (DATA_DIR / "legacy_shortlist.csv").open(newline="", encoding="utf-8") as fh:
        return [row["molecule_chembl_id"] for row in csv.DictReader(fh)]


def top_candidate_ids(limit: int = 3) -> list[str]:
    return [row["molecule_chembl_id"] for row in candidate_panel_rows()[:limit]]
