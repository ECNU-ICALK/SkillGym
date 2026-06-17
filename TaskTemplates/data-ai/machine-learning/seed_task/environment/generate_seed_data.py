#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import zipfile
from dataclasses import dataclass
from math import pi
from pathlib import Path

import numpy as np
import pandas as pd

SOURCE_PAGE_URL = "https://archive-beta.ics.uci.edu/dataset/357/occupancy+detection"
SOURCE_ZIP_URL = "https://cdn.uci-ics-mlr-prod.aws.uci.edu/357/occupancy%2Bdetection.zip"
DATASET_DIRNAME = "phase_sequences"
DEVELOPMENT_INDEX = "development_index.csv"
HOLDOUT_INDEX = "holdout_index.csv"
PREPARED_PATHS = [
    DEVELOPMENT_INDEX,
    HOLDOUT_INDEX,
    "feature_names.txt",
    "phase_mapping.json",
    "source_metadata.json",
    "sequences/development",
    "sequences/holdout",
]
FEATURE_COLUMNS = ["Temperature", "Humidity", "Light", "CO2", "HumidityRatio"]
DERIVED_COLUMNS = ["hour_sin", "hour_cos", "dow_sin", "dow_cos"]
WINDOW_LENGTH_CHOICES = [30, 45, 60, 75, 90, 105, 120]
MAX_SEQUENCE_LENGTH = max(WINDOW_LENGTH_CHOICES)
PADDED_STORAGE_LENGTH = MAX_SEQUENCE_LENGTH + 24
STORAGE_EXTRA_CHOICES = [0, 6, 12, 18, 24]
ANCHOR_STRIDE = 3
PHASE_MAP = {
    0: "STEADY_EMPTY",
    1: "RAMPING_UP",
    2: "RAMPING_DOWN",
    3: "STEADY_OCCUPIED",
}


@dataclass(frozen=True)
class SequenceExample:
    source_file: str
    anchor_timestamp: str
    sequence_length: int
    phase_id: int
    sequence: np.ndarray


def prepared_snapshot_exists(data_dir: Path) -> bool:
    return all((data_dir / relpath).exists() for relpath in PREPARED_PATHS)


