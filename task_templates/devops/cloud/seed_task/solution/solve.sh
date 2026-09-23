#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/root/environment}"
ROOT="$APP_ROOT/workspace"
MODULE_DIR="$ROOT/terraform-modules/aws/vpc"

mkdir -p "$MODULE_DIR/tests" "$ROOT/examples/complete"

cat > "$MODULE_DIR/main.tf" <<'EOF'
locals {
  platform_tags = {
    ManagedBy = "terraform"
    Platform  = "harbor"
    Owner     = "platform-team"
  }

  common_tags = merge(
    local.platform_tags,
    var.tags,
    {
      Name = var.name
    }
  )

  cluster_tag = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }

  public_subnet_tags = merge(
    local.common_tags,
    local.cluster_tag,
    {
      "kubernetes.io/role/elb" = "1"
    }
  )

  private_subnet_tags = merge(
    local.common_tags,
    local.cluster_tag,
    {
      "kubernetes.io/role/internal-elb" = "1"
    }
  )
}

resource "terraform_data" "vpc" {
  input = {
    kind                 = "vpc"
    name                 = var.name
    cidr_block           = var.cidr_block
    enable_dns_support   = var.enable_dns_support
    enable_dns_hostnames = var.enable_dns_hostnames
    tags                 = local.common_tags
  }
}

resource "terraform_data" "internet_gateway" {
  input = {
    kind = "internet_gateway"
    name = "${var.name}-igw"
    vpc  = terraform_data.vpc.id
    tags = merge(local.common_tags, {
      Name = "${var.name}-igw"
    })
  }
}

resource "terraform_data" "public_subnets" {
  count = length(var.public_subnet_cidrs)

  input = {
    kind                 = "subnet"
    tier                 = "public"
    name                 = "${var.name}-public-${count.index + 1}"
    cidr_block           = var.public_subnet_cidrs[count.index]
    availability_zone    = var.availability_zones[count.index]
    map_public_ip_launch = true
    tags = merge(local.public_subnet_tags, {
      Name = "${var.name}-public-${count.index + 1}"
      Tier = "public"
    })
  }
}

resource "terraform_data" "private_subnets" {
  count = length(var.private_subnet_cidrs)

  input = {
    kind              = "subnet"
    tier              = "private"
    name              = "${var.name}-private-${count.index + 1}"
    cidr_block        = var.private_subnet_cidrs[count.index]
    availability_zone = var.availability_zones[count.index]
    tags = merge(local.private_subnet_tags, {
      Name = "${var.name}-private-${count.index + 1}"
      Tier = "private"
    })
  }
}

resource "terraform_data" "nat_gateways" {
  count = var.single_nat_gateway ? 1 : length(var.public_subnet_cidrs)

  input = {
    kind         = "nat_gateway"
    name         = "${var.name}-nat-${count.index + 1}"
    single_nat   = var.single_nat_gateway
    subnet_index = var.single_nat_gateway ? 0 : count.index
    tags = merge(local.common_tags, {
      Name = "${var.name}-nat-${count.index + 1}"
    })
  }
}

resource "terraform_data" "public_route_table" {
  input = {
    kind         = "route_table"
    tier         = "public"
    name         = "${var.name}-public-rt"
    default_hop  = "internet_gateway"
    associations = length(var.public_subnet_cidrs)
    tags = merge(local.common_tags, {
      Name = "${var.name}-public-rt"
    })
  }
}

resource "terraform_data" "private_route_tables" {
  count = length(var.private_subnet_cidrs)

  input = {
    kind               = "route_table"
    tier               = "private"
    name               = "${var.name}-private-rt-${count.index + 1}"
    nat_gateway_index  = var.single_nat_gateway ? 0 : count.index
    association_subnet = count.index
    default_hop        = "nat_gateway"
    tags = merge(local.common_tags, {
      Name = "${var.name}-private-rt-${count.index + 1}"
    })
  }
}
EOF

cat > "$MODULE_DIR/variables.tf" <<'EOF'
variable "name" {
  description = "Name prefix for the VPC resources."
  type        = string
}

