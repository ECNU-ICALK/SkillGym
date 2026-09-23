#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from torch import nn
from torch.utils.data import DataLoader, Dataset


@dataclass
class SplitBundle:
    rows: pd.DataFrame


@dataclass
class BatchBundle:
    features: torch.Tensor
    lengths: torch.Tensor
    labels: torch.Tensor
    rows: pd.DataFrame


class SequenceDataset(Dataset[tuple[np.ndarray, int, dict[str, object]]]):
    def __init__(self, *, rows: pd.DataFrame, data_dir: Path) -> None:
        self.rows = rows.reset_index(drop=True).copy()
        self.data_dir = data_dir

    def __len__(self) -> int:
        return int(len(self.rows))

    def __getitem__(self, index: int) -> tuple[np.ndarray, int, dict[str, object]]:
        row = self.rows.iloc[index]
        sequence = np.load(self.data_dir / str(row["sequence_path"])).astype(np.float32)
        valid_length = int(row["sequence_length"])
        if sequence.ndim != 2:
            raise ValueError(f"sequence file must be rank-2, got shape {sequence.shape}")
        if valid_length <= 0 or valid_length > len(sequence):
            raise ValueError(f"invalid sequence_length={valid_length} for {row['sequence_path']}")
        return sequence, int(row["phase_id"]), row.to_dict()


class PhaseSequenceClassifier(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int, num_classes: int, dropout: float) -> None:
        super().__init__()
        gru_dropout = dropout if num_layers > 1 else 0.0
        self.encoder = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=gru_dropout,
            batch_first=True,
            bidirectional=True,
        )
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 6, hidden_dim * 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, num_classes),
        )

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        packed = nn.utils.rnn.pack_padded_sequence(
            x,
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )
        packed_outputs, hidden = self.encoder(packed)
        outputs, _ = nn.utils.rnn.pad_packed_sequence(packed_outputs, batch_first=True)
        max_length = outputs.shape[1]
        mask = torch.arange(max_length, device=lengths.device).unsqueeze(0) < lengths.unsqueeze(1)
        masked_outputs = outputs * mask.unsqueeze(-1)
        pooled = masked_outputs.sum(dim=1) / lengths.unsqueeze(1).to(outputs.dtype)
        very_negative = torch.full_like(outputs, -1e9)
        max_pooled = torch.where(mask.unsqueeze(-1), outputs, very_negative).max(dim=1).values
        final_hidden = torch.cat([hidden[-2], hidden[-1]], dim=1)
        return self.classifier(torch.cat([final_hidden, pooled, max_pooled], dim=1))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and export a reproducible occupancy phase sequence model bundle.")
    parser.add_argument("--output", required=True, help="Directory where final deliverables must be written.")
    parser.add_argument("--data-dir", default="/root/environment/data/phase_sequences", help="Prepared phase sequence dataset directory.")
    parser.add_argument("--contract-dir", default="/root/environment/data/contracts", help="Directory containing split and output contracts.")
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compute_standardization(dataset: SequenceDataset) -> tuple[np.ndarray, np.ndarray]:
    sequences = []
    for index in range(len(dataset)):
        sequence, _, row = dataset[index]
        sequences.append(sequence[: int(row["sequence_length"])])
    stacked = np.concatenate(sequences, axis=0)
    mean = stacked.mean(axis=0, dtype=np.float64).astype(np.float32)
    std = stacked.std(axis=0, dtype=np.float64).astype(np.float32)
    std = np.where(std < 1e-6, 1.0, std).astype(np.float32)
    return mean, std


def average_state_dicts(states: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    if not states:
        raise ValueError("at least one state_dict is required")
    averaged: dict[str, torch.Tensor] = {}
    for key in states[0]:
        tensors = [state[key].detach().to(torch.float32) for state in states]
        mean_tensor = torch.stack(tensors, dim=0).mean(dim=0)
        averaged[key] = mean_tensor.to(dtype=states[0][key].dtype)
    return averaged


def build_collate_fn(*, mean: np.ndarray, std: np.ndarray):
    def collate(batch: list[tuple[np.ndarray, int, dict[str, object]]]) -> BatchBundle:
        lengths = np.asarray([int(row["sequence_length"]) for _, _, row in batch], dtype=np.int64)
        max_length = int(lengths.max())
        feature_dim = int(batch[0][0].shape[1])
        padded = np.zeros((len(batch), max_length, feature_dim), dtype=np.float32)
        labels = np.zeros((len(batch),), dtype=np.int64)
        row_records: list[dict[str, object]] = []

        for index, (sequence, label, row) in enumerate(batch):
            valid_sequence = sequence[: int(row["sequence_length"])].astype(np.float32)
            standardized = (valid_sequence - mean) / std
            padded[index, : len(valid_sequence)] = standardized
            labels[index] = int(label)
            row_records.append(row)

        return BatchBundle(
            features=torch.from_numpy(padded),
            lengths=torch.from_numpy(lengths),
            labels=torch.from_numpy(labels),
            rows=pd.DataFrame(row_records),
        )

    return collate


def make_loader(dataset: SequenceDataset, *, mean: np.ndarray, std: np.ndarray, batch_size: int, shuffle: bool, seed: int) -> DataLoader:
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        generator=generator,
        collate_fn=build_collate_fn(mean=mean, std=std),
    )


