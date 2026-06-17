You need to deliver a reusable Helm chart for a Harbor-style containerized service. The platform has already provided the application specification and the release requirements for two environments. The current repository only retains the chart skeleton and the rendering entrypoint, so it cannot yet be used directly for environment delivery. Your task is to complete this chart while preserving the existing directory structure and release entrypoint so it can generate contract-compliant release manifests for `staging` and `prod`.

Input data is in `/app/`:
- `workspace/chart/`: the current Helm chart working directory, containing the basic skeleton and a small number of placeholder files.
- `workspace/releases/`: the environment-level configuration directory, containing the release configuration skeletons for `staging` and `prod`.
- `data/app_contract.json`: the application contract covering image, ports, probes, environment variables, resource quotas, and upgrade constraints.
- `data/release_matrix.yaml`: the requirements for replica strategy, domains, exposure model, and scaling behavior for the two environments.
- `data/platform_labels.json`: the unified naming, labels, annotations, and selector constraints.
- `data/render_contract.json`: the contract for required resource kinds, names, and key fields after rendering in each environment.
- `workspace/scripts/render_release.sh`: the existing rendering entrypoint.

Your tasks
1. Complete a reusable Helm chart in `workspace/chart/` so it can generate the two release outputs for `staging` and `prod` from the environment configurations in `workspace/releases/`.
2. Make the rendered results correctly express application runtime behavior, service exposure, configuration injection, environment differences, and availability constraints according to the input contracts.
3. Preserve the configuration-driven delivery model so environment differences are expressed through the existing release configuration. Do not maintain separate unrelated static manifests for different environments.
4. Preserve the existing chart path and the `workspace/scripts/render_release.sh` entrypoint. Do not bypass the existing render chain, and do not rewrite the task into a one-off export of fixed results.
5. Keep the business boundary unchanged and continue using the existing input data and directory structure as the source of truth. Do not lower the difficulty by removing capabilities, modifying the input contracts, or replacing the release entrypoint.
6. Ensure this delivery remains reusable for the team after completion. Do not shrink the implementation into a specialized version that covers only a single environment, a single domain, or a single parameter set.

Output:
- `/app/workspace/chart/`: the completed Helm chart files.
- `/app/workspace/releases/`: the environment configuration files for `staging` and `prod`.
- All artifact files must be valid UTF-8, and the YAML must be directly readable by the existing rendering entrypoint.

Notes:
- You may add the necessary templates, configuration, and a small number of supporting files, but do not change the task goal.
- You may add a small number of publicly installable dependencies, but do not introduce components that require external private accounts, extra manual logins, or cluster-external permissions.
- Do not modify the input data under `/app/data/` to work around the requirements.
- Do not rewrite the task into manual manifest stitching, hard-coded rendered artifacts, static copies of expected outputs, or special-case implementations that work only for fixed samples.
- Do not split the work into two unrelated delivery structures, and do not disable the existing rendering entrypoint to force a pass.
