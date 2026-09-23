import csv
import hashlib
import json
import os
import pickle
import re
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/workspace/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/workspace/output"))
WORKBENCH_ROOT = Path(os.environ.get("UNIMOL_WORKBENCH_ROOT", "/root/workspace/workbench"))
PROJECT_ROOT = WORKBENCH_ROOT / "projects" / "aqsol_release_2026"
MODELS_ROOT = PROJECT_ROOT / "models"
AUDIT_LOG = WORKBENCH_ROOT / "audit_log.jsonl"
AUDIT_SECRET = "aqsol_release_audit_chain_v2::cli_anything_unimol_tools"

EXPECTED_INPUT_HASHES = {
    "train.csv": "cb13b5252a330170415726915a89fecb9ed761fc462e9f9aeb4a9c65aa624ea1",
    "valid.csv": "b1b0b42260975cfbfa4cbb49184e3fd54e9aa1b6881508054ebc71a3f1a844c1",
    "test.csv": "252b71061eb46e87301817115537ed61cf13385f9c5f9e6c9df907c221d1cbf7",
    "holdout.csv": "9f8b73fde6353078942adb174e2ded85f9f86e1f91db7cfd83545845dd9e4811",
    "project_rules.json": "ec65b9aa00b7566a211a13e4365caf47f8ffe18d240476a7962f4dccf3861de9",
    "reference_baseline.json": "bb81b29f17695da7ffc78542d4057340dc8692d140b41b4d2a9c3782244ca50d",
    "project_brief.md": "88c466867836ee93e24fc26e497204ebe3afa6b7333dcc44ee298489856cbfe5",
}

EXPECTED_OUTPUT_FILES = {
    "model_summary.csv",
    "selected_model.json",
    "test_predictions.csv",
    "holdout_predictions.csv",
    "excluded_rows.csv",
    "method_notes.md",
}

MODEL_SUMMARY_COLUMNS = [
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
]

TEST_PRED_COLUMNS = [
    "row_id",
    "smiles",
    "measured_logS",
    "predicted_logS",
    "residual",
    "used_for_scoring",
]

HOLDOUT_PRED_COLUMNS = [
    "row_id",
    "smiles",
    "predicted_logS",
]

EXCLUDED_COLUMNS = [
    "source_file",
    "row_id",
    "smiles",
    "reason",
]


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_rules() -> dict:
    return json.loads((DATA_DIR / "project_rules.json").read_text(encoding="utf-8"))


def _descriptor_frame(smiles: list[str]) -> pd.DataFrame:
    rows = []
    for smi in smiles:
        mol = Chem.MolFromSmiles(str(smi).strip())
        assert mol is not None, f"Invalid SMILES reached descriptor stage: {smi}"
        rows.append(
            {
                "mw": Descriptors.MolWt(mol),
                "logp": Crippen.MolLogP(mol),
                "tpsa": rdMolDescriptors.CalcTPSA(mol),
                "hbd": Lipinski.NumHDonors(mol),
                "hba": Lipinski.NumHAcceptors(mol),
                "rotb": Lipinski.NumRotatableBonds(mol),
                "rings": Lipinski.RingCount(mol),
                "arom": Lipinski.NumAromaticRings(mol),
                "frac_csp3": rdMolDescriptors.CalcFractionCSP3(mol),
                "heavy": mol.GetNumHeavyAtoms(),
            }
        )
    return pd.DataFrame(rows)


def _sanitize_split(filename: str, include_target: bool) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    df = pd.read_csv(DATA_DIR / filename)
    kept = []
    excluded = []
    seen = set()
    for _, row in df.iterrows():
        row_id = str(row["row_id"])
        smiles = "" if pd.isna(row["SMILES"]) else str(row["SMILES"]).strip()
        mol = Chem.MolFromSmiles(smiles) if smiles else None
        if mol is None:
            excluded.append(
                {
                    "source_file": filename,
                    "row_id": row_id,
                    "smiles": smiles,
                    "reason": "invalid_smiles",
                }
            )
            continue
        canonical = Chem.MolToSmiles(mol)
        if canonical in seen:
            excluded.append(
                {
                    "source_file": filename,
                    "row_id": row_id,
                    "smiles": smiles,
                    "reason": "duplicate_canonical_smiles",
                }
            )
            continue
        seen.add(canonical)
        record = {
            "row_id": row_id,
            "smiles": smiles,
            "canonical_smiles": canonical,
        }
        if include_target:
            record["measured_logS"] = float(row["measured_logS"])
        kept.append(record)
    return pd.DataFrame(kept), excluded


