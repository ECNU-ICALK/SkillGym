You need to prepare a shippable hotfix release for the `meridian-hotfix` repository. In the current main working directory, there is already a set of in-progress audit changes that must not be disrupted by your fix; however, the hotfix pipeline in the same repository must be restored quickly, otherwise this release cannot proceed. Your task is to fix the hotfix pipeline and complete this delivery while preserving the existing git lineage, existing release entrypoints, and the preserved state of the main working directory.

Input data is available at paths visible within this container:
- `/app/repo/`: the git repository that needs fixing, including existing branches, tags, release scripts, the preserved working tree state, and the artifacts directory to be generated.
- `/root/data/hotfix_request.json`: the target version for this hotfix, the baseline release branch, the target hotfix branch name, and delivery requirements.
- `/root/data/changelog_fragments.ndjson`: the raw change fragments available for release notes.
- `/root/data/reference/`: public references for version-control workflows, commit conventions, and changelog guidance.

Your tasks
1. Prepare this hotfix based on the repository's existing git history, and fix code, scripts, or necessary documentation in the repo so the existing hotfix precheck and packaging pipeline becomes usable again.
2. Keep the current repository path, the existing release entrypoints, and the existing branch lineage; do not turn the task into copying the repo, rebuilding a parallel repository, exporting static results, or bypassing the existing git/history/script pipeline.
3. Keep the preserved audit changes in the main working directory usable; you must not "pass" by committing, discarding, overwriting, stashing, clearing, or moving away this preserved state.
4. Complete this hotfix via the real delivery chain: perform the fix based on the specified release branch's history relationship, generate official release notes, and produce the required delivery files.
5. All fixes must work within the current single-container environment; do not change the solution to depend on external GitHub, private accounts, remote pushes, manual approvals, or temporary external services.

Output
- Generate `artifacts/hotfix_report.json` in the working tree of the target hotfix branch.
- Generate `artifacts/release_notes.md` in the working tree of the target hotfix branch.
- `artifacts/hotfix_report.json` must be valid JSON.
- `artifacts/release_notes.md` must be valid Markdown text.

Notes
- It is explicitly forbidden to replace the real pipeline, remove functionality to evade issues, skip prechecks, skip packaging, skip release notes generation, change checks to always succeed, or directly fabricate `artifacts/hotfix_report.json` or `artifacts/release_notes.md`.
- Do not modify any input data under `/root/data/` to evade failures.
- Do not modify verifier, tests, task metadata, or skill files.
- Do not switch the main working directory to another branch and overwrite changes in-place, which would break the preserved working tree state.
- Do not rewrite the task into "only fix docs but not the pipeline", or "only generate result files but do not make the existing scripts actually work end-to-end".
