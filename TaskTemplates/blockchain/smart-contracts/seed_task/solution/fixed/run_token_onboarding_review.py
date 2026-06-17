from __future__ import annotations

import argparse
import json
from pathlib import Path

from review_core import (
    assign_token_decisions,
    build_evidence_index,
    collect_behavior_findings,
    coverage_frame,
    decisions_frame,
    findings_frame,
    load_policy,
    load_token_profiles,
    scan_protocol_coverage,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Directory where deliverables will be written")
    parser.add_argument("--root", default="/root/environment")
    return parser.parse_args()


def build_review_markdown(policy: dict, decisions_df, coverage_df, findings_df) -> str:
    decision_lines = []
    for row in decisions_df.itertuples(index=False):
        measures = row.required_protocol_measures or "none"
        blockers = row.blocking_conditions or "none"
        decision_lines.append(
            f"- `{row.symbol}` (`{row.token_id}`): `{row.decision}` | risk=`{row.overall_risk}` | measures=`{measures}` | notes=`{blockers}`"
        )

    coverage_lines = []
    for row in coverage_df.itertuples(index=False):
        coverage_lines.append(
            f"- `{row.measure_id}`: `{row.coverage_status}` | covered tokens=`{row.covered_tokens or 'none'}`"
        )

    evidence_lines = []
    for row in findings_df.itertuples(index=False):
        evidence_lines.append(
            f"- `{row.symbol}` / `{row.finding_id}` -> `{row.protocol_requirement}` ({row.evidence_refs})"
        )

    sections = [
        "# Scope",
        f"Review candidate ERC-20 collateral for `{policy['protocol_name']}` using the shipped onboarding policy, token behavior profiles, and Solidity contracts.",
        "",
        "# Protocol context",
        "The vault allowlists collateral, normalizes non-18-decimal assets, uses SafeERC20-style transfer flows, and applies reentrancy protection on deposits. The shipped contracts do not include an explicit blocklist runbook or a balance-resynchronization path for rebasing assets.",
        "",
        "# Candidate decisions",
        *decision_lines,
        "",
        "# Coverage summary",
        *coverage_lines,
        "",
        "# Evidence notes",
        *evidence_lines,
    ]
    return "\n".join(sections) + "\n"


def main() -> None:
    args = parse_args()
    task_root = Path(args.root)
    data_root = task_root / "data"
    contracts_root = task_root / "protocol" / "contracts"
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    policy = load_policy(data_root)
    profiles = load_token_profiles(data_root)
    _, findings_by_token = collect_behavior_findings(policy, profiles)
    coverage = scan_protocol_coverage(policy, contracts_root, findings_by_token)
    decisions = assign_token_decisions(policy, profiles, findings_by_token, coverage)
    evidence = build_evidence_index(policy, profiles, decisions, coverage, contracts_root)

    decisions_df = decisions_frame(policy, decisions)
    findings_df = findings_frame(policy, findings_by_token, coverage)
    coverage_df = coverage_frame(policy, coverage)

    (output_root / "token_decisions.tsv").write_text(
        decisions_df.to_csv(sep="\t", index=False),
        encoding="utf-8",
    )
    (output_root / "token_behavior_findings.tsv").write_text(
        findings_df.to_csv(sep="\t", index=False),
        encoding="utf-8",
    )
    (output_root / "guardrail_coverage.tsv").write_text(
        coverage_df.to_csv(sep="\t", index=False),
        encoding="utf-8",
    )
    (output_root / "evidence_index.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_root / "token_onboarding_review.md").write_text(
        build_review_markdown(policy, decisions_df, coverage_df, findings_df),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