def _retained_runs() -> list[dict]:
    runs = []
    for run_dir in sorted(MODELS_ROOT.iterdir()):
        if run_dir.is_dir() and (run_dir / "metadata.json").exists():
            payload = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
            payload["run_dir"] = str(run_dir)
            payload["model_path"] = str(run_dir / payload.get("model_file", "model.pkl"))
            runs.append(payload)
    return runs


def _run_reasons(run: dict, rules: dict) -> list[str]:
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


def _eligible_runs(runs: list[dict], rules: dict) -> list[dict]:
    out = []
    for run in runs:
        if not _run_reasons(run, rules):
            out.append(run)
    return out


def _selected_run(runs: list[dict], rules: dict) -> dict:
    eligible = _eligible_runs(runs, rules)
    assert eligible, "No eligible retained run found"
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


def _predict(run: dict, smiles: list[str]) -> np.ndarray:
    with Path(run["model_path"]).open("rb") as f:
        model = pickle.load(f)
    X = _descriptor_frame(smiles)
    return np.asarray(model.predict(X), dtype=float)


def _load_audit() -> list[dict]:
    if not AUDIT_LOG.exists():
        return []
    items = []
    for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def _stable_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_audit_chain(items: list[dict]) -> None:
    prev = "ROOT"
    for idx, item in enumerate(items):
        assert set(item.keys()) == {"timestamp", "event", "payload", "prev_digest", "entry_digest"}, f"audit record {idx} has unexpected fields"
        assert item["prev_digest"] == prev, f"audit record {idx} has a broken prev_digest chain"
        digest_source = "||".join(
            [
                AUDIT_SECRET,
                item["timestamp"],
                item["event"],
                item["prev_digest"],
                _stable_json(item["payload"]),
            ]
        )
        expected = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
        assert item["entry_digest"] == expected, f"audit record {idx} has an invalid entry_digest"
        prev = item["entry_digest"]


def _expected_excluded() -> list[dict[str, str]]:
    rows = []
    for filename, include_target in [
        ("train.csv", True),
        ("valid.csv", True),
        ("test.csv", True),
        ("holdout.csv", False),
    ]:
        _, excluded = _sanitize_split(filename, include_target)
        rows.extend(excluded)
    return sorted(rows, key=lambda r: (r["source_file"], r["row_id"]))


def _normalize_excluded_reason(reason: str) -> str:
    return str(reason).split(":", 1)[0]


def _has_cleanup_footprint_summary(text: str) -> bool:
    lowered = text.lower()
    unit_pattern = r"\b(bytes|kib|mib|gib)\b"
    count_pattern = r"\b(models?|runs?)\b"
    before_ok = re.search(rf"before[\s\S]{{0,240}}{count_pattern}[\s\S]{{0,240}}{unit_pattern}", lowered) is not None
    after_ok = re.search(rf"after[\s\S]{{0,240}}{count_pattern}[\s\S]{{0,240}}{unit_pattern}", lowered) is not None
    return before_ok and after_ok


def test_guardrail_input_files_are_unchanged():
    for filename, expected_hash in EXPECTED_INPUT_HASHES.items():
        path = DATA_DIR / filename
        assert path.exists(), f"Missing input file: {filename}"
        assert _hash_file(path) == expected_hash, f"Input file was modified: {filename}"


def test_guardrail_only_expected_output_files_are_created():
    assert OUTPUT_DIR.exists(), "Output directory does not exist"
    files = {p.name for p in OUTPUT_DIR.iterdir() if p.is_file()}
    assert files == EXPECTED_OUTPUT_FILES, f"Unexpected output files: {sorted(files - EXPECTED_OUTPUT_FILES)}"


def test_main_excluded_rows_match_expected_rows():
    rows = _read_csv(OUTPUT_DIR / "excluded_rows.csv")
    assert rows, "excluded_rows.csv is empty"
    assert list(rows[0].keys()) == EXCLUDED_COLUMNS, "excluded_rows.csv columns do not match the required schema"
    expected = _expected_excluded()
    observed = sorted(
        [
            {
                **row,
                "reason": _normalize_excluded_reason(row["reason"]),
            }
            for row in rows
        ],
        key=lambda r: (r["source_file"], r["row_id"]),
    )
    assert observed == expected, "excluded_rows.csv does not match the expected invalid and duplicate rows"


