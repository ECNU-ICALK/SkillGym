#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from occupancy_pipeline import train_and_export


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the official occupancy training and export pipeline.")
    parser.add_argument("--output", required=True, help="Directory where final deliverables must be written.")
    parser.add_argument(
        "--data-dir",
        default="/root/environment/data/phase_sequences",
        help="Prepared variable-length phase sequence dataset directory. Defaults to the bundled dataset path.",
    )
    parser.add_argument(
        "--contract-dir",
        default="/root/environment/data/contracts",
        help="Directory containing split and output contracts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_and_export(
        data_dir=Path(args.data_dir),
        contract_dir=Path(args.contract_dir),
        output_dir=Path(args.output),
    )


if __name__ == "__main__":
    main()
