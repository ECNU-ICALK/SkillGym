from __future__ import annotations

import argparse
import json
from pathlib import Path

from review_core import (
    assign_token_decisions,
    build_evidence_index,
    collect_behavior_findings,
    load_policy,
    load_token_profiles,
    scan_protocol_coverage,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Directory where deliverables will be written")
    parser.add_argument(
        "--root",
        default="/root/environment",
        help="Task root containing data/, protocol/, and pipeline/",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    task_root = Path(args.root)
    data_root = task_root / "data"
    contracts_root = task_root / "protocol" / "contracts"
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    policy = load_policy(data_root)
    profiles = load_token_profiles(data_root)

    findings = collect_behavior_findings(policy, profiles)
    coverage = scan_protocol_coverage(policy, contracts_root, findings)
    decisions = assign_token_decisions(policy, profiles, findings, coverage)
    evidence = build_evidence_index(policy, profiles, decisions, coverage, contracts_root)

    raise NotImplementedError(
        "Use policy, findings, coverage, decisions, and evidence to write the required review outputs."
    )


if __name__ == "__main__":
    main()