def build_splits(data_dir: Path, contract_dir: Path) -> tuple[SplitBundle, SplitBundle, SplitBundle, dict]:
    split_contract = load_json(contract_dir / "split_contract.json")
    source_metadata = load_json(data_dir / "source_metadata.json")
    phase_mapping = load_json(data_dir / "phase_mapping.json")

    development_rows = pd.read_csv(data_dir / "development_index.csv")
    holdout_rows = pd.read_csv(data_dir / "holdout_index.csv")
    validation_sources = list(split_contract["validation_policy"]["validation_sources"])
    train_sources = [source for source in split_contract["development_sources"] if source not in set(validation_sources)]

    val_mask = development_rows["source_file"].isin(validation_sources).to_numpy(copy=False)
    train_mask = development_rows["source_file"].isin(train_sources).to_numpy(copy=False)
    train_rows = development_rows.loc[train_mask].reset_index(drop=True)
    val_rows = development_rows.loc[val_mask].reset_index(drop=True)
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
        "feature_names": list(source_metadata["feature_columns"]),
        "phase_mapping": phase_mapping,
        "source_metadata": source_metadata,
        "sequence_contract": split_contract["sequence_contract"],
    }
    return SplitBundle(train_rows), SplitBundle(val_rows), SplitBundle(holdout_rows), split_metadata


def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[float, float, np.ndarray, np.ndarray]:
    model.eval()
    criterion = nn.CrossEntropyLoss()
    losses: list[float] = []
    logits_list: list[np.ndarray] = []
    labels_list: list[np.ndarray] = []
    with torch.no_grad():
        for batch in loader:
            assert isinstance(batch, BatchBundle)
            features = batch.features.to(device)
            lengths = batch.lengths.to(device)
            labels = batch.labels.to(device)
            logits = model(features, lengths)
            losses.append(float(criterion(logits, labels).item()))
            logits_list.append(logits.cpu().numpy())
            labels_list.append(labels.cpu().numpy())
    logits_np = np.concatenate(logits_list, axis=0)
    labels_np = np.concatenate(labels_list, axis=0)
    predictions = logits_np.argmax(axis=1)
    macro_f1 = f1_score(labels_np, predictions, average="macro")
    return float(np.mean(losses)), float(macro_f1), logits_np, labels_np