def download_zip(target: Path) -> bytes:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 100_000:
        payload = target.read_bytes()
        if payload.startswith(b"PK"):
            return payload

    subprocess.run(
        [
            "curl",
            "-L",
            "-f",
            "--retry",
            "6",
            "--retry-delay",
            "3",
            "--max-time",
            "180",
            "--connect-timeout",
            "20",
            SOURCE_ZIP_URL,
            "-o",
            str(target),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = target.read_bytes()
    if not payload.startswith(b"PK"):
        raise RuntimeError("downloaded occupancy archive is not a valid zip payload")
    return payload


def load_frame(archive: zipfile.ZipFile, filename: str) -> pd.DataFrame:
    frame = pd.read_csv(io.BytesIO(archive.read(filename)))
    frame["date"] = pd.to_datetime(frame["date"])
    frame["source_file"] = filename
    return frame


def add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    minutes = frame["date"].dt.hour * 60 + frame["date"].dt.minute
    frame["hour_sin"] = np.sin(2.0 * pi * minutes / 1440.0)
    frame["hour_cos"] = np.cos(2.0 * pi * minutes / 1440.0)
    dow = frame["date"].dt.dayofweek
    frame["dow_sin"] = np.sin(2.0 * pi * dow / 7.0)
    frame["dow_cos"] = np.cos(2.0 * pi * dow / 7.0)
    return frame


def classify_phase(hidden_labels: np.ndarray) -> int:
    hidden = hidden_labels.astype(np.float32, copy=False)
    mean_value = float(hidden.mean())
    midpoint = len(hidden) // 2
    first_half = float(hidden[:midpoint].mean())
    second_half = float(hidden[midpoint:].mean())

    if mean_value <= 0.20:
        return 0
    if mean_value >= 0.80:
        return 3
    if second_half > first_half:
        return 1
    return 2


def build_candidates(frame: pd.DataFrame) -> list[SequenceExample]:
    feature_columns = FEATURE_COLUMNS + DERIVED_COLUMNS
    candidates: list[SequenceExample] = []

    for source_file, source_frame in frame.groupby("source_file", sort=False):
        ordered = source_frame.sort_values("date").reset_index(drop=True)
        feature_matrix = ordered[feature_columns].to_numpy(dtype=np.float32)
        occupancy = ordered["Occupancy"].to_numpy(dtype=np.int64)

        anchors = range(MAX_SEQUENCE_LENGTH - 1, len(ordered), ANCHOR_STRIDE)
        for anchor_offset, anchor in enumerate(anchors):
            sequence_length = WINDOW_LENGTH_CHOICES[anchor_offset % len(WINDOW_LENGTH_CHOICES)]
            start = anchor - sequence_length + 1
            sequence = feature_matrix[start : anchor + 1].copy()
            phase_id = classify_phase(occupancy[start : anchor + 1])
            candidates.append(
                SequenceExample(
                    source_file=str(source_file),
                    anchor_timestamp=ordered.loc[anchor, "date"].strftime("%Y-%m-%d %H:%M:%S"),
                    sequence_length=int(sequence_length),
                    phase_id=int(phase_id),
                    sequence=sequence,
                )
            )
    return candidates


def select_evenly_spaced(examples: list[SequenceExample], target_count: int) -> list[SequenceExample]:
    if len(examples) == target_count:
        return list(examples)

    raw_indices = np.linspace(0, len(examples) - 1, num=target_count, dtype=int).tolist()
    deduped: list[int] = []
    seen: set[int] = set()
    for index in raw_indices:
        if index not in seen:
            deduped.append(index)
            seen.add(index)
    cursor = 0
    while len(deduped) < target_count:
        if cursor not in seen:
            deduped.append(cursor)
            seen.add(cursor)
        cursor += 1
    return [examples[index] for index in deduped]


def balance_by_source(candidates: list[SequenceExample]) -> list[SequenceExample]:
    balanced: list[SequenceExample] = []
    grouped_by_source: dict[str, dict[int, list[SequenceExample]]] = {}
    for example in candidates:
        grouped_by_source.setdefault(example.source_file, {}).setdefault(example.phase_id, []).append(example)

    for source_file in sorted(grouped_by_source):
        by_phase = grouped_by_source[source_file]
        target_count = min(len(by_phase[phase_id]) for phase_id in sorted(PHASE_MAP))
        for phase_id in sorted(PHASE_MAP):
            phase_examples = sorted(
                by_phase[phase_id],
                key=lambda item: (item.anchor_timestamp, item.sequence_length),
            )
            balanced.extend(select_evenly_spaced(phase_examples, target_count))
    return sorted(balanced, key=lambda item: (item.source_file, item.anchor_timestamp, item.phase_id))


def save_split(
    *,
    split_name: str,
    examples: list[SequenceExample],
    data_dir: Path,
) -> pd.DataFrame:
    sequence_dir = data_dir / "sequences" / split_name
    sequence_dir.mkdir(parents=True, exist_ok=True)
    confusing_tail_phase = {
        0: 3,
        1: 2,
        2: 1,
        3: 0,
    }
    examples_by_phase: dict[int, list[SequenceExample]] = {}
    for example in examples:
        examples_by_phase.setdefault(int(example.phase_id), []).append(example)

    rows: list[dict[str, object]] = []
    for index, example in enumerate(examples):
        sequence_id = f"{split_name}_sequence_{index:05d}"
        filename = f"{sequence_id}.npy"
        sequence_path = sequence_dir / filename
        valid_length = int(example.sequence_length)
        storage_extra = STORAGE_EXTRA_CHOICES[(index + int(example.phase_id)) % len(STORAGE_EXTRA_CHOICES)]
        storage_length = min(PADDED_STORAGE_LENGTH, valid_length + storage_extra)
        storage = np.zeros((storage_length, example.sequence.shape[1]), dtype=np.float32)
        storage[:valid_length] = example.sequence.astype(np.float32)
        tail_length = storage_length - valid_length
        if tail_length > 0:
            donor_pool = examples_by_phase[confusing_tail_phase[int(example.phase_id)]]
            donor = donor_pool[(index * 37 + valid_length * 11 + int(example.phase_id)) % len(donor_pool)]
            donor_sequence = donor.sequence.astype(np.float32)
            if len(donor_sequence) >= tail_length:
                tail = donor_sequence[-tail_length:]
            else:
                repeats = (tail_length + len(donor_sequence) - 1) // len(donor_sequence)
                tail = np.tile(donor_sequence, (repeats, 1))[:tail_length]
            storage[valid_length:] = tail
        np.save(sequence_path, storage)
        rows.append(
            {
                "sequence_id": sequence_id,
                "sequence_path": str(Path("sequences") / split_name / filename),
                "source_file": example.source_file,
                "anchor_timestamp": example.anchor_timestamp,
                "sequence_length": int(example.sequence_length),
                "phase_id": int(example.phase_id),
                "phase_label": PHASE_MAP[int(example.phase_id)],
            }
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(data_dir / f"{split_name}_index.csv", index=False)
    return frame


def count_by_source_and_phase(index_frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    grouped = index_frame.groupby(["source_file", "phase_label"]).size()
    output: dict[str, dict[str, int]] = {}
    for (source_file, phase_label), count in grouped.items():
        output.setdefault(str(source_file), {})[str(phase_label)] = int(count)
    return output


def main() -> None:
    environment_dir = Path(__file__).resolve().parent
    data_dir = environment_dir / "data" / DATASET_DIRNAME
    data_dir.mkdir(parents=True, exist_ok=True)
    if prepared_snapshot_exists(data_dir):
        return

    raw_dir = data_dir / "raw"
    archive_path = raw_dir / "occupancy_detection.zip"
    payload = download_zip(archive_path)

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        development_frame = pd.concat(
            [
                add_time_features(load_frame(archive, "datatraining.txt")),
                add_time_features(load_frame(archive, "datatest.txt")),
            ],
            ignore_index=True,
        )
        holdout_frame = add_time_features(load_frame(archive, "datatest2.txt"))

    development_examples = balance_by_source(build_candidates(development_frame))
    holdout_examples = balance_by_source(build_candidates(holdout_frame))
    development_index = save_split(split_name="development", examples=development_examples, data_dir=data_dir)
    holdout_index = save_split(split_name="holdout", examples=holdout_examples, data_dir=data_dir)

    feature_columns = FEATURE_COLUMNS + DERIVED_COLUMNS
    (data_dir / "feature_names.txt").write_text("\n".join(feature_columns) + "\n", encoding="utf-8")
    (data_dir / "phase_mapping.json").write_text(
        json.dumps({str(key): value for key, value in PHASE_MAP.items()}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (data_dir / "source_metadata.json").write_text(
        json.dumps(
            {
                "source_page_url": SOURCE_PAGE_URL,
                "source_zip_url": SOURCE_ZIP_URL,
                "zip_sha256": hashlib.sha256(payload).hexdigest(),
                "development_sources": ["datatraining.txt", "datatest.txt"],
                "holdout_source": "datatest2.txt",
                "feature_columns": feature_columns,
                "phase_mapping": {str(key): value for key, value in PHASE_MAP.items()},
                "sequence_length_choices": WINDOW_LENGTH_CHOICES,
                "max_sequence_length": MAX_SEQUENCE_LENGTH,
                "storage_sequence_length_max": PADDED_STORAGE_LENGTH,
                "storage_sequence_length_choices": sorted({length + extra for length in WINDOW_LENGTH_CHOICES for extra in STORAGE_EXTRA_CHOICES}),
                "anchor_stride_rows": ANCHOR_STRIDE,
                "development_examples": int(len(development_index)),
                "holdout_examples": int(len(holdout_index)),
                "development_counts_by_source_and_phase": count_by_source_and_phase(development_index),
                "holdout_counts_by_source_and_phase": count_by_source_and_phase(holdout_index),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
