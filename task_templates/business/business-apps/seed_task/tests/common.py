from __future__ import annotations

import csv
import json
import os
import urllib.request
from pathlib import Path

import yaml


DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/root/output"))
WORKLIST_PATH = OUTPUT_ROOT / "renewal_worklist.csv"
SUMMARY_PATH = OUTPUT_ROOT / "renewal_control_summary.json"
BRIEF_PATH = OUTPUT_ROOT / "ops_brief.md"

WORKLIST_FIELDS = [
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
]


def get_json(url: str, client: str = "verifier-main") -> dict:
    req = urllib.request.Request(url, headers={"X-Client": client})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_task_manifest() -> dict:
    return json.loads((DATA_ROOT / "ops_manifest.json").read_text(encoding="utf-8"))


def load_policy() -> dict:
    return yaml.safe_load((DATA_ROOT / "action_policy.yaml").read_text(encoding="utf-8"))


def load_contacts() -> dict[str, dict]:
    contacts = {}
    with (DATA_ROOT / "contact_directory.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            contacts[row["account_id"]] = row
    return contacts


def fetch_live_manifest(client: str = "verifier-main") -> dict:
    task_manifest = load_task_manifest()
    return get_json(task_manifest["manifest_endpoint"], client=client)


def fetch_live_accounts(client: str = "verifier-main") -> list[dict]:
    manifest = fetch_live_manifest(client=client)
    cohort_url = manifest["service_urls"]["cohort"]
    accounts_base = manifest["service_urls"]["accounts_base"].rstrip("/")
    cursor = None
    records = []
    while True:
        page = get_json(cohort_url if cursor is None else f"{cohort_url}?cursor={cursor}", client=client)
        for item in page["items"]:
            account_id = item["account_id"]
            records.append(
                {
                    "detail": get_json(f"{accounts_base}/{account_id}", client=client),
                    "preview": get_json(f"{accounts_base}/{account_id}/renewal-preview", client=client),
                    "dunning": get_json(f"{accounts_base}/{account_id}/dunning-events", client=client),
                }
            )
        if not page["has_next_page"]:
            break
        cursor = page["next_cursor"]
    return records


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


def build_expected() -> dict:
    task_manifest = load_task_manifest()
    live_manifest = fetch_live_manifest()
    policy = load_policy()
    contacts = load_contacts()
    live_records = fetch_live_accounts()
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
    for record in live_records:
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
    expansion_rows = [row for row in rows if row["action_bucket"] == "update_expansion_quote"]
    collect_rows = [row for row in rows if row["action_bucket"] == "collect_payment"]
    highest_expansion = max(expansion_rows, key=lambda row: row["renewal_arr_value"]) if expansion_rows else None
    urgent_collect = max(
        collect_rows,
        key=lambda row: (row["past_due_days"], row["payment_attempts"], row["open_invoice_amount_usd"]),
    ) if collect_rows else None
    return {
        "task_manifest": task_manifest,
        "live_manifest": live_manifest,
        "rows": rows,
        "action_counts": action_counts,
        "blocked_ids": blocked_ids,
        "totals": {
            "accounts_reviewed": len(rows),
            "renewal_arr_reviewed_usd": float(sum(row["renewal_arr_value"] for row in rows)),
            "accounts_needing_action": len(needing_action),
            "revenue_at_risk_usd": float(sum(row["renewal_arr_value"] for row in needing_action)),
        },
        "highest_expansion": highest_expansion,
        "urgent_collect": urgent_collect,
    }


def load_worklist() -> list[dict]:
    with WORKLIST_PATH.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_summary() -> dict:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
