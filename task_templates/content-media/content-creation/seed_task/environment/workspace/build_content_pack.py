#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Renewable Capacity Momentum 2025 publication pack.")
    parser.add_argument("--campaign-root", default="/app/campaign")
    parser.add_argument("--output-root", default="/app/output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    campaign_root = Path(args.campaign_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    raise RuntimeError(
        "The publication-pack build entrypoint still needs campaign parsing, channel-specific copy generation, "
        f"manifest assembly, and reproducible output writing using {campaign_root}."
    )


if __name__ == "__main__":
    raise SystemExit(main())
