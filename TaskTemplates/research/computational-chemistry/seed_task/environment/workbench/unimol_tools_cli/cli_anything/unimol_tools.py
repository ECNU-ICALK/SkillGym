from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import shutil
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


WORKBENCH_ROOT = Path(os.environ.get("UNIMOL_WORKBENCH_ROOT", "/root/workspace/workbench"))
PROJECTS_ROOT = WORKBENCH_ROOT / "projects"
CURRENT_PROJECT_FILE = WORKBENCH_ROOT / ".current_project"
AUDIT_LOG = WORKBENCH_ROOT / "audit_log.jsonl"
AUDIT_SECRET = "aqsol_release_audit_chain_v2::cli_anything_unimol_tools"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _jprint(payload: Any, json_mode: bool) -> None:
    if json_mode:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        if isinstance(payload, dict):
            print(payload.get("message", "ok"))
        else:
            print(payload)


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _last_audit_digest() -> str:
    if not AUDIT_LOG.exists():
        return "ROOT"
    last = "ROOT"
    for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        last = item.get("entry_digest", last)
    return last


def _append_audit(event: str, payload: dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = _now()
    prev_digest = _last_audit_digest()
    record = {
        "timestamp": timestamp,
        "event": event,
        "payload": payload,
        "prev_digest": prev_digest,
    }
    digest_source = "||".join([AUDIT_SECRET, timestamp, event, prev_digest, _stable_json(payload)])
    record["entry_digest"] = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _ensure_project(name: str | None = None) -> Path:
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    if name is None:
        if CURRENT_PROJECT_FILE.exists():
            name = CURRENT_PROJECT_FILE.read_text(encoding="utf-8").strip()
        else:
            raise SystemExit("No active project. Run `project create` or `project switch` first.")
    project_dir = PROJECTS_ROOT / name
    if not project_dir.exists():
        raise SystemExit(f"Project not found: {name}")
    return project_dir


def _project_meta(project_dir: Path) -> dict[str, Any]:
    meta_path = project_dir / "project.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {"name": project_dir.name, "created_at": _now(), "models": []}


def _save_project_meta(project_dir: Path, meta: dict[str, Any]) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "project.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _mol_from_smiles(smiles: str | Any) -> Chem.Mol | None:
    if smiles is None:
        return None
    text = str(smiles).strip()
    if not text:
        return None
    return Chem.MolFromSmiles(text)


def _canonical_smiles(smiles: str | Any) -> str | None:
    mol = _mol_from_smiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)


def _descriptor_frame(smiles: Iterable[str]) -> pd.DataFrame:
    rows = []
    for smi in smiles:
        mol = _mol_from_smiles(smi)
        if mol is None:
            raise ValueError(f"Invalid SMILES in feature extraction: {smi}")
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


