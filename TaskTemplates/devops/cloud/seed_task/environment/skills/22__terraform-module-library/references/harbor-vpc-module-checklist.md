# Harbor VPC Module Checklist

Use this checklist when the task is to build a reusable Terraform VPC module that
must stay locally plannable without cloud credentials.

## Root shape

- Keep `live/staging` and `live/prod` as thin callers with a single `module "vpc"`
  block that points at `../../terraform-modules/aws/vpc`.
- Keep the caller contract limited to the documented module inputs already present
  in the root variables and tfvars files.
- Add a complete example root under `examples/complete/` that also consumes the
  same shared module.

## Providerless resource model

- Model the network with `terraform_data` resources inside the module rather than
  real cloud providers.
- Put the network classification directly in each resource `input` payload so JSON
  plan inspection can recover the topology. Use:
  - `input.kind = "vpc"` for the VPC
  - `input.kind = "internet_gateway"` for the IGW
  - `input.kind = "nat_gateway"` for NAT gateways
  - `input.kind = "subnet"` plus `input.tier = "public"` or `"private"` for subnets
  - `input.kind = "route_table"` plus `input.tier = "public"` or `"private"` for route tables
- For subnet resources, include at least AZ, CIDR block, tier, and merged tags in
  the `input` payload.
- Mirror the subnet tier into the subnet tag set as well:
  - public subnet tags must include `Tier = "public"`
  - private subnet tags must include `Tier = "private"`
- For route tables, include enough information to tell whether default egress goes
  to the IGW or a NAT gateway.

## Topology contract

- Build one public subnet and one private subnet per availability zone.
- Build exactly one internet gateway.
- Build exactly one shared public route table total, with all public subnets using it.
- Build one private route table per private subnet.
- When `single_nat_gateway = true`, build exactly one NAT gateway and have all
  private route tables point to it.
- When `single_nat_gateway = false`, build one NAT gateway per AZ and keep private
  route tables aligned to their AZ-local NAT gateway.

## Tagging contract

- Merge the platform tags from `platform_tags.json` into the VPC and subnet tags.
- Add the EKS cluster discovery tag `kubernetes.io/cluster/<cluster_name> = shared`
  to all subnets.
- Add `kubernetes.io/role/elb = 1` to public subnets.
- Add `kubernetes.io/role/internal-elb = 1` to private subnets.

## Outputs and verification

- Provide the documented required outputs at minimum:
  `vpc_id`, `vpc_cidr_block`, `public_subnet_ids`, `private_subnet_ids`,
  `public_route_table_ids`, and `private_route_table_ids`.
- Keep the shared module self-contained at plan time. Do not make the module read
  sibling or parent task files such as `../../data/*.json` via `file()` or similar
  path lookups. A scratch root that points directly at the module source should be
  able to plan using only the documented module inputs.
- Also make sure a fresh scratch root using only the documented module inputs can
  still `plan` successfully.
- Before finishing, run:
  - `workspace/scripts/check_all.sh`
  - `workspace/scripts/plan_root.sh /root/environment/workspace/live/staging`
  - `workspace/scripts/plan_root.sh /root/environment/workspace/live/prod`
  - `terraform -chdir=/root/environment/workspace/terraform-modules/aws/vpc test`