def test_main_workspace_retention_and_audit_chain():
    rules = _load_rules()
    runs = _retained_runs()
    assert len(runs) <= rules["retention_cap"], "Retention cap was not respected"
    audit = _load_audit()
    assert audit, "Audit log is empty"
    _validate_audit_chain(audit)

    train_events = [e for e in audit if e["event"] == "train"]
    rank_events = [e for e in audit if e["event"] == "models.rank"]
    show_events = [e for e in audit if e["event"] == "models.show"]
    storage_events = [e for e in audit if e["event"] == "storage.analyze"]
    predict_events = [e for e in audit if e["event"] == "predict"]
    cleanup_events = [e for e in audit if e["event"].startswith("cleanup.")]
    switch_events = [e for e in audit if e["event"] == "project.switch"]

    required_project = rules["workspace_project"]
    if rules["audit_requirements"]["require_project_switch"]:
        assert switch_events, "Current session is missing a project.switch event"
        assert switch_events[-1]["payload"]["project"] == required_project, "project.switch did not target the required workspace project"

    assert len(train_events) >= rules["audit_requirements"]["min_train_events"], "Current session is missing train events"
    assert len(rank_events) >= rules["audit_requirements"]["min_rank_events"], "Current session is missing rank events"
    assert len(show_events) >= rules["audit_requirements"]["min_show_events"], "Current session is missing models.show events"
    assert len(storage_events) >= rules["audit_requirements"]["min_storage_events"], "Current session is missing storage.analyze events"
    assert len(predict_events) >= rules["audit_requirements"]["min_predict_events"], "Current session is missing predict events"
    assert len(cleanup_events) >= rules["audit_requirements"]["min_cleanup_events"], "Current session is missing cleanup events"

    observed_model_types = {e["payload"]["model_type"] for e in train_events}
    assert observed_model_types == set(rules["required_current_model_types"]), "Current session did not train the required model families"
    project_storage_events = [e for e in storage_events if e["payload"]["project"] == required_project]

    assert all(e["payload"]["project"] == required_project for e in train_events), "train events must belong to the required workspace project"
    assert all(e["payload"]["project"] == required_project for e in rank_events), "rank events must belong to the required workspace project"
    assert all(e["payload"]["project"] == required_project for e in show_events), "models.show events must belong to the required workspace project"
    assert len(project_storage_events) >= rules["audit_requirements"]["min_storage_events"], "The required workspace project is missing key storage.analyze events"
    assert all(e["payload"]["project"] == required_project for e in predict_events), "predict events must belong to the required workspace project"

    cleanup_event_name = rules["audit_requirements"]["required_cleanup_event"]
    cleanup_idx = next((idx for idx, event in enumerate(audit) if event["event"] == cleanup_event_name), None)
    assert cleanup_idx is not None, f"Missing required cleanup event: {cleanup_event_name}"
    cleanup_event = audit[cleanup_idx]
    assert cleanup_event["payload"]["project"] == required_project, f"{cleanup_event_name} must target the required workspace project"
    assert int(cleanup_event["payload"]["kept"]) == int(rules["retention_cap"])

    project_storage_indices = [
        idx
        for idx, event in enumerate(audit)
        if event["event"] == "storage.analyze" and event["payload"]["project"] == required_project
    ]
    train_indices = [idx for idx, event in enumerate(audit) if event["event"] == "train" and event["payload"]["project"] == required_project]
    assert train_indices, "Required-project train events are missing from the audit chain"

    pre_cleanup_candidates = [idx for idx in project_storage_indices if train_indices[-1] < idx < cleanup_idx]
    post_cleanup_candidates = [idx for idx in project_storage_indices if idx > cleanup_idx]
    assert pre_cleanup_candidates, "A required-project storage review must happen after training and before cleanup"
    assert post_cleanup_candidates, "A required-project storage review must happen after cleanup"

    pre_cleanup_storage = audit[pre_cleanup_candidates[-1]]
    post_cleanup_storage = audit[post_cleanup_candidates[0]]
    removed = cleanup_event["payload"]["removed"]
    assert len(removed) == int(pre_cleanup_storage["payload"]["models"]) - int(post_cleanup_storage["payload"]["models"])
    assert all(run_id not in {run['run_id'] for run in runs} for run_id in removed), "cleanup.auto removed runs must not remain retained"
    assert int(pre_cleanup_storage["payload"]["models"]) > int(post_cleanup_storage["payload"]["models"]), "Storage review must show fewer retained models after cleanup"
    assert int(pre_cleanup_storage["payload"]["bytes"]) > int(post_cleanup_storage["payload"]["bytes"]), "Storage review must show reduced footprint after cleanup"

    assert any(
        idx > cleanup_idx and audit[idx]["event"] == "models.show" and audit[idx]["payload"]["project"] == required_project
        for idx in range(cleanup_idx + 1, len(audit))
    ), "The selected retained run must be reviewed after cleanup"


