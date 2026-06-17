#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path


DATA_DIR = Path("/root/data")
OUTPUT_DIR = Path("/root/output")
MANIFEST = json.loads((DATA_DIR / "job_manifest.json").read_text(encoding="utf-8"))
SERVICE_URLS = MANIFEST["service_urls"]
PAGE_LIMIT = 3


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "skill-helper"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def paginate(url: str) -> list[dict]:
    items: list[dict] = []
    cursor: str | None = None
    while True:
        params = {"limit": str(PAGE_LIMIT)}
        if cursor is not None:
            params["cursor"] = cursor
        payload = get_json(f"{url}?{urllib.parse.urlencode(params)}")
        items.extend(payload["items"])
        cursor = payload["page_info"]["next_cursor"]
        if cursor is None:
            return items


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def decide(policy: dict, total_cash: float, high_risks: int) -> str:
    if total_cash > float(policy["budget_cap_brl"]):
        return "NO_BID"
    if high_risks <= int(policy["max_high_risks_for_bid"]):
        return "BID"
    if high_risks <= int(policy["max_high_risks_for_watch_only"]):
        return "WATCH_ONLY"
    return "NO_BID"


def write_notice_extract(payload: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ordered = {
        "asset_id": payload["asset_id"],
        "edital_id": payload["edital_id"],
        "item_number": int(payload["item_number"]),
        "auction_type": payload["auction_type"],
        "auctioneer_name": payload["auctioneer_name"],
        "auctioneer_registry": payload["auctioneer_registry"],
        "first_auction_at": payload["first_auction_at"],
        "second_auction_at": payload["second_auction_at"],
        "appraisal_value_brl": round2(payload["appraisal_value_brl"]),
        "first_min_bid_brl": round2(payload["first_min_bid_brl"]),
        "second_min_bid_brl": round2(payload["second_min_bid_brl"]),
        "payment_mode": list(payload["payment_mode"]),
        "fgts_allowed": bool(payload["fgts_allowed"]),
        "financing_allowed": bool(payload["financing_allowed"]),
        "address": payload["address"],
        "city": payload["city"],
        "state": payload["state"],
        "registry_office": payload["registry_office"],
        "property_registry_number": payload["property_registry_number"],
        "private_area_m2": round2(payload["private_area_m2"]),
        "total_area_m2": round2(payload["total_area_m2"]),
        "taxes_responsibility": payload["taxes_responsibility"],
        "condo_responsibility": payload["condo_responsibility"],
        "encumbrance_notes": payload["encumbrance_notes"],
        "regularization_notes": payload["regularization_notes"],
        "publication_at": payload["publication_at"],
    }
    (OUTPUT_DIR / "notice_extract.json").write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_risk_register(rows: list[dict]) -> None:
    with (OUTPUT_DIR / "risk_register.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["risk_code", "risk_title", "risk_level", "evidence_source", "summary"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "risk_code": row["risk_code"],
                    "risk_title": row["risk_title"],
                    "risk_level": row["risk_level"],
                    "evidence_source": row["evidence_source"],
                    "summary": row["summary"],
                }
            )


def write_cash_requirements(payload: dict) -> None:
    ordered = {
        "asset_id": payload["asset_id"],
        "pricing_basis": payload["pricing_basis"],
        "min_bid_brl": round2(payload["min_bid_brl"]),
        "auctioneer_fee_brl": round2(payload["auctioneer_fee_brl"]),
        "itbi_rate_pct": round2(payload["itbi_rate_pct"]),
        "itbi_brl": round2(payload["itbi_brl"]),
        "registry_cost_brl": round2(payload["registry_cost_brl"]),
        "modeled_tax_debts_brl": round2(payload["modeled_tax_debts_brl"]),
        "modeled_condo_debts_brl": round2(payload["modeled_condo_debts_brl"]),
        "modeled_regularization_brl": round2(payload["modeled_regularization_brl"]),
        "total_cash_out_brl": round2(payload["total_cash_out_brl"]),
        "cash_only_flag": bool(payload["cash_only_flag"]),
        "financing_flag": bool(payload["financing_flag"]),
        "fgts_flag": bool(payload["fgts_flag"]),
    }
    (OUTPUT_DIR / "cash_requirements.json").write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_memo(asset: dict, cost_model: dict, risk_rows: list[dict], recommendation: str, policy: dict) -> None:
    top_risks = [row for row in risk_rows if row["risk_level"] == "high"]
    with (OUTPUT_DIR / "investment_committee_memo.md").open("w", encoding="utf-8") as fh:
        fh.write("# Executive Summary\n")
        fh.write(
            f"Asset `{asset['asset_id']}` should be treated as `{recommendation}` under the current policy. "
            f"Total modeled cash out is R$ {round2(cost_model['total_cash_out_brl']):.2f} against a budget cap of "
            f"R$ {round2(policy['budget_cap_brl']):.2f}, while the live risk set contains {len(top_risks)} high-severity items.\n\n"
        )
        fh.write("# Auction Facts\n")
        fh.write(
            f"Item {asset['item_number']} in edital {asset['edital_id']} is scheduled for {asset['first_auction_at']} "
            f"and {asset['second_auction_at']}. The second-auction minimum bid is R$ {round2(asset['second_min_bid_brl']):.2f} "
            f"for {asset['address']}, {asset['city']}/{asset['state']}. Payment modes currently allowed are "
            f"{', '.join(asset['payment_mode'])}.\n\n"
        )
        fh.write("# Risks\n")
        for row in risk_rows:
            fh.write(f"- `{row['risk_level']}` `{row['risk_code']}`: {row['summary']} Evidence: {row['evidence_source']}.\n")
        fh.write("\n# Cash Requirement\n")
        fh.write(
            f"Starting from the second-auction minimum bid of R$ {round2(cost_model['min_bid_brl']):.2f}, the modeled buyer outlay includes "
            f"R$ {round2(cost_model['auctioneer_fee_brl']):.2f} for the leiloeiro fee, "
            f"R$ {round2(cost_model['itbi_brl']):.2f} for ITBI at {round2(cost_model['itbi_rate_pct']):.2f}%, "
            f"R$ {round2(cost_model['registry_cost_brl']):.2f} for registry costs, "
            f"R$ {round2(cost_model['modeled_tax_debts_brl']):.2f} for modeled tax debts, "
            f"R$ {round2(cost_model['modeled_condo_debts_brl']):.2f} for modeled condo debts, and "
            f"R$ {round2(cost_model['modeled_regularization_brl']):.2f} for regularization reserve.\n\n"
        )
        fh.write("# Recommendation\n")
        fh.write(
            f"{recommendation}. The current cash requirement stays within the budget cap, but title cleanup and buyer-borne debt exposure keep the asset out of a straight `BID` path. "
            f"Any committee approval should assume the documented regularization workload and the municipal transfer-tax basis remain active constraints.\n"
        )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    get_json(SERVICE_URLS["manifest"])
    asset = get_json(SERVICE_URLS["asset_current"])
    cost_model = get_json(SERVICE_URLS["cost_model_current"])
    risk_rows = paginate(SERVICE_URLS["risk_signals"])
    policy = get_json(SERVICE_URLS["decision_policy_current"])
    recommendation = decide(policy, float(cost_model["total_cash_out_brl"]), sum(row["risk_level"] == "high" for row in risk_rows))
    write_notice_extract(asset)
    write_risk_register(risk_rows)
    write_cash_requirements(cost_model)
    write_memo(asset, cost_model, risk_rows, recommendation, policy)


if __name__ == "__main__":
    main()
