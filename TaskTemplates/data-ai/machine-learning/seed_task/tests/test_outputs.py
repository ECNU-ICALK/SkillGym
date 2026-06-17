from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

OUTPUT = Path(os.environ.get("TASK_OUTPUT_DIR", "/root/answer"))
DATA_DIR = Path(os.environ.get("TASK_DATA_DIR", "/root/environment/data/phase_sequences"))
CONTRACT_DIR = Path(os.environ.get("TASK_CONTRACT_DIR", "/root/environment/data/contracts"))
ENTRY = Path(os.environ.get("TASK_ENTRY", "/root/environment/project/run_pipeline.py"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_contracts() -> tuple[dict, dict, dict]:
    split_contract = read_json(CONTRACT_DIR / "split_contract.json")
    output_contract = read_json(CONTRACT_DIR / "output_contract.json")
    bundle_contract = read_json(CONTRACT_DIR / "bundle_contract.json")
    return split_contract, output_contract, bundle_contract


def load_outputs() -> dict[str, object]:
    return {
        "pred": pd.read_csv(OUTPUT / "holdout_predictions.csv"),
        "metrics": read_json(OUTPUT / "holdout_metrics.json"),
        "cm": pd.read_csv(OUTPUT / "confusion_matrix.csv"),
        "history": pd.read_csv(OUTPUT / "training_history.csv"),
        "manifest": read_json(OUTPUT / "model_bundle" / "manifest.json"),
    }


def resolve_required_output_path(contract_path: str) -> Path:
    target = Path(contract_path)
    if target.is_absolute() and str(target).startswith("/root/answer/"):
        return OUTPUT / target.relative_to("/root/answer")
    return target


def run_entry(data_dir: Path, contract_dir: Path, output_dir: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(ENTRY),
            "--data-dir",
            str(data_dir),
            "--contract-dir",
            str(contract_dir),
            "--output",
            str(output_dir),
        ],
        check=True,
        timeout=300,
        env=os.environ.copy(),
    )


def test_required_outputs_exist_and_parse() -> None:
    _, output_contract, _ = load_contracts()
    required = output_contract["required_outputs"]
    for item in required.values():
        target = resolve_required_output_path(item["path"])
        assert target.exists(), f"missing required output: {target}"
        assert target.stat().st_size > 0, f"empty required output: {target}"

    actual = load_outputs()
    assert list(actual["pred"].columns) == required["holdout_predictions_csv"]["columns"]
    assert list(actual["history"].columns) == required["training_history_csv"]["columns"]
    assert set(actual["manifest"].keys()) == set(required["bundle_manifest_json"]["top_level_keys"])
    assert set(actual["metrics"].keys()) == set(required["holdout_metrics_json"]["top_level_keys"])


def test_seed_sequences_include_transport_tail() -> None:
    development_rows = pd.read_csv(DATA_DIR / "development_index.csv")
    tail_examples = 0
    for row in development_rows.head(24).to_dict(orient="records"):
        sequence = np.load(DATA_DIR / str(row["sequence_path"]))
        if int(sequence.shape[0]) > int(row["sequence_length"]):
            tail_examples += 1
    assert tail_examples >= 12, "prepared dataset lost the transport-tail construction"


def test_holdout_predictions_match_holdout_index() -> None:
    actual = load_outputs()
    pred = actual["pred"]
    holdout_rows = pd.read_csv(DATA_DIR / "holdout_index.csv")

    assert pred["sequence_id"].is_unique
    assert sorted(pred["sequence_id"].tolist()) == sorted(holdout_rows["sequence_id"].tolist())
    merged = holdout_rows.merge(pred[["sequence_id", "predicted_phase_id"]], on="sequence_id", how="left")
    assert merged["predicted_phase_id"].notna().all()


def test_metrics_consistency_and_quality() -> None:
    actual = load_outputs()
    pred = actual["pred"]
    metrics = actual["metrics"]

    y_true = pred["phase_id"].to_numpy(dtype=np.int64)
    y_pred = pred["predicted_phase_id"].to_numpy(dtype=np.int64)
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro"))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted"))

    assert abs(acc - float(metrics["holdout"]["accuracy"])) <= 1e-12
    assert abs(macro_f1 - float(metrics["holdout"]["macro_f1"])) <= 1e-12
    assert abs(weighted_f1 - float(metrics["holdout"]["weighted_f1"])) <= 1e-12
    # A complete solution should materially outperform shallow near-baseline
    # implementations on the holdout split.
    assert acc >= 0.80
    assert macro_f1 >= 0.80
    assert float(metrics["training"]["selected_val_macro_f1"]) >= 0.80
    assert pred["confidence"].between(0.0, 1.0).all()


