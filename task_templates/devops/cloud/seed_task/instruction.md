You need to build a reusable Terraform VPC module library for the platform infrastructure team. The current repository already has `staging` and `prod` environments maintaining their own network resource definitions, but they suffer from duplicated implementations, inconsistent interfaces, inconsistent tags, and scattered EKS integration requirements, so the team can no longer reuse this capability as a shared module. Your task is to complete this module library while preserving the existing Terraform usage flow, and convert the current environments to consume network capability through the shared module.

Input data is in `/root/environment/`:
- `workspace/live/staging/`: the Terraform entrypoint and current environment configuration for `staging`.
- `workspace/live/prod/`: the Terraform entrypoint and current environment configuration for `prod`.
- `workspace/terraform-modules/aws/vpc/`: the shared module library skeleton, where this module must be completed.
- `workspace/examples/`: the module example directory skeleton.
- `workspace/scripts/`: the existing execution and validation entrypoints.
- `data/environment_blueprints/staging.json`: the network blueprint for the `staging` environment.
- `data/environment_blueprints/prod.json`: the network blueprint for the `prod` environment.
- `data/module_contract.json`: the input/output contract that the module must satisfy.
- `data/eks_subnet_tag_contract.json`: the subnet-tag contract for EKS integration requirements.
- `data/platform_tags.json`: the platform-wide tagging and naming constraints.

Your tasks
1. Build a reusable Terraform VPC module under `workspace/terraform-modules/aws/vpc/` so it can generate VPCs, subnets, route tables, gateways, and tag configurations that satisfy the contract based on the input data.
2. Complete the foundational structure that a shared module library should have for this module, including resource definitions, variable definitions, key outputs, version constraints, complete examples, and necessary documentation.
3. Keep `workspace/live/staging/` and `workspace/live/prod/` working through their existing Terraform entrypoints, but convert them to consume the same shared module instead of maintaining separate duplicated resource implementations.
4. Keep the module interface and environment-calling relationship clear and reusable. Do not turn the implementation into a specialized version that works only for a single environment.
5. Preserve the existing Terraform execution and validation entrypoints in the repository so this work continues along the current flow. Do not rewrite the task into manual static result generation, manual artifact stitching, or a direct bypass of Terraform evaluation.
6. The shared module should be abstracted from the local Terraform execution model that already exists in the current environments, rather than being replaced with another implementation that requires extra provider login or an external control plane.

Output:
- Directly modify the Terraform module files, environment invocation files, and any necessary supporting files under `/root/environment/workspace/`.
- Preserve the existing main entrypoints; validation will continue using the repository's existing Terraform execution and validation flow.
- After completion, the repository must behave as a structure of "shared Terraform module library + multi-environment consumers" rather than two separate environment script sets.

Notes:
- You may add the necessary Terraform files, examples, documentation, and testing support, but do not change the task goal.
- You may add a small number of publicly installable dependencies, but do not introduce components that require external private accounts, extra manual logins, or real cloud permissions.
- Preserve the current repository's locally runnable Terraform evaluation flow. Do not introduce an implementation that depends on real cloud credentials, real provider logins, or an external cloud control plane.
- Do not require the caller's root module to add extra cloud credentials or provider login configuration in order to complete `plan` in the local isolated environment.
- Do not modify the input data under `/root/environment/data/` to work around the problem.
- Replacing the real chain or removing functionality to avoid the problem is explicitly forbidden.
- Do not simply leave the resources in `live/staging` and `live/prod` in place and run them separately; they must consume capability through the shared module.
- Do not copy the resource definitions in the environment directories twice and then adjust them separately, and do not create a separate parallel module path for each environment.
- Do not turn the module into hard-coded outputs, static file generation, or a fake implementation that works only for fixed samples.
- Do not remove variable interfaces, output interfaces, examples, version constraints, or documentation to avoid the module-building requirements.
- Do not special-case only the current two environment blueprints; the module must demonstrate reusability.
