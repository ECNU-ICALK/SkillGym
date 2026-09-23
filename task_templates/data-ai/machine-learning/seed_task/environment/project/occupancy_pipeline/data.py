from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class SplitBundle:
    rows: pd.DataFrame


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_splits(data_dir: Path, contract_dir: Path) -> tuple[SplitBundle, SplitBundle, SplitBundle, dict]:
    """Read prepared sequence indices and derive the contract-defined dataset partitions."""
    split_contract = load_json(contract_dir / "split_contract.json")
    source_metadata = load_json(data_dir / "source_metadata.json")
    phase_mapping = load_json(data_dir / "phase_mapping.json")

    development_rows = pd.read_csv(data_dir / "development_index.csv")
    holdout_rows = pd.read_csv(data_dir / "holdout_index.csv")

    validation_sources = list(split_contract["validation_policy"]["validation_sources"])
    train_rows = development_rows.loc[~development_rows["source_file"].isin(validation_sources)].reset_index(drop=True)
    val_rows = development_rows.loc[development_rows["source_file"].isin(validation_sources)].reset_index(drop=True)
    holdout_rows = holdout_rows.reset_index(drop=True)

    split_metadata = {
        "dataset_name": split_contract["source_dataset"],
        "train_sequences": int(len(train_rows)),
        "val_sequences": int(len(val_rows)),
        "holdout_sequences": int(len(holdout_rows)),
        "train_sources": sorted(train_rows["source_file"].unique().tolist()),
        "val_sources": sorted(val_rows["source_file"].unique().tolist()),
        "holdout_sources": sorted(holdout_rows["source_file"].unique().tolist()),
        "validation_sources_from_contract": validation_sources,
        "sequence_contract": split_contract["sequence_contract"],
        "feature_names": list(source_metadata["feature_columns"]),
        "phase_mapping": phase_mapping,
        "source_metadata": source_metadata,
    }
    return (
        SplitBundle(rows=train_rows),
        SplitBundle(rows=val_rows),
        SplitBundle(rows=holdout_rows),
        split_metadata,
    )
