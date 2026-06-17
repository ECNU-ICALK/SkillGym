# AWS Module Library Notes

Use this reference when a Terraform module task must stay locally plannable without
cloud credentials but still behave like a reusable AWS module library.

## Local planning pattern

- Prefer a providerless modeling approach such as `terraform_data` when the task
  explicitly requires `terraform init`, `validate`, `plan` and `test` to work in
  an isolated local container without AWS login.
- Keep environment roots thin. Shared topology logic, tag merging, derived names,
  and NAT / route-table behavior should live in the module rather than stay spread
  across multiple `live/*` roots.
- In Harbor-style local-module tasks, do not stop at passing `validate`. Inspect
  the JSON plan shape and make sure the module exposes the network topology via
  planned `terraform_data` resources rather than only via summarized outputs.

## Reusable VPC contract pattern

- Treat caller environment identity as metadata already available from `tags` and
  `name`. Do not make an extra `environment` string a mandatory module input unless
  every caller root truly needs and supplies it.
- For a reusable public/private subnet module contract, a common stable pattern is:
  one shared public route table for all public subnets, and one private route table
  per private subnet.
- `single_nat_gateway` should change NAT gateway count and private egress mapping,
  not the rest of the module interface.
- A stable providerless network model is to stamp `terraform_data` resources with
  `input.kind` values such as `vpc`, `subnet`, `internet_gateway`, `nat_gateway`,
  and `route_table`, with subnet resources also carrying `input.tier = "public"`
  or `"private"`.
- For the public/private subnet resources, include enough `input` metadata for
  downstream plan inspection: CIDR block, availability zone, tier, and merged tags.
- For route tables, make the public route table a single shared object and private
  route tables one-per-private-subnet. `single_nat_gateway = true` should point all
  private route tables to the same NAT gateway index; `false` should preserve a
  one-to-one NAT mapping by availability zone.

## Delivery pattern

- Ship `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf`, `README.md`,
  `examples/complete`, and at least one Terraform native test file.
- Add Terraform tests that exercise both `single_nat_gateway = true` and
  `single_nat_gateway = false`.
- Verify all of the following before finishing: root `plan` for each live
  environment, module-level `terraform test`, and at least one fresh scratch
  root that consumes the module using only the documented module contract.