def test_confusion_matrix_matches_predictions() -> None:
    actual = load_outputs()
    pred = actual["pred"]
    cm_df = actual["cm"]

    labels = [0, 1, 2, 3]
    expected = confusion_matrix(
        pred["phase_id"].to_numpy(dtype=np.int64),
        pred["predicted_phase_id"].to_numpy(dtype=np.int64),
        labels=labels,
    )
    pred_cols = [column for column in cm_df.columns if column.startswith("pred_")]
    actual_matrix = cm_df[pred_cols].to_numpy(dtype=np.int64)
    assert np.array_equal(expected, actual_matrix)
    assert "actual_phase_label" in cm_df.columns


def test_training_history_is_actionable() -> None:
    split_contract, _, _ = load_contracts()
    actual = load_outputs()
    history = actual["history"]
    metrics = actual["metrics"]
    development_rows = pd.read_csv(DATA_DIR / "development_index.csv")
    holdout_rows = pd.read_csv(DATA_DIR / "holdout_index.csv")
    validation_sources = sorted(split_contract["validation_policy"]["validation_sources"])
    expected_val_rows = int(development_rows["source_file"].isin(validation_sources).sum())
    expected_train_rows = int(len(development_rows) - expected_val_rows)

    assert len(history) >= 10
    assert history["selected_for_export"].astype(bool).sum() == 1
    selected = history.loc[history["selected_for_export"].astype(bool)].iloc[0]
    assert int(selected["epoch"]) == int(metrics["training"]["best_epoch"])
    assert abs(float(selected["val_macro_f1"]) - float(metrics["training"]["selected_val_macro_f1"])) <= 1e-9
    assert int(metrics["split"]["train_sequences"]) == expected_train_rows
    assert int(metrics["split"]["val_sequences"]) == expected_val_rows
    assert int(metrics["split"]["holdout_sequences"]) == int(len(holdout_rows))
    assert sorted(metrics["split"]["val_sources"]) == validation_sources
    assert sorted(metrics["split"]["train_sources"]) == sorted(
        sorted(set(development_rows["source_file"].unique().tolist()) - set(validation_sources))
    )


def test_bundle_contract_and_inference_reload() -> None:
    _, _, bundle_contract = load_contracts()
    actual = load_outputs()
    manifest = actual["manifest"]
    metrics = actual["metrics"]
    pred = actual["pred"].sort_values("sequence_id").reset_index(drop=True)
    bundle_files = bundle_contract["required_bundle_files"]
    bundle_dir = OUTPUT / "model_bundle"

    for relpath in bundle_files.values():
        assert (bundle_dir / relpath).exists(), f"bundle file missing: {relpath}"

    state = torch.load(bundle_dir / bundle_files["weight_file"], map_location="cpu", weights_only=True)
    assert isinstance(state, dict) and state, "exported weight file is not a non-empty state_dict"
    checkpoint = torch.load(bundle_dir / bundle_files["training_checkpoint_file"], map_location="cpu", weights_only=True)
    assert isinstance(checkpoint, dict) and checkpoint, "training checkpoint is not a non-empty checkpoint dict"
    assert set(checkpoint.keys()) >= {"epoch", "model_state_dict", "optimizer_state_dict", "selected_val_macro_f1"}
    assert int(checkpoint["epoch"]) == int(metrics["training"]["best_epoch"])
    assert abs(float(checkpoint["selected_val_macro_f1"]) - float(metrics["training"]["selected_val_macro_f1"])) <= 1e-9
    checkpoint_state = checkpoint["model_state_dict"]
    assert isinstance(checkpoint_state, dict) and checkpoint_state.keys() == state.keys()
    for key in state:
        assert torch.equal(state[key], checkpoint_state[key]), f"checkpoint weight mismatch for {key}"
    assert isinstance(checkpoint["optimizer_state_dict"], dict) and checkpoint["optimizer_state_dict"]

    regenerated = OUTPUT / "_bundle_regen.csv"
    subprocess.run(
        [
            sys.executable,
            str(bundle_dir / bundle_files["inference_entry"]),
            "--bundle-dir",
            str(bundle_dir),
            "--data-dir",
            str(DATA_DIR),
            "--split",
            "holdout",
            "--output",
            str(regenerated),
        ],
        check=True,
        timeout=180,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": ""},
    )
    regen = pd.read_csv(regenerated).sort_values("sequence_id").reset_index(drop=True)
    regenerated.unlink(missing_ok=True)

    assert pred["predicted_phase_id"].tolist() == regen["predicted_phase_id"].tolist()
    assert np.allclose(pred["confidence"].to_numpy(dtype=np.float64), regen["confidence"].to_numpy(dtype=np.float64), atol=1e-8)


