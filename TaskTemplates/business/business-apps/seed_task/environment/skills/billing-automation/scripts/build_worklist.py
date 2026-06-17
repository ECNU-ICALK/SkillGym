from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

import yaml


DATA_ROOT = Path("/root/data")


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "skill-build-worklist"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


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


def main() -> None:
    manifest = json.loads((DATA_ROOT / "ops_manifest.json").read_text(encoding="utf-8"))
    policy = yaml.safe_load((DATA_ROOT / "action_policy.yaml").read_text(encoding="utf-8"))
    contacts = load_contacts()
    live_manifest = get_json(manifest["manifest_endpoint"])
    cohort_url = live_manifest["service_urls"]["cohort"]
    accounts_base = live_manifest["service_urls"]["accounts_base"].rstrip("/")
    cursor = None
    rows = []
    while True:
        payload = get_json(cohort_url if cursor is None else f"{cohort_url}?cursor={cursor}")
        for item in payload["items"]:
            account_id = item["account_id"]
            detail = get_json(f"{accounts_base}/{account_id}")
            preview = get_json(f"{accounts_base}/{account_id}/renewal-preview")
            dunning = get_json(f"{accounts_base}/{account_id}/dunning-events")
            action_bucket, action_reason = classify(detail, preview, dunning, policy)
            rows.append(
                {
                    "account_id": account_id,
                    "company_name": detail["company_name"],
                    "crm_deal_id": detail["crm_deal_id"],
                    "owner_name": contacts[account_id]["owner_name"],
                    "renewal_date": detail["renewal_date"],
                    "renewal_arr_usd": preview["renewal_arr_usd"],
                    "invoice_status": detail["invoice_status"],
                    "dunning_stage": dunning["current_stage"],
                    "seat_delta": preview["seat_delta"],
                    "action_bucket": action_bucket,
                    "action_reason": action_reason,
                    "next_step": policy["next_steps"][action_bucket]
                }
            )
        if not payload["has_next_page"]:
            break
        cursor = payload["next_cursor"]
    print(json.dumps(rows, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
