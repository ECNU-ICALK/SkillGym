#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the North America energy briefing packet.")
    parser.add_argument("--briefing-root", default="/app/briefing")
    parser.add_argument("--output-root", default="/app/output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    briefing_root = Path(args.briefing_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    draft = briefing_root / "drafts" / "briefing_draft.docx"
    output_docx = output_root / "north_america_energy_briefing.docx"
    shutil.copyfile(draft, output_docx)

    manifest = {
        "document_path": output_docx.name,
        "countries": ["Canada", "Mexico", "United States"],
        "source_files": [],
        "sections": [],
        "key_metrics": {
            "population_year": 0,
            "gdp_year": 0,
            "co2_year": 0,
            "electricity_year": 0
        },
        "notes": ["draft build output"]
    }
    (output_root / "briefing_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