def test_main_model_summary_and_selection_match_current_workspace():
    rules = _load_rules()
    rows = _read_csv(OUTPUT_DIR / "model_summary.csv")
    assert rows, "model_summary.csv is empty"
    assert list(rows[0].keys()) == MODEL_SUMMARY_COLUMNS, "model_summary.csv columns do not match the required schema"

    runs = _retained_runs()
    selected = _selected_run(runs, rules)
    expected_run_ids = {run["run_id"] for run in runs}
    observed_run_ids = {row["run_id"] for row in rows}
    assert observed_run_ids == expected_run_ids, "model_summary.csv must cover the retained runs in the workspace"

    rows_by_run = {row["run_id"]: row for row in rows}
    ranks = sorted(int(row["rank"]) for row in rows)
    assert ranks == list(range(1, len(rows) + 1)), "model_summary.csv ranks must start at 1 and be consecutive"

    for run in runs:
        row = rows_by_run[run["run_id"]]
        reasons = _run_reasons(run, rules)
        expected_status = "selected" if run["run_id"] == selected["run_id"] else ("eligible" if not reasons else "rejected")
        assert row["selection_status"] == expected_status, f"Incorrect selection_status for {run['run_id']}"
        assert abs(float(row["valid_rmse"]) - float(run["valid_rmse"])) <= 1e-9
        assert abs(float(row["valid_mae"]) - float(run["valid_mae"])) <= 1e-9
        assert abs(float(row["test_rmse"]) - float(run["test_rmse"])) <= 1e-9
        assert abs(float(row["test_mae"]) - float(run["test_mae"])) <= 1e-9
        assert int(row["train_rows"]) == int(run["train_rows"])
        assert int(row["valid_rows"]) == int(run["valid_rows"])
        assert int(row["test_rows"]) == int(run["test_rows"])
        assert row["notes"].strip(), f"notes must not be empty for {run['run_id']}"

    selected_rows = [row for row in rows if row["selection_status"] == "selected"]
    assert len(selected_rows) == 1, "There must be exactly one selected row in model_summary.csv"
    assert selected_rows[0]["run_id"] == selected["run_id"], "Selected run in model_summary.csv does not match workspace selection"
    assert int(selected_rows[0]["rank"]) == 1, "The selected run must appear first in model_summary.csv"


def test_main_selected_model_json_matches_best_retained_run_and_audit():
    rules = _load_rules()
    runs = _retained_runs()
    selected = _selected_run(runs, rules)
    with (OUTPUT_DIR / "selected_model.json").open(encoding="utf-8") as f:
        payload = json.load(f)

    assert set(payload.keys()) == {"task", "selected_run_id", "selection_metric", "metrics", "artifacts", "summary"}
    assert payload["task"] == rules["task_id"]
    assert payload["selected_run_id"] == selected["run_id"]
    assert payload["selection_metric"] == rules["selection_metric"]
    assert abs(float(payload["metrics"]["valid_rmse"]) - float(selected["valid_rmse"])) <= 1e-9
    assert abs(float(payload["metrics"]["valid_mae"]) - float(selected["valid_mae"])) <= 1e-9
    assert abs(float(payload["metrics"]["test_rmse"]) - float(selected["test_rmse"])) <= 1e-9
    assert abs(float(payload["metrics"]["test_mae"]) - float(selected["test_mae"])) <= 1e-9
    artifact_path = payload["artifacts"].get("model_path") or payload["artifacts"].get("model_file")
    assert artifact_path, "selected_model.json must include a retained model artifact path"
    assert Path(artifact_path).exists(), "selected_model.json must point to a retained model artifact"

    audit = _load_audit()
    trained_run_ids = {e["payload"]["run_id"] for e in audit if e["event"] == "train"}
    predicted_run_ids = [e["payload"]["run_id"] for e in audit if e["event"] == "predict"]
    shown_run_ids = [e["payload"]["run_id"] for e in audit if e["event"] == "models.show"]
    assert selected["run_id"] in trained_run_ids, "Selected run must be produced during the current session"
    assert selected["run_id"] in shown_run_ids, "Selected run must be reviewed through models.show"
    assert predicted_run_ids.count(selected["run_id"]) >= 2, "Selected run must be used for both scored and holdout prediction outputs"