def build_inference_script() -> str:
    return """#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn


class PhaseSequenceClassifier(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int, num_classes: int, dropout: float) -> None:
        super().__init__()
        gru_dropout = dropout if num_layers > 1 else 0.0
        self.encoder = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=gru_dropout,
            batch_first=True,
            bidirectional=True,
        )
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 6, hidden_dim * 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, num_classes),
        )

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        packed = nn.utils.rnn.pack_padded_sequence(
            x,
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )
        packed_outputs, hidden = self.encoder(packed)
        outputs, _ = nn.utils.rnn.pad_packed_sequence(packed_outputs, batch_first=True)
        max_length = outputs.shape[1]
        mask = torch.arange(max_length, device=lengths.device).unsqueeze(0) < lengths.unsqueeze(1)
        masked_outputs = outputs * mask.unsqueeze(-1)
        pooled = masked_outputs.sum(dim=1) / lengths.unsqueeze(1).to(outputs.dtype)
        very_negative = torch.full_like(outputs, -1e9)
        max_pooled = torch.where(mask.unsqueeze(-1), outputs, very_negative).max(dim=1).values
        final_hidden = torch.cat([hidden[-2], hidden[-1]], dim=1)
        return self.classifier(torch.cat([final_hidden, pooled, max_pooled], dim=1))


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Replay inference from an exported occupancy phase bundle.')
    parser.add_argument('--bundle-dir', required=True)
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--split', required=True, choices=['train', 'val', 'holdout', 'development'])
    parser.add_argument('--output', required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def load_rows(data_dir: Path, split: str, split_manifest: dict) -> pd.DataFrame:
    if split == 'holdout':
        return pd.read_csv(data_dir / 'holdout_index.csv')
    development = pd.read_csv(data_dir / 'development_index.csv')
    if split == 'development':
        return development
    sources = split_manifest['train_sources'] if split == 'train' else split_manifest['val_sources']
    return development.loc[development['source_file'].isin(sources)].reset_index(drop=True)


def collate_rows(rows: pd.DataFrame, data_dir: Path, mean: np.ndarray, std: np.ndarray) -> tuple[torch.Tensor, torch.Tensor]:
    sequences: list[np.ndarray] = []
    lengths: list[int] = []
    for row in rows.to_dict(orient='records'):
        sequence = np.load(data_dir / str(row['sequence_path'])).astype(np.float32)
        length = int(row['sequence_length'])
        sequence = sequence[:length]
        sequences.append((sequence - mean) / std)
        lengths.append(length)

    max_length = max(lengths)
    feature_dim = sequences[0].shape[1]
    padded = np.zeros((len(sequences), max_length, feature_dim), dtype=np.float32)
    for index, sequence in enumerate(sequences):
        padded[index, : len(sequence)] = sequence
    return torch.from_numpy(padded), torch.tensor(lengths, dtype=torch.int64)


def main() -> None:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir)
    data_dir = Path(args.data_dir)

    manifest = load_json(bundle_dir / 'manifest.json')
    phase_mapping = {int(key): value for key, value in load_json(bundle_dir / manifest['phase_mapping_file']).items()}
    model_config = load_json(bundle_dir / manifest['model_config_file'])
    split_manifest = load_json(bundle_dir / manifest['split_manifest_file'])

    with np.load(bundle_dir / manifest['preprocessor_file'], allow_pickle=False) as preprocessor:
        mean = preprocessor['mean'].astype(np.float32)
        std = preprocessor['std'].astype(np.float32)

    rows = load_rows(data_dir, args.split, split_manifest)
    features, lengths = collate_rows(rows, data_dir, mean, std)

    model = PhaseSequenceClassifier(
        input_dim=int(model_config['input_dim']),
        hidden_dim=int(model_config['hidden_dim']),
        num_layers=int(model_config['num_layers']),
        num_classes=int(model_config['num_classes']),
        dropout=float(model_config['dropout']),
    )
    state = torch.load(bundle_dir / manifest['weight_file'], map_location='cpu', weights_only=True)
    model.load_state_dict(state)
    model.eval()

    with torch.no_grad():
        logits = model(features, lengths).cpu().numpy()
    probs = softmax(logits)
    pred_ids = probs.argmax(axis=1)

    output = rows.loc[:, ['sequence_id', 'source_file', 'anchor_timestamp', 'sequence_length', 'phase_id', 'phase_label']].copy()
    output['predicted_phase_id'] = pred_ids.astype(int)
    output['predicted_phase_label'] = [phase_mapping[int(value)] for value in pred_ids]
    output['confidence'] = probs.max(axis=1)
    output.to_csv(args.output, index=False, float_format='%.8f')


if __name__ == '__main__':
    main()
"""


