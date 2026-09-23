You are preparing a board-ready decision packet for a public school district that is considering a generative AI writing support pilot for grades 9-12. The local workspace already contains the committee brief, candidate options, policy extracts, evidence summaries, stakeholder notes, and an export entrypoint. Your job is to complete the deliverables so the board can review one decision that is evidence-traceable and operationally usable.

Input data is in:

- `/root/data/brief/committee_brief.json`: board scope, allowed outcomes, budget cap, launch window, and non-negotiable operating constraints
- `/root/data/options/deployment_options.csv`: candidate pilot options and their operating characteristics
- `/root/data/policy/decision_contract.json`: output contract, scoring rules, required controls, and consistency rules
- `/root/data/policy/policy_clauses.json`: policy and governance requirements referenced by the board packet
- `/root/data/evidence/public_evidence.jsonl`: evidence summaries tied to the policy and rollout questions
- `/root/data/stakeholders/`: stakeholder notes that the packet must address
- `/root/data/reference/`: source index and public-reference extracts that support the local evidence pack
- `/root/workspace/`: export entrypoint and working area

Your task

1. Complete the decision packet using the provided local inputs.
2. Keep the recommendation inside the allowed outcomes from the committee brief and respect the non-negotiable constraints.
3. Make the packet traceable and operationally usable: the recommendation, option comparison, issue handling, controls, and remaining questions must agree with each other.
4. Keep the work local to the current environment. Do not rely on external web apps, logins, paid APIs, or changing third-party service state.
5. Leave the packet in a handoff-ready state so another reviewer can inspect the decision basis without additional explanation.

Output:

- Write all deliverables under `/root/output/`.
- Produce `/root/output/decision_memo.md` as UTF-8 Markdown.
  - It must contain the section headings `Scope`, `Recommendation`, `Option comparison`, `Controls`, and `Open questions`.
- Produce `/root/output/source_inventory.tsv` as UTF-8 TSV with these columns in this order:
  - `source_name`, `path`, `source_type`, `coverage`, `note`
- Produce `/root/output/option_assessment.tsv` as UTF-8 TSV with these columns in this order:
  - `option_id`, `outcome_id`, `decision_status`, `hard_fail_reasons`, `governance_score`, `delivery_score`, `total_score`, `budget_status`, `data_status`, `oversight_status`, `recommended_next_step`
- Produce `/root/output/decision_issues.tsv` as UTF-8 TSV with these columns in this order:
  - `issue_id`, `category`, `status`, `severity`, `linked_option_ids`, `evidence_ids`, `required_control`, `owner`, `next_review`
- Produce `/root/output/assumption_audit.tsv` as UTF-8 TSV with these columns in this order:
  - `assumption_id`, `layer`, `assumption_type`, `assumption_statement`, `fragility`, `impact`, `risk_score`, `linked_issue_id`, `linked_control_id`, `verification_question`
- Produce `/root/output/safeguard_plan.yaml` as UTF-8 YAML.
  - It must use these top-level keys only: `selected_option_id`, `controls`, `monitoring`, `manual_checks`.
- Produce `/root/output/decision_bundle.json` as UTF-8 JSON.
  - It must use these top-level keys only: `selected_outcome`, `selected_option_id`, `selected_option_name`, `rejected_outcomes`, `required_controls`, `open_questions`, `artifacts`.

Notes:

- Follow `/root/data/policy/decision_contract.json` for output semantics, consistency rules, and required control behavior.
- Treat `/root/data/policy/decision_contract.json` as the final authority for field meanings. When the local files already provide IDs, statuses, reason names, controls, or rule names, use those values verbatim.
- Use the option IDs and outcome IDs exactly as provided in the input files.
- Treat the local contract vocabulary as fixed. If the local files already define IDs, labels, controls, or rule names, keep them verbatim instead of inventing alternate terminology.
- Keep the source inventory closed to the local contract source set. Do not add extra source rows or replace the intended source names with a custom catalog.
- `option_assessment.tsv` is a contract-scoped comparison table. Keep its statuses, score fields, and next-step fields inside the local contract model instead of introducing a new rubric.
- `decision_issues.tsv` is a contract-defined governance issue table for the packet. Keep it rule-driven and contract-shaped instead of rewriting it into a custom note set or a single-option risk log.
- `assumption_audit.tsv` is the packet's assumption register. Keep it compact, use the contract layer and type labels verbatim, and make each verification question specific enough for a reviewer to act on it.
- Keep contract-driven IDs and status labels literal across the deliverables. Do not replace local labels with richer prose labels, percentage bands, or alternate scales.
- In `decision_bundle.json`, `required_controls` must be a list of control IDs. In `decision_issues.tsv`, `linked_option_ids` and `evidence_ids` must stay as comma-separated ID lists.
- Keep each deliverable thin and contract-shaped. `source_inventory.tsv` should stay at one row per listed source, `option_assessment.tsv` should stay inside the local scoring and status model, `decision_issues.tsv` should keep the contract-linked option set and evidence formatting, `assumption_audit.tsv` should stay row-oriented, `safeguard_plan.yaml` should include `monitoring` and `manual_checks`, and `decision_bundle.json` should not add extra wrapper metadata.
- In `safeguard_plan.yaml`, keep `monitoring` tied to the highest-risk assumptions that still require follow-up instead of turning it into a generic checklist.
- Keep the outputs schema-tight. Do not add extra top-level JSON keys, extra top-level YAML keys, or extra source rows outside the local contract source set.
- Keep the final packet grounded in the supplied local materials. Do not replace the deliverable with a general essay or a chat-style answer.
- Build the recommendation from the supplied premises only. Do not carry forward unsupported assumptions, outside policy frameworks, or a new scoring rubric that is not present in the local files.
- If a local read-only methodology pack is available under `/root/.codex/skills/`, inspect it before you lock the decision basis, then keep the required deliverables aligned to the local contract.
- You may add small helper files under `/root/workspace/` if needed, but the required outputs above remain the primary deliverables.
- Do not modify `/root/data/`, verifier files, or task metadata.
- Do not hardcode a final answer that ignores the committee brief, the option table, or the decision contract.
- The following command must succeed after your changes:

```bash
python /root/workspace/build_decision_packet.py --data /root/data --output /root/output
```