variable "cidr_block" {
  description = "IPv4 CIDR block for the VPC."
  type        = string

  validation {
    condition     = can(cidrhost(var.cidr_block, 0))
    error_message = "cidr_block must be valid IPv4 CIDR notation."
  }
}

variable "availability_zones" {
  description = "Availability zones used by the module."
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) > 0
    error_message = "availability_zones must not be empty."
  }
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets."
  type        = list(string)

  validation {
    condition = (
      length(var.public_subnet_cidrs) == length(var.availability_zones) &&
      alltrue([for cidr in var.public_subnet_cidrs : can(cidrhost(cidr, 0))])
    )
    error_message = "public_subnet_cidrs must contain one valid CIDR per availability zone."
  }
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets."
  type        = list(string)

  validation {
    condition = (
      length(var.private_subnet_cidrs) == length(var.availability_zones) &&
      alltrue([for cidr in var.private_subnet_cidrs : can(cidrhost(cidr, 0))])
    )
    error_message = "private_subnet_cidrs must contain one valid CIDR per availability zone."
  }
}

variable "single_nat_gateway" {
  description = "Whether to use a single NAT gateway for all private subnets."
  type        = bool
}

variable "enable_dns_support" {
  description = "Enable DNS support for the VPC."
  type        = bool
  default     = true
}

variable "enable_dns_hostnames" {
  description = "Enable DNS hostnames for the VPC."
  type        = bool
  default     = true
}

variable "cluster_name" {
  description = "Cluster name used to stamp EKS-compatible subnet tags."
  type        = string
}

variable "tags" {
  description = "Environment-specific tags merged with platform defaults."
  type        = map(string)
  default     = {}
}
EOF

cat > "$MODULE_DIR/outputs.tf" <<'EOF'
output "vpc_id" {
  description = "ID of the VPC."
  value       = terraform_data.vpc.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC."
  value       = terraform_data.vpc.output.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of public subnets."
  value       = terraform_data.public_subnets[*].id
}

output "private_subnet_ids" {
  description = "IDs of private subnets."
  value       = terraform_data.private_subnets[*].id
}

output "public_route_table_ids" {
  description = "IDs of public route tables."
  value       = [terraform_data.public_route_table.id]
}

output "private_route_table_ids" {
  description = "IDs of private route tables."
  value       = terraform_data.private_route_tables[*].id
}
EOF

cat > "$MODULE_DIR/versions.tf" <<'EOF'
terraform {
  required_version = ">= 1.6.0"
}
EOF

cat > "$MODULE_DIR/README.md" <<'EOF'
# AWS VPC Module

This module builds a reusable Terraform representation of the Harbor platform VPC baseline.
It standardizes public and private subnet fan-out, NAT strategy selection, EKS-compatible subnet tagging, and platform tag propagation across environments.
The same interface is shared by staging, production, examples, and future environments so consumers vary blueprint values instead of copying resource graphs.

## Inputs

- `name`: resource name prefix for the environment.
- `cidr_block`: VPC CIDR block.
- `availability_zones`: AZ list that drives subnet fan-out.
- `public_subnet_cidrs`: one public subnet CIDR per AZ.
- `private_subnet_cidrs`: one private subnet CIDR per AZ.
- `single_nat_gateway`: use one NAT for all private subnets when `true`, or one NAT per AZ when `false`.
- `cluster_name`: used to stamp EKS subnet discovery tags.
- `tags`: environment-specific tags merged with platform defaults.

## Outputs

- `vpc_id`
- `vpc_cidr_block`
- `public_subnet_ids`
- `private_subnet_ids`
- `public_route_table_ids`
- `private_route_table_ids`

## Example

See `examples/complete/` for a full root module that consumes this shared module.
EOF

