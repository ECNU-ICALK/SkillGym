You are preparing a token onboarding review package for a yield vault protocol that plans to accept several ERC-20 assets as collateral. The protocol team has already staged the vault and router contracts, candidate token behavior profiles, the onboarding policy, and the output contract in the local environment, but the final review package has not been delivered.

Input data are available in:
- `/root/environment/protocol/contracts/`: Solidity contracts for the vault, router, registry, and supporting libraries
- `/root/environment/data/token_profiles/`: candidate token behavior profiles and metadata snapshots
- `/root/environment/data/reference/`: standards extracts, integration notes, and behavior reference material
- `/root/environment/data/listing_policy.json`: onboarding policy, decision values, required measure names, output vocabularies, and consistency rules
- `/root/environment/pipeline/`: formal review entrypoint and helper code

Your task:
1. Build the end-to-end review workflow from the shipped contracts, token profiles, reference material, and onboarding policy.
2. For every candidate token, determine the protocol-relevant compatibility and operational risks that affect collateral onboarding.
3. Apply the shipped onboarding policy to assign one final decision per token and keep that decision consistent across all deliverables.
4. Map each candidate token to the protocol-side measures it requires, and identify whether the shipped contracts already cover those measures.
5. Keep the formal pipeline usable. After your changes, `python /root/environment/pipeline/run_token_onboarding_review.py --output /root/answer` must regenerate the full deliverable set.
6. If you add helper scripts or working notes, the formal deliverables still need to be written by the shipped pipeline entrypoint.

Outputs:
- `/root/answer/token_onboarding_review.md`
  - must contain the headings: `Scope`, `Protocol context`, `Candidate decisions`, `Coverage summary`, `Evidence notes`

- `/root/answer/token_decisions.tsv`
  - columns: `token_id`, `symbol`, `decision`, `overall_risk`, `blocking_conditions`, `required_protocol_measures`, `evidence_refs`
  - `decision` must use the decision values from `listing_policy.json`
  - `required_protocol_measures` must join multiple values with `;`
  - `evidence_refs` must join multiple references with `;`

- `/root/answer/token_behavior_findings.tsv`
  - columns: `token_id`, `symbol`, `finding_id`, `finding_group`, `severity`, `integration_impact`, `protocol_requirement`, `evidence_refs`

- `/root/answer/guardrail_coverage.tsv`
  - columns: `measure_id`, `requirement`, `protocol_location`, `coverage_status`, `covered_tokens`, `evidence_refs`
  - `coverage_status` must use the allowed values from `listing_policy.json`
  - `covered_tokens` must join multiple token ids with `;`

- `/root/answer/evidence_index.json`
  - top-level keys must include: `protocol_files`, `candidate_tokens`, `decisions`, `coverage`, `notes`

Notes:
- `listing_policy.json` is the source of truth for decision values, allowed vocabularies, measure names, and consistency rules.
- Candidate tokens may share the same baseline ERC-20 interface while still requiring different onboarding outcomes.
- Keep token-level findings aligned across `token_decisions.tsv`, `token_behavior_findings.tsv`, `guardrail_coverage.tsv`, `evidence_index.json`, and `token_onboarding_review.md`.
- Do not hardcode final decisions, risk labels, behavior findings, coverage results, or evidence references.
- Do not replace the workflow with static files, copied artifacts, hand-written outputs, or shortcut scripts that bypass the formal pipeline entrypoint.
- Do not modify the shipped input data, tests, or `environment/skills`.
- You may add helper code, logs, or small utilities, but the final deliverables must be generated through the formal pipeline.