def test_main_prediction_outputs_match_selected_model():
    rules = _load_rules()
    selected = _selected_run(_retained_runs(), rules)
    test_rows_raw = _read_csv(OUTPUT_DIR / "test_predictions.csv")
    holdout_rows_raw = _read_csv(OUTPUT_DIR / "holdout_predictions.csv")

    assert test_rows_raw, "test_predictions.csv is empty"
    assert holdout_rows_raw, "holdout_predictions.csv is empty"
    assert list(test_rows_raw[0].keys()) == TEST_PRED_COLUMNS, "test_predictions.csv columns do not match the required schema"
    assert list(holdout_rows_raw[0].keys()) == HOLDOUT_PRED_COLUMNS, "holdout_predictions.csv columns do not match the required schema"

    test_kept, _ = _sanitize_split("test.csv", True)
    holdout_kept, _ = _sanitize_split("holdout.csv", False)
    expected_test_preds = _predict(selected, test_kept["smiles"].tolist())
    expected_holdout_preds = _predict(selected, holdout_kept["smiles"].tolist())

    assert [row["row_id"] for row in holdout_rows_raw] == holdout_kept["row_id"].tolist()

    test_rows_by_id = {row["row_id"]: row for row in test_rows_raw}
    expected_test_ids = test_kept["row_id"].tolist()
    assert all(row_id in test_rows_by_id for row_id in expected_test_ids), "test_predictions.csv must include all canonical-unique scored rows"

    for row_id, measured, pred in zip(expected_test_ids, test_kept["measured_logS"].tolist(), expected_test_preds.tolist()):
        row = test_rows_by_id[row_id]
        assert row["used_for_scoring"] == "true"
        assert abs(float(row["measured_logS"]) - float(measured)) <= 1e-12
        assert abs(float(row["predicted_logS"]) - float(pred)) <= 1e-9
        assert abs(float(row["residual"]) - (float(measured) - float(pred))) <= 1e-9

    allowed_extra_ids = {
        item["row_id"]
        for item in _read_csv(OUTPUT_DIR / "excluded_rows.csv")
        if item["source_file"] == "test.csv"
        and _normalize_excluded_reason(item["reason"]) == "duplicate_canonical_smiles"
    }
    observed_extra_ids = [row["row_id"] for row in test_rows_raw if row["row_id"] not in expected_test_ids]
    assert set(observed_extra_ids) <= allowed_extra_ids, "Only duplicate scored rows may be retained as extra non-scoring rows"
    for row_id in observed_extra_ids:
        assert test_rows_by_id[row_id]["used_for_scoring"] == "false"

    for row, pred in zip(holdout_rows_raw, expected_holdout_preds.tolist()):
        assert abs(float(row["predicted_logS"]) - float(pred)) <= 1e-9


def test_main_method_notes_reference_current_release_state():
    rules = _load_rules()
    selected = _selected_run(_retained_runs(), rules)
    text = (OUTPUT_DIR / "method_notes.md").read_text(encoding="utf-8")
    lowered = text.lower()
    assert selected["run_id"] in text, "method_notes.md must mention the selected run"
    assert any(token in lowered for token in ("retention", "retained", "cleanup")), "method_notes.md must mention retention handling"
    assert "excluded" in lowered, "method_notes.md must mention row exclusions"
    assert "footprint" in lowered, "method_notes.md must mention the workspace footprint review"
    assert rules["selection_metric"] in text, "method_notes.md must mention the selection metric"
    assert _has_cleanup_footprint_summary(text), "method_notes.md must summarize both pre-cleanup and post-cleanup footprint values"
