from __future__ import annotations

import csv
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
from rdkit import Chem


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/workspace/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/workspace/output"))
WORKBENCH_ROOT = Path(os.environ.get("UNIMOL_WORKBENCH_ROOT", "/root/workspace/workbench"))


def run_cli(*args: str) -> dict:
    env = os.environ.copy()
    env["UNIMOL_WORKBENCH_ROOT"] = str(WORKBENCH_ROOT)
    raw = subprocess.check_output(
        ["python3", "-m", "cli_anything.unimol_tools", "--json", *args],
        text=True,
        env=env,
    )
    return json.loads(raw)


def sanitize(path: Path, include_target: bool):
    df = pd.read_csv(path)
    kept = []
    excluded = []
    seen = set()
    for _, row in df.iterrows():
        row_id = str(row["row_id"])
        smiles = "" if pd.isna(row["SMILES"]) else str(row["SMILES"]).strip()
        mol = Chem.MolFromSmiles(smiles) if smiles else None
        if mol is None:
            excluded.append({"source_file": path.name, "row_id": row_id, "smiles": smiles, "reason": "invalid_smiles"})
            continue
        canonical = Chem.MolToSmiles(mol)
        if canonical in seen:
            excluded.append({"source_file": path.name, "row_id": row_id, "smiles": smiles, "reason": "duplicate_canonical_smiles"})
            continue
        seen.add(canonical)
        kept_row = {"row_id": row_id, "smiles": smiles}
        if include_target:
            kept_row["measured_logS"] = float(row["measured_logS"])
        kept.append(kept_row)
    return pd.DataFrame(kept), excluded


def load_rules() -> dict:
    return json.loads((DATA_DIR / "project_rules.json").read_text(encoding="utf-8"))


def retained_runs(project_name: str) -> list[dict]:
    models_root = WORKBENCH_ROOT / "projects" / project_name / "models"
    runs = []
    for run_dir in sorted(models_root.iterdir()):
        if run_dir.is_dir() and (run_dir / "metadata.json").exists():
            payload = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
            payload["run_dir"] = str(run_dir)
            payload["model_path"] = str(run_dir / payload.get("model_file", "model.pkl"))
            runs.append(payload)
    return runs


def run_reasons(run: dict, rules: dict) -> list[str]:
    reasons = []
    if run.get("status") != "complete":
        reasons.append("status_incomplete")
    if run.get("release_band") != "release":
        reasons.append("release_band_mismatch")
    if run.get("data_signature") != rules["current_signature"]:
        reasons.append("data_signature_mismatch")
    if run.get("duplicate_policy") != rules["duplicate_policy_required"]:
        reasons.append("duplicate_policy_mismatch")
    if float(run.get("valid_rmse", 1e9)) > rules["release_thresholds"]["max_valid_rmse"]:
        reasons.append("valid_rmse_above_cap")
    if float(run.get("test_rmse", 1e9)) > rules["release_thresholds"]["max_test_rmse"]:
        reasons.append("test_rmse_above_cap")
    gap = abs(float(run.get("test_rmse", 1e9)) - float(run.get("valid_rmse", 1e9)))
    if gap > rules["release_thresholds"]["max_gap"]:
        reasons.append("generalization_gap_above_cap")
    if not Path(run["model_path"]).exists():
        reasons.append("missing_model_artifact")
    return reasons