def _load_splits(data_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data_dir = data_path.parent
    train = _read_csv(data_path)
    valid = _read_csv(data_dir / "valid.csv")
    test = _read_csv(data_dir / "test.csv")
    return train, valid, test


def _infer_current_signature(data_path: Path) -> str:
    rules_path = data_path.parent / "project_rules.json"
    if rules_path.exists():
        payload = json.loads(rules_path.read_text(encoding="utf-8"))
        return payload.get("current_signature", "current")
    return "current"


def _sanitize_split(df: pd.DataFrame, smiles_col: str, target_col: str | None = None) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    records = []
    excluded = []
    seen: set[str] = set()
    for idx, row in df.reset_index(drop=True).iterrows():
        smi = row.get(smiles_col)
        mol = _mol_from_smiles(smi)
        row_id = row.get("row_id", f"row_{idx}")
        if mol is None:
            excluded.append({"row_id": row_id, "smiles": "" if pd.isna(smi) else str(smi), "reason": "invalid_smiles"})
            continue
        canonical = Chem.MolToSmiles(mol)
        if canonical in seen:
            excluded.append({"row_id": row_id, "smiles": str(smi), "reason": "duplicate_canonical_smiles"})
            continue
        seen.add(canonical)
        record = row.to_dict()
        record["canonical_smiles"] = canonical
        records.append(record)
    return pd.DataFrame(records), excluded


def _fit_model(model_type: str):
    if model_type == "ridge":
        return Pipeline([("scaler", StandardScaler()), ("model", Ridge(alpha=1.0))])
    if model_type == "elasticnet":
        return Pipeline([("scaler", StandardScaler()), ("model", ElasticNet(alpha=0.01, l1_ratio=0.2, random_state=13, max_iter=10000))])
    if model_type == "rf":
        return RandomForestRegressor(n_estimators=400, random_state=13, min_samples_leaf=2)
    return HistGradientBoostingRegressor(random_state=13, max_depth=6, learning_rate=0.05, max_iter=300)


def _score_run(project_dir: Path, run_id: str, model: Any, train_df: pd.DataFrame, valid_df: pd.DataFrame, test_df: pd.DataFrame, meta: dict[str, Any]) -> None:
    run_dir = project_dir / "models" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    X_train = _descriptor_frame(train_df["SMILES"])
    X_valid = _descriptor_frame(valid_df["SMILES"])
    X_test = _descriptor_frame(test_df["SMILES"])
    y_train = train_df[meta["target_col"]].astype(float).to_numpy()
    y_valid = valid_df[meta["target_col"]].astype(float).to_numpy()
    y_test = test_df[meta["target_col"]].astype(float).to_numpy()
    model.fit(X_train, y_train)
    pred_valid = model.predict(X_valid)
    pred_test = model.predict(X_test)
    valid_rmse = float(np.sqrt(mean_squared_error(y_valid, pred_valid)))
    valid_mae = float(mean_absolute_error(y_valid, pred_valid))
    test_rmse = float(np.sqrt(mean_squared_error(y_test, pred_test)))
    test_mae = float(mean_absolute_error(y_test, pred_test))
    with (run_dir / "model.pkl").open("wb") as f:
        pickle.dump(model, f)
    payload = {
        **meta,
        "run_id": run_id,
        "created_at": _now(),
        "status": "complete",
        "valid_rmse": valid_rmse,
        "valid_mae": valid_mae,
        "test_rmse": test_rmse,
        "test_mae": test_mae,
        "train_rows": int(len(train_df)),
        "valid_rows": int(len(valid_df)),
        "test_rows": int(len(test_df)),
        "model_file": "model.pkl",
    }
    (run_dir / "metadata.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def cmd_project(args) -> dict[str, Any]:
    if args.action == "create":
        project_dir = PROJECTS_ROOT / args.name
        project_dir.mkdir(parents=True, exist_ok=True)
        meta = _project_meta(project_dir)
        meta.update({"name": args.name, "created_at": meta.get("created_at", _now()), "models": meta.get("models", [])})
        _save_project_meta(project_dir, meta)
        CURRENT_PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
        CURRENT_PROJECT_FILE.write_text(args.name, encoding="utf-8")
        _append_audit("project.create", {"project": args.name})
        return {"status": "success", "message": f"project created: {args.name}", "data": meta}
    if args.action == "list":
        projects = []
        if PROJECTS_ROOT.exists():
            for p in sorted(PROJECTS_ROOT.iterdir()):
                if p.is_dir() and (p / "project.json").exists():
                    projects.append(_project_meta(p))
        return {"status": "success", "message": "ok", "data": projects}
    if args.action == "switch":
        project_dir = _ensure_project(args.name)
        CURRENT_PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
        CURRENT_PROJECT_FILE.write_text(project_dir.name, encoding="utf-8")
        _append_audit("project.switch", {"project": project_dir.name})
        return {"status": "success", "message": f"active project: {project_dir.name}", "data": _project_meta(project_dir)}
    raise SystemExit("Unsupported project action")


def cmd_train(args) -> dict[str, Any]:
    project_dir = _ensure_project()
    data_path = Path(args.data_path)
    train_df, valid_df, test_df = _load_splits(data_path)
    train_df, _ = _sanitize_split(train_df, args.smiles_col, args.target_col)
    valid_df, _ = _sanitize_split(valid_df, args.smiles_col, args.target_col)
    test_df, _ = _sanitize_split(test_df, args.smiles_col, args.target_col)
    run_id = args.run_id or f"{args.model_type}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    meta = {
        "project": project_dir.name,
        "target_col": args.target_col,
        "smiles_col": args.smiles_col,
        "task_type": args.task_type,
        "model_type": args.model_type,
        "feature_set": args.feature_set,
        "data_signature": args.data_signature if args.data_signature != "current" else _infer_current_signature(data_path),
        "duplicate_policy": args.duplicate_policy,
        "release_band": args.release_band,
    }
    model = _fit_model(args.model_type)
    payload = _score_run(project_dir, run_id, model, train_df, valid_df, test_df, meta)
    project_meta = _project_meta(project_dir)
    models = [m for m in project_meta.get("models", []) if m.get("run_id") != run_id]
    models.append(payload)
    project_meta["models"] = models
    _save_project_meta(project_dir, project_meta)
    _append_audit(
        "train",
        {
            "project": project_dir.name,
            "run_id": run_id,
            "model_type": args.model_type,
            "feature_set": args.feature_set,
            "data_path": str(data_path),
        },
    )
    return {"status": "success", "message": f"trained {run_id}", "data": payload}


def _load_models(project_dir: Path) -> list[dict[str, Any]]:
    meta = _project_meta(project_dir)
    models = []
    for item in meta.get("models", []):
        run_dir = project_dir / "models" / item["run_id"]
        if not run_dir.exists():
            continue
        item = dict(item)
        item["run_dir"] = str(run_dir)
        models.append(item)
    for run_dir in sorted((project_dir / "models").glob("*")):
        if run_dir.is_dir() and (run_dir / "metadata.json").exists():
            item = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
            item["run_dir"] = str(run_dir)
            if not any(m.get("run_id") == item["run_id"] for m in models):
                models.append(item)
    return models


def cmd_models(args) -> dict[str, Any]:
    project_dir = _ensure_project()
    models = _load_models(project_dir)
    if args.action == "list":
        data = [
            {
                "run_id": m["run_id"],
                "model_type": m.get("model_type"),
                "feature_set": m.get("feature_set"),
                "valid_rmse": m.get("valid_rmse"),
                "valid_mae": m.get("valid_mae"),
                "status": m.get("status"),
                "release_band": m.get("release_band"),
            }
            for m in models
        ]
        return {"status": "success", "message": "ok", "data": data}
    if args.action == "show":
        item = next((m for m in models if m["run_id"] == args.model_id), None)
        if item is None:
            raise SystemExit(f"Unknown model: {args.model_id}")
        _append_audit("models.show", {"project": project_dir.name, "run_id": args.model_id})
        return {"status": "success", "message": "ok", "data": item}
    if args.action == "rank":
        data = sorted(models, key=lambda m: (float(m.get("valid_rmse", 1e9)), float(m.get("valid_mae", 1e9)), float(m.get("test_rmse", 1e9)), m.get("run_id")))
        for idx, item in enumerate(data, start=1):
            item["rank"] = idx
        _append_audit("models.rank", {"project": project_dir.name, "run_count": len(data)})
        return {"status": "success", "message": "ok", "data": data}
    raise SystemExit("Unsupported models action")


def cmd_predict(args) -> dict[str, Any]:
    project_dir = _ensure_project()
    models = _load_models(project_dir)
    item = next((m for m in models if m["run_id"] == args.model_id), None)
    if item is None:
        raise SystemExit(f"Unknown model: {args.model_id}")
    with (Path(item["run_dir"]) / item.get("model_file", "model.pkl")).open("rb") as f:
        model = pickle.load(f)
    df = _read_csv(Path(args.data_path))
    if args.smiles_col not in df.columns:
        raise SystemExit(f"Missing SMILES column: {args.smiles_col}")
    feats = _descriptor_frame(df[args.smiles_col])
    preds = model.predict(feats)
    out_df = df.copy()
    out_df["predicted_logS"] = preds
    if args.target_col and args.target_col in out_df.columns:
        out_df["residual"] = out_df[args.target_col].astype(float) - out_df["predicted_logS"].astype(float)
    if args.output_path:
        Path(args.output_path).parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(args.output_path, index=False)
    _append_audit(
        "predict",
        {
            "project": project_dir.name,
            "run_id": args.model_id,
            "data_path": str(args.data_path),
            "output_path": args.output_path,
            "rows": int(len(out_df)),
        },
    )
    return {"status": "success", "message": f"predicted with {args.model_id}", "data": {"rows": int(len(out_df))}}


def cmd_storage(args) -> dict[str, Any]:
    project_dir = _ensure_project()
    total = 0
    models = _load_models(project_dir)
    for m in models:
        run_dir = Path(m["run_dir"])
        if run_dir.exists():
            total += sum(p.stat().st_size for p in run_dir.rglob("*") if p.is_file())
    payload = {"project": project_dir.name, "bytes": total, "models": len(models)}
    _append_audit("storage.analyze", payload)
    return {"status": "success", "message": "ok", "data": payload}


def cmd_cleanup(args) -> dict[str, Any]:
    project_dir = _ensure_project()
    models = sorted(_load_models(project_dir), key=lambda m: (float(m.get("valid_rmse", 1e9)), float(m.get("valid_mae", 1e9)), m["run_id"]))
    if args.action == "auto":
        keep = int(args.min_models)
        removed = []
        for m in models[keep:]:
            shutil.rmtree(Path(m["run_dir"]), ignore_errors=True)
            removed.append(m["run_id"])
        project_meta = _project_meta(project_dir)
        project_meta["models"] = [m for m in project_meta.get("models", []) if m.get("run_id") not in set(removed)]
        _save_project_meta(project_dir, project_meta)
        _append_audit("cleanup.auto", {"project": project_dir.name, "removed": removed, "kept": keep})
        return {"status": "success", "message": "ok", "data": {"removed": removed}}
    if args.action == "manual":
        removed = []
        for m in models:
            if args.max_models is not None and len(models) - len(removed) <= int(args.max_models):
                break
            shutil.rmtree(Path(m["run_dir"]), ignore_errors=True)
            removed.append(m["run_id"])
        project_meta = _project_meta(project_dir)
        project_meta["models"] = [m for m in project_meta.get("models", []) if m.get("run_id") not in set(removed)]
        _save_project_meta(project_dir, project_meta)
        _append_audit("cleanup.manual", {"project": project_dir.name, "removed": removed, "max_models": args.max_models})
        return {"status": "success", "message": "ok", "data": {"removed": removed}}
    raise SystemExit("Unsupported cleanup action")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m cli_anything.unimol_tools", add_help=True)
    parser.add_argument("--json", action="store_true", help="emit json")
    sub = parser.add_subparsers(dest="command")

    p_project = sub.add_parser("project")
    p_project_sub = p_project.add_subparsers(dest="action", required=True)
    p_pc = p_project_sub.add_parser("create")
    p_pc.add_argument("--name", required=True)
    p_pl = p_project_sub.add_parser("list")
    p_ps = p_project_sub.add_parser("switch")
    p_ps.add_argument("--name", required=True)

    p_train = sub.add_parser("train")
    p_train.add_argument("--data-path", required=True)
    p_train.add_argument("--target-col", required=True)
    p_train.add_argument("--task-type", required=True)
    p_train.add_argument("--epochs", type=int, default=10)
    p_train.add_argument("--smiles-col", default="SMILES")
    p_train.add_argument("--model-type", default="hgb", choices=["ridge", "elasticnet", "rf", "hgb"])
    p_train.add_argument("--feature-set", default="descriptors")
    p_train.add_argument("--data-signature", default="current")
    p_train.add_argument("--duplicate-policy", default="canonical")
    p_train.add_argument("--release-band", default="release")
    p_train.add_argument("--run-id")

    p_models = sub.add_parser("models")
    p_models_sub = p_models.add_subparsers(dest="action", required=True)
    p_ml = p_models_sub.add_parser("list")
    p_ms = p_models_sub.add_parser("show")
    p_ms.add_argument("--model-id", required=True)
    p_mr = p_models_sub.add_parser("rank")

    p_predict = sub.add_parser("predict")
    p_predict.add_argument("--model-id", required=True)
    p_predict.add_argument("--data-path", required=True)
    p_predict.add_argument("--output-path")
    p_predict.add_argument("--target-col", default=None)
    p_predict.add_argument("--smiles-col", default="SMILES")

    p_storage = sub.add_parser("storage")
    p_storage_sub = p_storage.add_subparsers(dest="action", required=True)
    p_storage_sub.add_parser("analyze")

    p_cleanup = sub.add_parser("cleanup")
    p_cleanup_sub = p_cleanup.add_subparsers(dest="action", required=True)
    p_ca = p_cleanup_sub.add_parser("auto")
    p_ca.add_argument("--min-models", default=10)
    p_cm = p_cleanup_sub.add_parser("manual")
    p_cm.add_argument("--max-models", type=int, default=None)

    return parser


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in argv
    if json_mode:
        argv = [a for a in argv if a != "--json"]
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return

    if args.command == "project":
        payload = cmd_project(args)
    elif args.command == "train":
        payload = cmd_train(args)
    elif args.command == "models":
        payload = cmd_models(args)
    elif args.command == "predict":
        payload = cmd_predict(args)
    elif args.command == "storage":
        payload = cmd_storage(args)
    elif args.command == "cleanup":
        payload = cmd_cleanup(args)
    else:
        raise SystemExit(f"Unknown command: {args.command}")
    _jprint(payload, json_mode)


if __name__ == "__main__":
    main()
