#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


# Implement the packet from local inputs only.
# Keep output semantics aligned to the local contract instead of inventing a richer schema.
# Important reminders:
# - source_inventory.tsv stays limited to the contract source set
# - option_assessment.tsv stays inside the local status, score, and next-step model
# - decision_issues.tsv stays contract-defined rather than becoming a custom note set
# - assumption_audit.tsv stays compact and uses the contract layer/type labels verbatim
# - reuse local IDs and rule names verbatim when the data already provides them
# - decision_bundle.json artifacts stay as file names only, not absolute paths
# - decision_bundle.json stores required_controls as control IDs only

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

    brief = json.loads((data_root / "brief" / "committee_brief.json").read_text(encoding="utf-8"))
    options_path = data_root / "options" / "deployment_options.csv"

    with options_path.open("r", encoding="utf-8", newline="") as handle:
        options = list(csv.DictReader(handle))

    source_inventory = output_root / "source_inventory.tsv"
    source_inventory.write_text(
        "source_name\tpath\tsource_type\tcoverage\tnote\n"
        "committee_brief\t/root/data/brief/committee_brief.json\tjson\tboard scope\tstarter placeholder\n",
        encoding="utf-8",
    )

    (output_root / "option_assessment.tsv").write_text(
        "option_id\toutcome_id\tdecision_status\thard_fail_reasons\tgovernance_score\tdelivery_score\ttotal_score\tbudget_status\tdata_status\toversight_status\trecommended_next_step\n",
        encoding="utf-8",
    )
    (output_root / "decision_issues.tsv").write_text(
        "issue_id\tcategory\tstatus\tseverity\tlinked_option_ids\tevidence_ids\trequired_control\towner\tnext_review\n",
        encoding="utf-8",
    )
    (output_root / "assumption_audit.tsv").write_text(
        "assumption_id\tlayer\tassumption_type\tassumption_statement\tfragility\timpact\trisk_score\tlinked_issue_id\tlinked_control_id\tverification_question\n",
        encoding="utf-8",
    )
    (output_root / "safeguard_plan.yaml").write_text("selected_option_id: null\ncontrols: []\n", encoding="utf-8")

    selected = options[0] if options else {"outcome_id": "", "option_id": ""}
    bundle = {
        "selected_outcome": selected.get("outcome_id"),
        "selected_option_id": selected.get("option_id"),
        "rejected_outcomes": [row.get("outcome_id") for row in options[1:]],
        "required_controls": [],
        "open_questions": [],
        "artifacts": [
            "decision_memo.md",
            "source_inventory.tsv",
            "option_assessment.tsv",
            "decision_issues.tsv",
            "assumption_audit.tsv",
            "safeguard_plan.yaml",
            "decision_bundle.json",
        ],
    }
    (output_root / "decision_bundle.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    memo = "\n".join(
        [
            "# Scope",
            f"- District: {brief['district_name']}",
            "",
            "# Recommendation",
            "Placeholder recommendation.",
            "",
            "# Option comparison",
            "Placeholder comparison.",
            "",
            "# Controls",
            "Placeholder controls.",
            "",
            "# Open questions",
            "Placeholder open questions.",
            "",
        ]
    )
    (output_root / "decision_memo.md").write_text(memo, encoding="utf-8")


if __name__ == "__main__":
    main()