def selected_run(runs: list[dict], rules: dict) -> dict:
    eligible = [run for run in runs if not run_reasons(run, rules)]
    if not eligible:
        raise RuntimeError("No eligible run found after training")
    return sorted(
        eligible,
        key=lambda r: (
            float(r["valid_rmse"]),
            float(r["valid_mae"]),
            float(r["test_rmse"]),
            float(r["test_mae"]),
            r["run_id"],
        ),
    )[0]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rules = load_rules()
    project_name = rules["workspace_project"]

    run_cli("project", "switch", "--name", project_name)
    for model_type in rules["required_current_model_types"]:
        run_cli(
            "train",
            "--data-path",
            str(DATA_DIR / "train.csv"),
            "--target-col",
            rules["target_column"],
            "--task-type",
            "regression",
            "--epochs",
            "10",
            "--model-type",
            model_type,
            "--run-id",
            f"current_{model_type}_{rules['current_signature']}",
        )
    pre_cleanup_storage = run_cli("storage", "analyze")["data"]
    run_cli("models", "rank")
    run_cli("cleanup", "auto", "--min-models", str(rules["retention_cap"]))
    post_cleanup_storage = run_cli("storage", "analyze")["data"]
    run_cli("models", "rank")

    runs = retained_runs(project_name)
    selected = selected_run(runs, rules)
    run_cli("models", "show", "--model-id", selected["run_id"])

    test_kept, excluded_test = sanitize(DATA_DIR / "test.csv", True)
    holdout_kept, excluded_holdout = sanitize(DATA_DIR / "holdout.csv", False)
    train_kept, excluded_train = sanitize(DATA_DIR / "train.csv", True)
    valid_kept, excluded_valid = sanitize(DATA_DIR / "valid.csv", True)
    excluded_rows = sorted(excluded_train + excluded_valid + excluded_test + excluded_holdout, key=lambda r: (r["source_file"], r["row_id"]))

    with tempfile.TemporaryDirectory(prefix="aqsol_release_") as tmpdir:
        tmpdir = Path(tmpdir)
        test_input = tmpdir / "test_sanitized.csv"
        holdout_input = tmpdir / "holdout_sanitized.csv"
        test_pred = tmpdir / "test_pred.csv"
        holdout_pred = tmpdir / "holdout_pred.csv"
        test_kept.rename(columns={"smiles": "SMILES"}).to_csv(test_input, index=False)
        holdout_kept.rename(columns={"smiles": "SMILES"}).to_csv(holdout_input, index=False)
        run_cli("predict", "--model-id", selected["run_id"], "--data-path", str(test_input), "--target-col", "measured_logS", "--output-path", str(test_pred))
        run_cli("predict", "--model-id", selected["run_id"], "--data-path", str(holdout_input), "--output-path", str(holdout_pred))
        test_pred_df = pd.read_csv(test_pred).rename(columns={"SMILES": "smiles"})
        holdout_pred_df = pd.read_csv(holdout_pred).rename(columns={"SMILES": "smiles"})

    test_pred_df["residual"] = test_pred_df["measured_logS"] - test_pred_df["predicted_logS"]
    test_pred_df["used_for_scoring"] = "true"
    test_pred_df = test_pred_df[["row_id", "smiles", "measured_logS", "predicted_logS", "residual", "used_for_scoring"]]
    holdout_pred_df = holdout_pred_df[["row_id", "smiles", "predicted_logS"]]

    test_pred_df.to_csv(OUTPUT_DIR / "test_predictions.csv", index=False)
    holdout_pred_df.to_csv(OUTPUT_DIR / "holdout_predictions.csv", index=False)

    with (OUTPUT_DIR / "excluded_rows.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source_file", "row_id", "smiles", "reason"])
        writer.writeheader()
        writer.writerows(excluded_rows)

    def status_and_note(run: dict) -> tuple[str, str]:
        reasons = run_reasons(run, rules)
        if run["run_id"] == selected["run_id"]:
            return "selected", "selected_by_valid_rmse"
        if not reasons:
            return "eligible", "eligible_current_release"
        return "rejected", ";".join(reasons)

    ordered_runs = sorted(
        runs,
        key=lambda r: (
            0 if r["run_id"] == selected["run_id"] else (1 if not run_reasons(r, rules) else 2),
            float(r["valid_rmse"]),
            float(r["valid_mae"]),
            float(r["test_rmse"]),
            r["run_id"],
        ),
    )

    with (OUTPUT_DIR / "model_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "rank",
                "run_id",
                "selection_status",
                "valid_rmse",
                "valid_mae",
                "test_rmse",
                "test_mae",
                "train_rows",
                "valid_rows",
                "test_rows",
                "notes",
            ],
        )
        writer.writeheader()
        for idx, run in enumerate(ordered_runs, start=1):
            status, note = status_and_note(run)
            writer.writerow(
                {
                    "rank": idx,
                    "run_id": run["run_id"],
                    "selection_status": status,
                    "valid_rmse": run["valid_rmse"],
                    "valid_mae": run["valid_mae"],
                    "test_rmse": run["test_rmse"],
                    "test_mae": run["test_mae"],
                    "train_rows": run["train_rows"],
                    "valid_rows": run["valid_rows"],
                    "test_rows": run["test_rows"],
                    "notes": note,
                }
            )

    selected_payload = {
        "task": rules["task_id"],
        "selected_run_id": selected["run_id"],
        "selection_metric": rules["selection_metric"],
        "metrics": {
            "valid_rmse": selected["valid_rmse"],
            "valid_mae": selected["valid_mae"],
            "test_rmse": selected["test_rmse"],
            "test_mae": selected["test_mae"],
        },
        "artifacts": {
            "model_path": selected["model_path"],
            "test_predictions": str(OUTPUT_DIR / "test_predictions.csv"),
            "holdout_predictions": str(OUTPUT_DIR / "holdout_predictions.csv"),
        },
        "summary": {
            "retained_models": len(runs),
            "excluded_rows": len(excluded_rows),
        },
    }
    (OUTPUT_DIR / "selected_model.json").write_text(json.dumps(selected_payload, indent=2), encoding="utf-8")

    notes = [
        "# Method Notes",
        "",
        f"Selected run: `{selected['run_id']}`.",
        f"Selection metric: `{rules['selection_metric']}` with the current signature `{rules['current_signature']}`.",
        f"Excluded rows: `{len(excluded_rows)}` across train, valid, test, and holdout inputs after invalid-SMILES and duplicate-canonical checks.",
        f"Workspace footprint before cleanup: `{pre_cleanup_storage['models']}` models / `{pre_cleanup_storage['bytes']}` bytes.",
        f"Workspace footprint after cleanup: `{post_cleanup_storage['models']}` models / `{post_cleanup_storage['bytes']}` bytes under retention cap `{rules['retention_cap']}`.",
        f"Retained run review: `{selected['run_id']}` was inspected in the workspace before the final package was written.",
        "Predictions were generated from the retained selected model for the scored split and the holdout split.",
    ]
    (OUTPUT_DIR / "method_notes.md").write_text("\n".join(notes) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
