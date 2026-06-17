#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_root = Path(args.data)
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)
    raise SystemExit(
        f"run_marine_heat_intake.py is still a starter script. "
        f"Implement the intake pipeline for {data_root} and write the required outputs to {output_root}. "
        f"Run the local preflight probe at /root/workspace/probe_intake.py when it is available and use its JSON output as the output-conventions contract."
    )


if __name__ == "__main__":
    main()
