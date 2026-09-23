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
    req = urllib.request.Request(url, headers={"X-Client": "oracle-solution"})
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


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    get_json(SERVICE_URLS["manifest"])
    asset = get_json(SERVICE_URLS["asset_current"])
    cost_model = get_json(SERVICE_URLS["cost_model_current"])
    risk_rows = paginate(SERVICE_URLS["risk_signals"])
    policy = get_json(SERVICE_URLS["decision_policy_current"])
    recommendation = decide(policy, float(cost_model["total_cash_out_brl"]), sum(row["risk_level"] == "high" for row in risk_rows))

    notice_payload = {
        "asset_id": asset["asset_id"],
        "edital_id": asset["edital_id"],
        "item_number": int(asset["item_number"]),
        "auction_type": asset["auction_type"],
        "auctioneer_name": asset["auctioneer_name"],
        "auctioneer_registry": asset["auctioneer_registry"],
        "first_auction_at": asset["first_auction_at"],
        "second_auction_at": asset["second_auction_at"],
        "appraisal_value_brl": round2(asset["appraisal_value_brl"]),
        "first_min_bid_brl": round2(asset["first_min_bid_brl"]),
        "second_min_bid_brl": round2(asset["second_min_bid_brl"]),
        "payment_mode": list(asset["payment_mode"]),
        "fgts_allowed": bool(asset["fgts_allowed"]),
        "financing_allowed": bool(asset["financing_allowed"]),
        "address": asset["address"],
        "city": asset["city"],
        "state": asset["state"],
        "registry_office": asset["registry_office"],
        "property_registry_number": asset["property_registry_number"],
        "private_area_m2": round2(asset["private_area_m2"]),
        "total_area_m2": round2(asset["total_area_m2"]),
        "taxes_responsibility": asset["taxes_responsibility"],
        "condo_responsibility": asset["condo_responsibility"],
        "encumbrance_notes": asset["encumbrance_notes"],
        "regularization_notes": asset["regularization_notes"],
        "publication_at": asset["publication_at"],
    }
    (OUTPUT_DIR / "notice_extract.json").write_text(json.dumps(notice_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with (OUTPUT_DIR / "risk_register.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["risk_code", "risk_title", "risk_level", "evidence_source", "summary"])
        writer.writeheader()
        for row in risk_rows:
            writer.writerow(row)

    cash_payload = {
        "asset_id": cost_model["asset_id"],
        "pricing_basis": cost_model["pricing_basis"],
        "min_bid_brl": round2(cost_model["min_bid_brl"]),
        "auctioneer_fee_brl": round2(cost_model["auctioneer_fee_brl"]),
        "itbi_rate_pct": round2(cost_model["itbi_rate_pct"]),
        "itbi_brl": round2(cost_model["itbi_brl"]),
        "registry_cost_brl": round2(cost_model["registry_cost_brl"]),
        "modeled_tax_debts_brl": round2(cost_model["modeled_tax_debts_brl"]),
        "modeled_condo_debts_brl": round2(cost_model["modeled_condo_debts_brl"]),
        "modeled_regularization_brl": round2(cost_model["modeled_regularization_brl"]),
        "total_cash_out_brl": round2(cost_model["total_cash_out_brl"]),
        "cash_only_flag": bool(cost_model["cash_only_flag"]),
        "financing_flag": bool(cost_model["financing_flag"]),
        "fgts_flag": bool(cost_model["fgts_flag"]),
    }
    (OUTPUT_DIR / "cash_requirements.json").write_text(json.dumps(cash_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with (OUTPUT_DIR / "investment_committee_memo.md").open("w", encoding="utf-8") as fh:
        fh.write("# Executive Summary\n")
        fh.write(
            f"Asset `{asset['asset_id']}` should be treated as `{recommendation}`. Total modeled cash out is R$ {round2(cost_model['total_cash_out_brl']):.2f}, "
            f"and the live risk set contains {sum(row['risk_level'] == 'high' for row in risk_rows)} high-severity items.\n\n"
        )
        fh.write("# Auction Facts\n")
        fh.write(
            f"Item {asset['item_number']} in edital {asset['edital_id']} has a second-auction minimum bid of R$ {round2(asset['second_min_bid_brl']):.2f}. "
            f"The unit is located at {asset['address']}, {asset['city']}/{asset['state']}, and the current payment modes are {', '.join(asset['payment_mode'])}.\n\n"
        )
        fh.write("# Risks\n")
        for row in risk_rows:
            fh.write(f"- `{row['risk_level']}` `{row['risk_code']}`: {row['summary']} Evidence: {row['evidence_source']}.\n")
        fh.write("\n# Cash Requirement\n")
        fh.write(
            f"The modeled buyer cash package totals R$ {round2(cost_model['total_cash_out_brl']):.2f}, including the bid, leiloeiro fee, ITBI, registry costs, tax debt reserve, condo debt reserve, and regularization reserve.\n\n"
        )
        fh.write("# Recommendation\n")
        fh.write(
            f"{recommendation}. Budget room remains, but the title annotation, buyer-borne debt exposure, and regularization workload justify a cautious committee stance.\n"
        )


if __name__ == "__main__":
    main()
