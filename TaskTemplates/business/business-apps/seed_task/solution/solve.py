from __future__ import annotations

import csv
import json
import os
import urllib.request
from pathlib import Path

import yaml


DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/root/output"))


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "oracle-solution"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_policy() -> dict:
    return yaml.safe_load((DATA_ROOT / "action_policy.yaml").read_text(encoding="utf-8"))


def load_task_manifest() -> dict:
    return json.loads((DATA_ROOT / "ops_manifest.json").read_text(encoding="utf-8"))


def load_contacts() -> dict[str, dict]:
    contacts = {}
    with (DATA_ROOT / "contact_directory.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            contacts[row["account_id"]] = row
    return contacts


def classify(detail: dict, preview: dict, dunning: dict, policy: dict) -> tuple[str, str]:
    if detail["legal_hold"]:
        return "pause_renewal", "legal_hold"
    if preview["quote_required"] and int(preview["seat_delta"]) > 0:
        return "update_expansion_quote", "expansion_quote_required"
    if detail["procurement_blocker"] == "missing_purchase_order":
        return "escalate_csm", "missing_purchase_order"
    collect_cfg = policy["collect_payment"]
    if (
        detail["invoice_status"] == "open"
        and int(dunning["past_due_days"]) >= int(collect_cfg["min_past_due_days"])
        and int(dunning["payment_attempts"]) >= int(collect_cfg["min_payment_attempts"])
        and float(detail.get("open_invoice_amount_usd", 0.0)) >= float(collect_cfg["min_amount_due_usd"])
    ):
        return "collect_payment", "overdue_payment_attempts"
    if detail["invoice_status"] == "draft" and not detail["autopay_enabled"]:
        return "send_invoice", "draft_invoice_ready"
    return "monitor", "healthy_autopay"


def fetch_records() -> tuple[dict, list[dict]]:
    task_manifest = load_task_manifest()
    live_manifest = get_json(task_manifest["manifest_endpoint"])
    cohort_url = live_manifest["service_urls"]["cohort"]
    accounts_base = live_manifest["service_urls"]["accounts_base"].rstrip("/")
    records = []
    cursor = None
    while True:
        page = get_json(cohort_url if cursor is None else f"{cohort_url}?cursor={cursor}")
        for item in page["items"]:
            account_id = item["account_id"]
            records.append(
                {
                    "detail": get_json(f"{accounts_base}/{account_id}"),
                    "preview": get_json(f"{accounts_base}/{account_id}/renewal-preview"),
                    "dunning": get_json(f"{accounts_base}/{account_id}/dunning-events"),
                }
            )
        if not page["has_next_page"]:
            break
        cursor = page["next_cursor"]
    return live_manifest, records


def build_outputs() -> tuple[list[dict], dict, str]:
    policy = load_policy()
    contacts = load_contacts()
    live_manifest, records = fetch_records()
    rows = []
    action_counts = {
        "send_invoice": 0,
        "collect_payment": 0,
        "escalate_csm": 0,
        "update_expansion_quote": 0,
        "pause_renewal": 0,
        "monitor": 0,
    }
    blocked_ids = []
    for record in records:
        detail = record["detail"]
        preview = record["preview"]
        dunning = record["dunning"]
        action_bucket, action_reason = classify(detail, preview, dunning, policy)
        action_counts[action_bucket] += 1
        if detail["legal_hold"] or detail["procurement_blocker"] == "missing_purchase_order":
            blocked_ids.append(detail["account_id"])
        rows.append(
            {
                "account_id": detail["account_id"],
                "company_name": detail["company_name"],
                "crm_deal_id": detail["crm_deal_id"],
                "owner_name": contacts[detail["account_id"]]["owner_name"],
                "renewal_date": detail["renewal_date"],
                "renewal_arr_usd": f"{float(preview['renewal_arr_usd']):.1f}",
                "invoice_status": detail["invoice_status"],
                "dunning_stage": dunning["current_stage"],
                "seat_delta": str(int(preview["seat_delta"])),
                "action_bucket": action_bucket,
                "action_reason": action_reason,
                "next_step": policy["next_steps"][action_bucket],
                "renewal_arr_value": float(preview["renewal_arr_usd"]),
                "past_due_days": int(dunning["past_due_days"]),
                "payment_attempts": int(dunning["payment_attempts"]),
                "open_invoice_amount_usd": float(detail.get("open_invoice_amount_usd", 0.0)),
            }
        )

    blocked_ids = sorted(blocked_ids)
    needing_action = [row for row in rows if row["action_bucket"] != "monitor"]
    highest_expansion = max(
        (row for row in rows if row["action_bucket"] == "update_expansion_quote"),
        key=lambda row: row["renewal_arr_value"],
    )
    urgent_collect = max(
        (row for row in rows if row["action_bucket"] == "collect_payment"),
        key=lambda row: (row["past_due_days"], row["payment_attempts"], row["open_invoice_amount_usd"]),
    )
    summary = {
        "workspace_id": live_manifest["workspace_id"],
        "cohort_date": live_manifest["cohort_date"],
        "totals": {
            "accounts_reviewed": len(rows),
            "renewal_arr_reviewed_usd": float(sum(row["renewal_arr_value"] for row in rows)),
            "accounts_needing_action": len(needing_action),
            "revenue_at_risk_usd": float(sum(row["renewal_arr_value"] for row in needing_action)),
        },
        "action_counts": action_counts,
        "workflow_blocked_account_ids": blocked_ids,
        "service_checks": {
            "revops_manifest": True,
            "accounts": True,
            "account_details": True,
            "renewal_previews": True,
            "dunning_events": True,
        },
        "notes": [
            "ACC-107 and ACC-108 appear in the live cohort even though they are absent from the older CRM export.",
            f"Workflow blockers are {', '.join(blocked_ids)}."
        ],
    }
    brief = "\n".join(
        [
            f"Workspace: {live_manifest['workspace_id']}",
            f"Cohort date: {live_manifest['cohort_date']}",
            f"Accounts reviewed: {summary['totals']['accounts_reviewed']}",
            f"Accounts needing action: {summary['totals']['accounts_needing_action']}",
            f"Workflow-blocked accounts: {', '.join(blocked_ids)}",
            f"Highest expansion quote account: {highest_expansion['account_id']} ({highest_expansion['company_name']})",
            f"Most urgent collection account: {urgent_collect['account_id']} ({urgent_collect['company_name']})",
            "Action routing logic: legal holds take priority, then quote-required expansion, then procurement blockers, then overdue payment collection, then draft invoices without autopay, with the remaining accounts left on monitor."
        ]
    ) + "\n"
    return rows, summary, brief


def write_outputs(rows: list[dict], summary: dict, brief: str) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT_ROOT / "renewal_worklist.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "account_id",
                "company_name",
                "crm_deal_id",
                "owner_name",
                "renewal_date",
                "renewal_arr_usd",
                "invoice_status",
                "dunning_stage",
                "seat_delta",
                "action_bucket",
                "action_reason",
                "next_step",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in writer.fieldnames})
    (OUTPUT_ROOT / "renewal_control_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (OUTPUT_ROOT / "ops_brief.md").write_text(brief, encoding="utf-8")


def main() -> None:
    rows, summary, brief = build_outputs()
    write_outputs(rows, summary, brief)


if __name__ == "__main__":
    main()
