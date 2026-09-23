#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the engineering release digest.")
    parser.add_argument("--bundle-root", default="/app/release-watch")
    parser.add_argument("--workspace-root", default="/app/workspace")
    parser.add_argument("--output-root", default="/app/output")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def replace_block(text: str, tier: str, lines: list[str]) -> str:
    start_marker = f"<!-- DIGEST-START:{tier} -->"
    end_marker = f"<!-- DIGEST-END:{tier} -->"
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker)
    return text[:start] + "\n" + "\n".join(lines) + "\n" + text[end:]


def main() -> int:
    args = parse_args()
    bundle_root = Path(args.bundle_root)
    workspace_root = Path(args.workspace_root)
    output_root = Path(args.output_root)

    contract = load_json(bundle_root / "contracts" / "digest_contract.json")
    draft_path = bundle_root / "drafts" / contract["output_file"]
    state_db_path = workspace_root / contract["state_db_file"]
    audit_log_path = workspace_root / contract["audit_log_file"]
    reopen_state_path = workspace_root / contract["reopen_state_file"]

    output_root.mkdir(parents=True, exist_ok=True)

    raise RuntimeError(
        "The release-watch build entrypoint still needs the local tracker reconciliation, scan, "
        f"delivery selection, digest rendering, and workspace state updates for {draft_path.name} "
        f"using {state_db_path.name}, {audit_log_path.name}, and {reopen_state_path.name}."
    )


if __name__ == "__main__":
    raise SystemExit(main())
