#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from reference_pipeline import write_outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    write_outputs(Path(args.data), Path(args.output), client="solver-reference")


if __name__ == "__main__":
    main()