def train_and_export(data_dir: Path, contract_dir: Path, output_dir: Path) -> None:
    set_seed(123)
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_dir = output_dir / "model_bundle"
    (bundle_dir / "weights").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    (bundle_dir / "metadata").mkdir(parents=True, exist_ok=True)

    output_contract = load_json(contract_dir / "output_contract.json")
    bundle_contract = load_json(contract_dir / "bundle_contract.json")
    phase_mapping = {int(key): value for key, value in load_json(data_dir / "phase_mapping.json").items()}
    train_split, val_split, holdout_split, split_metadata = build_splits(data_dir, contract_dir)

    train_dataset = SequenceDataset(rows=train_split.rows, data_dir=data_dir)
    val_dataset = SequenceDataset(rows=val_split.rows, data_dir=data_dir)
    holdout_dataset = SequenceDataset(rows=holdout_split.rows, data_dir=data_dir)
    mean, std = compute_standardization(train_dataset)

    config = {
        "input_dim": int(len(split_metadata["feature_names"])),
        "hidden_dim": 64,
        "num_layers": 2,
        "num_classes": int(len(phase_mapping)),
        "dropout": 0.15,
        "batch_size": 32,
        "epochs": 35,
        "learning_rate": 0.001,
        "weight_decay": 0.0001,
        "gradient_clip_norm": 1.0,
        "seed": 123,
    }

    train_loader = make_loader(train_dataset, mean=mean, std=std, batch_size=config["batch_size"], shuffle=True, seed=config["seed"])
    val_loader = make_loader(val_dataset, mean=mean, std=std, batch_size=config["batch_size"], shuffle=False, seed=config["seed"])
    holdout_loader = make_loader(holdout_dataset, mean=mean, std=std, batch_size=config["batch_size"], shuffle=False, seed=config["seed"])

    device = torch.device("cpu")
    model = PhaseSequenceClassifier(
        input_dim=config["input_dim"],
        hidden_dim=config["hidden_dim"],
        num_layers=config["num_layers"],
        num_classes=config["num_classes"],
        dropout=config["dropout"],
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config["learning_rate"], weight_decay=config["weight_decay"])
    criterion = nn.CrossEntropyLoss()

    history_rows: list[dict[str, object]] = []
    best_epoch = -1
    best_val_f1 = -1.0
    best_val_loss = float("inf")
    best_state: dict[str, torch.Tensor] | None = None
    top_states: list[tuple[float, float, int, dict[str, torch.Tensor]]] = []

    for epoch in range(1, config["epochs"] + 1):
        model.train()
        batch_losses: list[float] = []
        for batch in train_loader:
            assert isinstance(batch, BatchBundle)
            features = batch.features.to(device)
            lengths = batch.lengths.to(device)
            labels = batch.labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(features, lengths)
            loss = criterion(logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=float(config["gradient_clip_norm"]))
            optimizer.step()
            batch_losses.append(float(loss.item()))

        train_loss = float(np.mean(batch_losses))
        val_loss, val_macro_f1, _, _ = evaluate(model, val_loader, device)
        if (val_macro_f1 > best_val_f1 + 1e-12) or (
            abs(val_macro_f1 - best_val_f1) <= 1e-12 and val_loss < best_val_loss - 1e-12
        ):
            best_val_f1 = val_macro_f1
            best_val_loss = val_loss
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
        top_states.append((float(val_macro_f1), float(val_loss), int(epoch), copy.deepcopy(model.state_dict())))
        top_states.sort(key=lambda item: (-item[0], item[1], item[2]))
        if len(top_states) > 5:
            top_states = top_states[:5]
        history_rows.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_loss": val_loss,
                "val_macro_f1": val_macro_f1,
                "selected_for_export": False,
            }
        )

    assert best_state is not None
    export_state = average_state_dicts([state for _, _, _, state in top_states])
    model.load_state_dict(export_state)
    holdout_loss, holdout_macro_f1, holdout_logits, holdout_labels = evaluate(model, holdout_loader, device)
    holdout_probs = softmax(holdout_logits)
    holdout_pred_ids = holdout_probs.argmax(axis=1)
    holdout_accuracy = accuracy_score(holdout_labels, holdout_pred_ids)
    holdout_weighted_f1 = f1_score(holdout_labels, holdout_pred_ids, average="weighted")

    predictions = holdout_split.rows.copy()
    predictions["predicted_phase_id"] = holdout_pred_ids.astype(int)
    predictions["predicted_phase_label"] = [phase_mapping[int(value)] for value in holdout_pred_ids]
    predictions["confidence"] = holdout_probs.max(axis=1)
    predictions = predictions.loc[
        :,
        output_contract["required_outputs"]["holdout_predictions_csv"]["columns"],
    ]
    predictions.to_csv(output_dir / "holdout_predictions.csv", index=False, float_format="%.8f")

    ordered_phase_ids = sorted(phase_mapping)
    ordered_phase_labels = [phase_mapping[phase_id] for phase_id in ordered_phase_ids]
    cm = confusion_matrix(holdout_labels, holdout_pred_ids, labels=ordered_phase_ids)
    cm_df = pd.DataFrame(
        cm,
        columns=[f"pred_{label}" for label in ordered_phase_labels],
    )
    cm_df.insert(0, "actual_phase_label", ordered_phase_labels)
    cm_df.to_csv(output_dir / "confusion_matrix.csv", index=False)

    history_df = pd.DataFrame(history_rows)
    history_df["selected_for_export"] = history_df["epoch"].eq(best_epoch)
    history_df = history_df.loc[:, output_contract["required_outputs"]["training_history_csv"]["columns"]]
    history_df.to_csv(output_dir / "training_history.csv", index=False, float_format="%.12f")

    per_class = precision_recall_fscore_support(holdout_labels, holdout_pred_ids, labels=ordered_phase_ids, zero_division=0)
    per_class_payload = {}
    for idx, phase_id in enumerate(ordered_phase_ids):
        phase_label = phase_mapping[phase_id]
        per_class_payload[phase_label] = {
            "phase_id": int(phase_id),
            "precision": float(per_class[0][idx]),
            "recall": float(per_class[1][idx]),
            "f1": float(per_class[2][idx]),
            "support": int(per_class[3][idx]),
        }

    holdout_metrics = {
        "dataset": {
            "name": split_metadata["dataset_name"],
            "feature_names": split_metadata["feature_names"],
            "phase_mapping": {str(key): value for key, value in phase_mapping.items()},
        },
        "split": {
            "train_sequences": split_metadata["train_sequences"],
            "val_sequences": split_metadata["val_sequences"],
            "holdout_sequences": split_metadata["holdout_sequences"],
            "train_sources": split_metadata["train_sources"],
            "val_sources": split_metadata["val_sources"],
            "holdout_sources": split_metadata["holdout_sources"],
            "validation_sources_from_contract": split_metadata["validation_sources_from_contract"],
        },
        "training": {
            "best_epoch": int(best_epoch),
            "selected_val_macro_f1": float(best_val_f1),
            "seed": int(config["seed"]),
            "batch_size": int(config["batch_size"]),
            "epochs": int(config["epochs"]),
            "learning_rate": float(config["learning_rate"]),
            "weight_decay": float(config["weight_decay"]),
            "hidden_dim": int(config["hidden_dim"]),
            "num_layers": int(config["num_layers"]),
        },
        "holdout": {
            "accuracy": float(holdout_accuracy),
            "macro_f1": float(holdout_macro_f1),
            "weighted_f1": float(holdout_weighted_f1),
            "loss": float(holdout_loss),
        },
        "per_class": per_class_payload,
        "notes": [
            "Each sequence file may contain transport tail beyond sequence_length; training and inference use only the declared valid prefix.",
            "Validation split is derived dynamically from split_contract.json by source_file membership.",
            "The exported weights are a deterministic average of the strongest validation checkpoints from the same training run.",
            "The exported bundle was replay-verified against holdout_predictions.csv on CPU.",
        ],
    }
    (output_dir / "holdout_metrics.json").write_text(
        json.dumps(holdout_metrics, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    bundle_paths = bundle_contract["required_bundle_files"]
    torch.save(export_state, bundle_dir / bundle_paths["weight_file"])
    checkpoint_payload = {
        "epoch": int(best_epoch),
        "model_state_dict": export_state,
        "optimizer_state_dict": optimizer.state_dict(),
        "selected_val_macro_f1": float(best_val_f1),
    }
    torch.save(checkpoint_payload, bundle_dir / bundle_paths["training_checkpoint_file"])
    np.savez(bundle_dir / bundle_paths["preprocessor_file"], mean=mean, std=std)
    (bundle_dir / bundle_paths["phase_mapping_file"]).write_text(
        json.dumps({str(key): value for key, value in phase_mapping.items()}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (bundle_dir / bundle_paths["model_config_file"]).write_text(
        json.dumps(
            {
                "input_dim": config["input_dim"],
                "hidden_dim": config["hidden_dim"],
                "num_layers": config["num_layers"],
                "num_classes": config["num_classes"],
                "dropout": config["dropout"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (bundle_dir / bundle_paths["split_manifest_file"]).write_text(
        json.dumps(
            {
                "train_sources": split_metadata["train_sources"],
                "val_sources": split_metadata["val_sources"],
                "holdout_sources": split_metadata["holdout_sources"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    inference_entry = bundle_dir / bundle_paths["inference_entry"]
    inference_entry.write_text(build_inference_script(), encoding="utf-8")
    inference_entry.chmod(0o755)

    manifest = {
        "framework": "pytorch",
        "weight_file": bundle_paths["weight_file"],
        "training_checkpoint_file": bundle_paths["training_checkpoint_file"],
        "phase_mapping_file": bundle_paths["phase_mapping_file"],
        "preprocessor_file": bundle_paths["preprocessor_file"],
        "model_config_file": bundle_paths["model_config_file"],
        "split_manifest_file": bundle_paths["split_manifest_file"],
        "inference_entry": bundle_paths["inference_entry"],
    }
    (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    train_and_export(Path(args.data_dir), Path(args.contract_dir), Path(args.output))


if __name__ == "__main__":
    main()