cat > "$MODULE_DIR/tests/module.tftest.hcl" <<'EOF'
run "plan_complete_example" {
  command = plan

  variables {
    name                 = "test-vpc"
    cidr_block           = "10.10.0.0/16"
    availability_zones   = ["us-west-2a", "us-west-2b"]
    public_subnet_cidrs  = ["10.10.0.0/24", "10.10.1.0/24"]
    private_subnet_cidrs = ["10.10.10.0/24", "10.10.11.0/24"]
    single_nat_gateway   = true
    enable_dns_support   = true
    enable_dns_hostnames = true
    cluster_name         = "test-cluster"
    tags = {
      Environment = "test"
      Application = "platform"
      CostCenter  = "eng-platform"
    }
  }

  assert {
    condition     = length(terraform_data.public_subnets) == 2
    error_message = "Expected two public subnets."
  }

  assert {
    condition     = length(terraform_data.private_subnets) == 2
    error_message = "Expected two private subnets."
  }

  assert {
    condition     = length(terraform_data.nat_gateways) == 1
    error_message = "Expected a single NAT gateway."
  }
}
EOF

cat > "$ROOT/live/staging/main.tf" <<'EOF'
terraform {
  required_version = ">= 1.6.0"
}

module "vpc" {
  source = "../../terraform-modules/aws/vpc"

  name                 = var.name
  cidr_block           = var.cidr_block
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  single_nat_gateway   = var.single_nat_gateway
  enable_dns_support   = var.enable_dns_support
  enable_dns_hostnames = var.enable_dns_hostnames
  cluster_name         = var.cluster_name
  tags                 = var.tags
}
EOF

cat > "$ROOT/live/prod/main.tf" <<'EOF'
terraform {
  required_version = ">= 1.6.0"
}

module "vpc" {
  source = "../../terraform-modules/aws/vpc"

  name                 = var.name
  cidr_block           = var.cidr_block
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  single_nat_gateway   = var.single_nat_gateway
  enable_dns_support   = var.enable_dns_support
  enable_dns_hostnames = var.enable_dns_hostnames
  cluster_name         = var.cluster_name
  tags                 = var.tags
}
EOF

cat > "$ROOT/examples/complete/main.tf" <<'EOF'
terraform {
  required_version = ">= 1.6.0"
}

module "vpc" {
  source = "../../terraform-modules/aws/vpc"

  name                 = var.name
  cidr_block           = var.cidr_block
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  single_nat_gateway   = var.single_nat_gateway
  enable_dns_support   = var.enable_dns_support
  enable_dns_hostnames = var.enable_dns_hostnames
  cluster_name         = var.cluster_name
  tags                 = var.tags
}
EOF

cat > "$ROOT/examples/complete/variables.tf" <<'EOF'
variable "region" {
  type = string
}

variable "name" {
  type = string
}

variable "cidr_block" {
  type = string
}

variable "availability_zones" {
  type = list(string)
}

variable "public_subnet_cidrs" {
  type = list(string)
}

variable "private_subnet_cidrs" {
  type = list(string)
}

variable "single_nat_gateway" {
  type = bool
}

variable "enable_dns_support" {
  type = bool
}

variable "enable_dns_hostnames" {
  type = bool
}

variable "cluster_name" {
  type = string
}

variable "tags" {
  type = map(string)
}
EOF

cat > "$ROOT/examples/complete/terraform.tfvars.json" <<'EOF'
{
  "region": "us-west-2",
  "name": "platform-example",
  "cidr_block": "10.200.0.0/16",
  "availability_zones": [
    "us-west-2a",
    "us-west-2b"
  ],
  "public_subnet_cidrs": [
    "10.200.0.0/24",
    "10.200.1.0/24"
  ],
  "private_subnet_cidrs": [
    "10.200.10.0/24",
    "10.200.11.0/24"
  ],
  "single_nat_gateway": true,
  "enable_dns_support": true,
  "enable_dns_hostnames": true,
  "cluster_name": "platform-example-eks",
  "tags": {
    "Environment": "example",
    "Application": "platform",
    "CostCenter": "eng-platform"
  }
}
EOF

terraform fmt -recursive "$ROOT" >/dev/null