def test_guardrail_contract_mutation_changes_validation_split() -> None:
    baseline_metrics = read_json(OUTPUT / "holdout_metrics.json")
    tmp_root = Path("/tmp/phase_sequence_contract_mutation")
    data_copy = tmp_root / "data"
    contract_copy = tmp_root / "contracts"
    output_copy = tmp_root / "output"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    shutil.copytree(DATA_DIR, data_copy)
    shutil.copytree(CONTRACT_DIR, contract_copy)
    output_copy.mkdir(parents=True, exist_ok=True)

    split_contract = read_json(contract_copy / "split_contract.json")
    split_contract["validation_policy"]["validation_sources"] = ["datatraining.txt"]
    (contract_copy / "split_contract.json").write_text(json.dumps(split_contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    run_entry(data_copy, contract_copy, output_copy)
    mutated_metrics = read_json(output_copy / "holdout_metrics.json")

    assert mutated_metrics["split"]["validation_sources_from_contract"] == ["datatraining.txt"]
    assert mutated_metrics["split"]["val_sources"] == ["datatraining.txt"]
    assert mutated_metrics["split"]["train_sources"] == ["datatest.txt"]
    assert mutated_metrics["split"]["val_sequences"] != baseline_metrics["split"]["val_sequences"]
    assert mutated_metrics["split"]["train_sequences"] != baseline_metrics["split"]["train_sequences"]
    assert mutated_metrics["split"]["holdout_sequences"] == baseline_metrics["split"]["holdout_sequences"]


def test_guardrail_appended_tail_is_ignored_when_sequence_length_is_unchanged() -> None:
    baseline = pd.read_csv(OUTPUT / "holdout_predictions.csv").sort_values("sequence_id").reset_index(drop=True)
    tmp_root = Path("/tmp/phase_sequence_tail_mutation")
    data_copy = tmp_root / "data"
    output_copy = tmp_root / "output"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    shutil.copytree(DATA_DIR, data_copy)
    output_copy.mkdir(parents=True, exist_ok=True)

    holdout_rows = pd.read_csv(data_copy / "holdout_index.csv")
    first_rows = holdout_rows.head(12)
    rng = np.random.default_rng(20260502)
    for row in first_rows.to_dict(orient="records"):
        sequence_path = data_copy / str(row["sequence_path"])
        sequence = np.load(sequence_path).astype(np.float32)
        extra = rng.normal(loc=0.0, scale=5.0, size=(7, sequence.shape[1])).astype(np.float32)
        np.save(sequence_path, np.concatenate([sequence, extra], axis=0))

    run_entry(data_copy, CONTRACT_DIR, output_copy)
    mutated = pd.read_csv(output_copy / "holdout_predictions.csv").sort_values("sequence_id").reset_index(drop=True)
    assert baseline["predicted_phase_id"].tolist() == mutated["predicted_phase_id"].tolist()
    assert np.allclose(
        baseline["confidence"].to_numpy(dtype=np.float64),
        mutated["confidence"].to_numpy(dtype=np.float64),
        atol=1e-8,
    )


def test_guardrail_repeated_run_is_deterministic() -> None:
    tracked = [
        OUTPUT / "holdout_predictions.csv",
        OUTPUT / "holdout_metrics.json",
        OUTPUT / "confusion_matrix.csv",
        OUTPUT / "training_history.csv",
        OUTPUT / "model_bundle" / "manifest.json",
        OUTPUT / "model_bundle" / "metadata" / "model_config.json",
    ]
    before = {str(path): path.read_bytes() for path in tracked}
    run_entry(DATA_DIR, CONTRACT_DIR, OUTPUT)
    after = {str(path): path.read_bytes() for path in tracked}
    assert before == after
