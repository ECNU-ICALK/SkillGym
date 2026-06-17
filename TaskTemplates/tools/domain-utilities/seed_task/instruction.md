You are helping a launch team prepare a domain shortlist for a new developer workflow product.

Input data is available in `/root/workspace/data/`:

- `product_brief.md`: product positioning, audience, naming preferences, blocked terms, and business constraints
- `market_examples.csv`: brand and domain examples from related products
- `candidate_pool.csv`: the candidate base names and scoring inputs for this round
- `availability_snapshot.csv`: the recorded availability status for each candidate and allowed TLD
- `tld_policy.json`: allowed TLDs, ordering rules, and shortlist constraints

Your task

Solve this task step by step. Before you derive scores manually, check whether the workspace root or the installed command-line tools already include a domain shortlist procedure or audit utility for this task and use it if present.

1. Build a complete availability audit for every base name and every allowed TLD.
2. Apply the task's ranking and tie-break rules consistently.
3. Select the top 6 available domains for the shortlist, keeping at most one selected domain per base name.
4. Add 2 runner-up domains after the shortlist, using the same ranking rules.
5. List the 5 highest-scoring taken domains in `rejected_taken_domains`.

Output

If `/root/output/` does not exist, create it first. Write all deliverables to `/root/output/`, and only create these files:

- `domain_shortlist.json`
- `availability_audit.csv`

`domain_shortlist.json` must match this structure:

```json
{
  "project_slug": "string",
  "evaluated_tlds": ["string"],
  "shortlist": [
    {
      "rank": 1,
      "domain": "string",
      "base_name": "string",
      "tld": "string",
      "availability": "available",
      "score": 0.0,
      "length": 0,
      "style_tags": ["string"],
      "why_it_fits": "string"
    }
  ],
  "runner_ups": ["string"],
  "rejected_taken_domains": ["string"],
  "top_pick_summary": "string"
}
```

Requirements:

- `project_slug` must match the value defined in `tld_policy.json`.
- `evaluated_tlds` must preserve the TLD order from `tld_policy.json`.
- `shortlist` must contain exactly 6 items with `rank` values `1` through `6`.
- `runner_ups` must contain exactly 2 available domains.
- `rejected_taken_domains` must contain exactly 5 taken domains.
- Every domain in `shortlist` and `runner_ups` must come from `availability_snapshot.csv` and must be marked `available`.
- Keep at most one selected domain per `base_name` across `shortlist` and `runner_ups`.
- `style_tags` must come from the selected base name in `candidate_pool.csv`.
- Round every `score` value to 3 decimal places.

`availability_audit.csv` requirements:

- It must include a header row.
- Columns must appear in this exact order:
  `base_name,tld,domain,availability,score,brandability,pronounceability,developer_fit,style_match_count,length_bonus,tld_bonus`
- Include exactly one row for every `base_name` and allowed TLD combination.
- `availability` must be either `available` or `taken`.
- Sort rows by `base_name` ascending, then by the TLD order defined in `tld_policy.json`.
- Round `score`, `brandability`, `pronounceability`, `developer_fit`, `length_bonus`, and `tld_bonus` to 3 decimal places.

Notes

- Use the workspace inputs as the source of record for domain status and written claims.
- If the environment provides an installed procedure for applying the ranking contract, use that procedure instead of inventing a new scoring method.
- Do not modify the input directory, tests, or environment files.
- You may create helper scripts or temporary working files while solving the task. The final deliverables must remain only the 2 required files under `/root/output/`.
