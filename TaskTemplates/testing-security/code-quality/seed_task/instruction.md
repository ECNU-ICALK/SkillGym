You are preparing the release-readiness audit for a local toolchain digest package in `/app/workspace/`. The release manager needs one formal quality-gate audit artifact for the current candidate and tracked local change set.

Input data is under `/app/workspace/`:
- `package/`: the existing Node.js / TypeScript package with its scripts, tests, and local git metadata
- `data/npm/`: local npm-registry latest-package snapshots for the digest inputs
- `data/github/`: local GitHub release snapshots for the digest inputs
- `contracts/release_contract.json`: the required gate set, decision rules, and gate order for the audit
- `contracts/output_contract.json`: the JSON field contract for the final audit artifact
- `docs/release_brief.md`: business scope, artifact expectations, and limitation notes

Your task:
1. Use the repository's existing verification loop and promotion review commands to assess the current candidate and decide whether it is ready for promotion.
2. Cover every gate required by `release_contract.json`, and base each gate result on commands executed in this container session.
3. Write the final result to `/app/output/release_readiness_report.json` in the following format:

```json
{
  "project_id": "<project id>",
  "release_ready": false,
  "summary": "<short release summary>",
  "gates": [
    {
      "name": "<gate name>",
      "status": "pass",
      "command": "<executed command>",
      "evidence": "<concise evidence>",
      "blocking": false
    }
  ],
  "blocking_issues": [
    {
      "gate": "<gate name>",
      "summary": "<issue summary>"
    }
  ],
  "publishable_artifacts": [
    "<artifact path>"
  ]
}
```

Output:
- Only `/app/output/release_readiness_report.json` needs to be submitted
- The JSON must be valid UTF-8 and the field names must match the contract above exactly
- `gates` must cover every gate required by `release_contract.json`, in that file's order
- `status` must be either `pass` or `fail`
- `command` must identify the command actually used for that gate
- `blocking_issues` may be empty only when `release_ready` is `true`
- `publishable_artifacts` may be an empty array, but the field must remain present

Notes:
- Use the existing repository verification loop and workflow already provided in the container.
- Before running the audit, check whether a relevant local skill is available under `/root/.codex/skills/` and use it as read-only workflow guidance when present.
- Keep repository code, tests, contracts, package metadata, input snapshots, and git history unchanged.
- Leave every file outside `/app/output/` unchanged.
- Do not fabricate gate results, skip a required gate, or rely on cached summaries, old logs, or file timestamps as a substitute for current command results.
- Do not replace the packaged verification flow with a custom checker that bypasses the existing scripts.
- No additional output file is required beyond the JSON contract above.
