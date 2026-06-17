You need to complete a deliverable release automation solution for the `saturn-checkout` service. The current repository already retains the application source code, the container build entrypoint, the cluster deployment entrypoint, and the acceptance scripts, but the full automation chain from code changes to delivery artifacts has not yet been implemented according to this release contract. Your task is to complete this delivery while preserving the existing repository structure, script entrypoints, and release path.

Input data is in `/app/`:
- `workspace/repo/`: the service repository to be delivered, including the application source code, Dockerfile, base Kubernetes manifests, existing Makefile / scripts entrypoints, and the skeleton used to generate delivery artifacts.
- `data/pipeline_contract.json`: the automation-chain contract for this delivery, including trigger conditions, stage order, artifact requirements, concurrency constraints, and delivery naming rules.
- `data/environment_policy.json`: the rules for each delivery environment, including environment names, approval requirements, serialization constraints, and deployment windows.
- `data/rollout_policy.json`: the release-strategy rules, including traffic-shift steps, pause windows, health-check requirements, and rollback trigger conditions.
- `data/quality_gates.json`: requirements for build, test, scan, smoke, e2e, and other gates.
- `data/reference/`: reference materials compiled from public sources for automation configuration, image publishing, cluster release strategy, and security scanning.

Your tasks
1. Based on the repository's existing scripts and release entrypoints, complete the automation chain and supporting release configuration required for this delivery so that continuous validation, artifact building, pre-release verification, formal release, and post-release validation are connected according to the contract.
2. Preserve the current repository paths, existing build commands, existing release scripts, and existing cluster release entrypoints. Do not migrate to another delivery system, and do not rewrite this as a pure documentation answer, static answer, or bypass around the repository's existing command chain.
3. Keep the formal release flowing through the repository's existing release path, and satisfy the contract requirements for environments, approvals, serialization, traffic shifting, and health checks. The full release chain for the same delivery reference must also avoid parallel runs overwriting each other. Do not achieve passing results by removing stages, skipping gates, weakening release steps, or narrowing validation scope.
4. Ensure that this delivery can be validated within the current single-container environment. Do not introduce steps that depend on external private accounts, manual web logins, remote repository write access, or additional hosted platform state.
5. Let day-to-day change review and formal delivery continue to share the same validation standard, while keeping clear responsibility boundaries between the review path and the formal delivery path. The caller must continue to control runtime validation choices, and reusable entrypoints, input naming, and chaining methods must remain consistent with the contract. Do not secretly push runtime selection down into the callee or replace it with another naming scheme.
6. Make the delivered result complete enough for the team to take over. The related configuration, release manifests, and archived results should continue to serve future deliveries rather than shrinking into a one-off implementation aimed only at the current sample.
7. Keep the responsibility boundaries of the existing delivery entrypoints stable. The automation chain, release manifests, and final release summary must continue to work according to the contract's terminology. The final summary should remain a compact contract view, and stage-by-stage byproducts should remain in their corresponding workflows, release manifests, and environment summaries. Do not create a separate parallel summary chain to replace the existing repository entrypoints.
8. When the same delivery reference advances to later environments after release completion, continue using the same immutable image reference produced during the release stage. Do not reconstruct temporary tags per environment, fall back to `latest`, or switch to another image-naming convention.
9. Pre-release and production environment manifests must align with their respective delivery entrypoints. The production environment manifests must continue to reflect the formal release manifests themselves, and the related rendered artifacts must remain under `artifacts/` for later handoff and review.

Output:
- Directly modify the files under `/app/workspace/repo/` that relate to the automation chain, release configuration, and any necessary supporting scripts.
- Make the repository's existing delivery entrypoint produce `artifacts/release_bundle.json`, and keep it valid UTF-8 JSON.
- Validation will continue using the repository's existing scripts, automation configuration, and release manifests. The final repository must still behave as a deliverable service release scenario.

Notes:
- You may add the necessary automation configuration, reusable fragments, local scripts, config files, or release manifests, but do not change the task goal.
- If delivery workflows need access to repository contents, image registries, or artifact channels, explicitly declare the required permissions according to the contract. Do not leave key access capabilities to chance through default settings.
- Keep the review path within the shared validation scope. Artifact publishing, environment delivery, and the final release summary must advance only for formal delivery events. Do not advance to release stages early on the pull request path.
- If the shared validation entrypoint needs runtime parameters, use the contract's input keys and passing relationships directly. Do not wrap them in an extra relay naming layer to replace the contract terminology.
- Day-to-day branch and pull request change review must also remain attached to the shared validation chain, but the review path should carry validation responsibilities only and must not incidentally advance artifact publishing, environment delivery, or the release summary.
- In addition to being called by the main delivery chain, the shared validation entrypoint must also retain a directly invokable recheck entrypoint, using the same runtime input keys, so the team can re-verify before and after release with the same contract terms.
- If the shared validation entrypoint needs to reuse repository or artifact-channel context already present in the calling chain, continue using the caller's existing secret context. Do not split it into another separate credential interface on the callee side.
- After generating environment manifests during the formal release stage, you must still continue through the repository's existing post-release acceptance entrypoint. Do not shrink production delivery into manifest rendering only or summary upload only.
- Prioritize completing the automation chain and release manifests themselves. If the existing bundle entrypoint and release scripts can already carry the contract responsibilities, keep the final summary as a compact contract view and do not expand its output semantics unnecessarily.
- Archival output kept for the handoff team at the environment stage must cover both the environment summary and the rendered release manifests for that environment. Do not leave only a short overview text.
- The final summary entrypoint must continue to conclude based on the repository's current automation chain, shared validation entrypoint, and production release manifests. If those artifacts are disconnected from the contract, do not continue outputting a `ready` result.
- You may add a small number of publicly installable dependencies, but do not introduce components that require extra accounts, manual web operations, or external private services.
- Do not modify the input data under `/app/data/` to work around the requirements.
- Do not implement the result as hard-coded constants, a one-off script output, or a bypass implementation that only generates surface artifacts.
- Do not delete existing build, test, scan, pre-release, formal release, validation, or rollback entrypoints to lower the bar.
- Do not turn the repository into a single-stage automation flow only, or degrade the formal release into a direct push with no environment constraints, no approvals, and no validation.
- Do not write image publishing, release summary, traffic shifting, or health checks as special-case logic that works only for the current sample values.
- Do not modify verifier files, tests, task metadata, or skill files.
