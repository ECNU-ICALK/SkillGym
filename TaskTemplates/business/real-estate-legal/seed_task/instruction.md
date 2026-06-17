You need to prepare a pre-auction review package for a distressed-asset investment team for a single asset, to be delivered to this week's investment committee. The container already includes scraped public materials, plus an older internal summary and an older cost sheet; these older exports may be incomplete or based on outdated definitions. For this delivery, the current in-container local service definitions provided via `job_manifest.json` are authoritative.

Input data is under `/root/data/`:

- `job_manifest.json`: target asset ID, delivery requirements, output files, and the local service URL.
- `source_notice_batch.pdf`: the official notice PDF for this batch.
- `source_notice_excerpt.pdf`: excerpt pages for faster verification.
- `source_itbi_sp.html`: a snapshot of the Sao Paulo ITBI page.
- `source_fiduciary_law.html`: a snapshot of legal text related to the foreclosure auction process.
- `source_cpc.html`: a snapshot of legal text related to auction procedure.
- `source_listing_snapshot.html`: an older saved snapshot of an external listing page, for background reference only.
- `stale_notice_summary.json`: an older exported internal summary that may be incomplete or outdated.
- `stale_cost_sheet.csv`: an older exported cost assumptions sheet that may not match the current definitions.

Your tasks

1. Produce a structured extraction of key notice facts for the target asset, covering the critical information needed for investment committee review.
2. Produce a risk register for the target asset, clearly stating the main risks, risk levels, evidence sources, and brief explanations.
3. Based on the current pricing basis, calculate the primary cash outlays required for the buyer to complete the transaction.
4. Write a short conclusion memo for the investment committee stating whether the asset should proceed to bidding, and the core rationale.

Output

If `/root/output/` does not exist, create it first.

1. Write `/root/output/notice_extract.json`

Top-level fields must be exactly as follows:

```json
{
  "asset_id": "",
  "edital_id": "",
  "item_number": 0,
  "auction_type": "",
  "auctioneer_name": "",
  "auctioneer_registry": "",
  "first_auction_at": "",
  "second_auction_at": "",
  "appraisal_value_brl": 0.0,
  "first_min_bid_brl": 0.0,
  "second_min_bid_brl": 0.0,
  "payment_mode": [],
  "fgts_allowed": false,
  "financing_allowed": false,
  "address": "",
  "city": "",
  "state": "",
  "registry_office": "",
  "property_registry_number": "",
  "private_area_m2": 0.0,
  "total_area_m2": 0.0,
  "taxes_responsibility": "",
  "condo_responsibility": "",
  "encumbrance_notes": "",
  "regularization_notes": "",
  "publication_at": ""
}
```

Requirements:

- All fields must be filled. Do not write `null`, placeholder text, or an empty array.
- All amount and area fields must be numeric and keep 2 decimal places.
- `item_number` must be numeric.
- `payment_mode` must be an array of strings.
- Boolean fields must be boolean types.
- The result must match the current authoritative definitions.

2. Write `/root/output/risk_register.csv`

Column names must be exactly:

```csv
risk_code,risk_title,risk_level,evidence_source,summary
```

Requirements:

- Must cover all key risk items.
- `risk_level` must be one of `low`, `medium`, `high`.
- `evidence_source` must clearly state which input material or current authoritative definition the evidence comes from.
- `summary` must be a brief explanation; it must not be just keywords.
- Risks should cover key issues that could affect the bidding decision, transaction costs, and subsequent holding or disposal plans.

3. Write `/root/output/cash_requirements.json`

Top-level fields must be exactly as follows:

```json
{
  "asset_id": "",
  "pricing_basis": "",
  "min_bid_brl": 0.0,
  "auctioneer_fee_brl": 0.0,
  "itbi_rate_pct": 0.0,
  "itbi_brl": 0.0,
  "registry_cost_brl": 0.0,
  "modeled_tax_debts_brl": 0.0,
  "modeled_condo_debts_brl": 0.0,
  "modeled_regularization_brl": 0.0,
  "total_cash_out_brl": 0.0,
  "cash_only_flag": false,
  "financing_flag": false,
  "fgts_flag": false
}
```

Requirements:

- All amount and rate fields must be numeric and keep 2 decimal places.
- `pricing_basis` must clearly describe which basis is used for this calculation.
- `total_cash_out_brl` must equal the sum of the components according to the current definitions.
- Boolean fields must be consistent with the current notice conditions and cost definitions.
- You must not skip taxes, fees, registry costs, or any items that the rules require the buyer to bear.

4. Write `/root/output/investment_committee_memo.md`

The content must include the following level-1 headings, in this exact order:

- `# Executive Summary`
- `# Auction Facts`
- `# Risks`
- `# Cash Requirement`
- `# Recommendation`

Requirements:

- Must reference key facts, risks, and amounts that are consistent with the JSON/CSV outputs above.
- In `# Recommendation`, you must explicitly state exactly one of the following conclusions:
  - `BID`
  - `WATCH_ONLY`
  - `NO_BID`
- Must explain the main rationale for the conclusion, and must mention at least one risk and one cash constraint.
- The memo should be written for investment committee readers: concise and actionable.

Notes:

- The current in-container local service definitions take priority over the older exported summary and cost sheet.
- `stale_notice_summary.json` and `stale_cost_sheet.csv` are for reference only.
- Do not modify any input files under `/root/data/`.
- Do not stop, replace, or bypass the in-container service.
- Do not use cached answers, hard-coded results, or manually assembled placeholder content instead of doing the verification work.
- Do not remove risk items, fee items, or deliverable files, and do not evade review by modifying the environment.
- Do not modify tests, verifier files, skill files, or environment files.
- You may write helper scripts in the working directory, but the only required deliverables are the 4 files under `/root/output/`.
