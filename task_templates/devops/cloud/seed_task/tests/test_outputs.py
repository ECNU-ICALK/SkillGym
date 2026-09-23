import json
import os
import subprocess
import tempfile
from pathlib import Path

import hcl2
import pytest


APP_ROOT = Path(os.environ.get("APP_ROOT", "/root/environment"))
WORKSPACE = APP_ROOT / "workspace"
MODULE_DIR = WORKSPACE / "terraform-modules" / "aws" / "vpc"
SCRIPTS_DIR = WORKSPACE / "scripts"
DATA_DIR = APP_ROOT / "data"
PLATFORM_TAGS = json.loads((DATA_DIR / "platform_tags.json").read_text(encoding="utf-8"))
EKS_TAG_CONTRACT = json.loads((DATA_DIR / "eks_subnet_tag_contract.json").read_text(encoding="utf-8"))
MODULE_CONTRACT = json.loads((DATA_DIR / "module_contract.json").read_text(encoding="utf-8"))


def run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def load_hcl(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return hcl2.load(f)


def all_tf_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.tf"))


def module_block_from_directory(directory: Path) -> dict:
    for path in all_tf_files(directory):
        data = load_hcl(path)
        for block in data.get("module", []):
            for key, value in block.items():
                if key.strip('"') == "vpc":
                    return value
    raise AssertionError(f"No module \"vpc\" block found in {directory}")


def read_tf_text(directory: Path) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in all_tf_files(directory))


def collect_resources(module: dict) -> list[dict]:
    resources = list(module.get("resources", []))
    for child in module.get("child_modules", []):
        resources.extend(collect_resources(child))
    return resources


def plan_root(root_dir: Path) -> dict:
    plan_json = run(["bash", str(SCRIPTS_DIR / "plan_root.sh"), str(root_dir)])
    return json.loads(plan_json)


def build_hidden_root(tmpdir: Path, blueprint: dict) -> Path:
    main_tf = f"""
terraform {{
  required_version = ">= 1.6.0"
}}

module "vpc" {{
  source = "{MODULE_DIR}"

  name                  = "{blueprint["name"]}"
  cidr_block            = "{blueprint["cidr_block"]}"
  availability_zones    = {json.dumps(blueprint["availability_zones"])}
  public_subnet_cidrs   = {json.dumps(blueprint["public_subnet_cidrs"])}
  private_subnet_cidrs  = {json.dumps(blueprint["private_subnet_cidrs"])}
  single_nat_gateway    = {str(blueprint["single_nat_gateway"]).lower()}
  enable_dns_support    = {str(blueprint["enable_dns_support"]).lower()}
  enable_dns_hostnames  = {str(blueprint["enable_dns_hostnames"]).lower()}
  cluster_name          = "{blueprint["cluster_name"]}"
  tags                  = {json.dumps(blueprint["tags"])}
}}
"""
    (tmpdir / "main.tf").write_text(main_tf.strip() + "\n", encoding="utf-8")
    return tmpdir


def assert_subnet_tags(resources: list[dict], cluster_name: str) -> None:
    required_platform_tags = PLATFORM_TAGS["required_tags"]
    cluster_tag_key = EKS_TAG_CONTRACT["cluster_tag_template"].replace("<cluster_name>", cluster_name)

    for resource in resources:
        if resource["type"] != "terraform_data":
            continue
        values = resource["values"]
        payload = values.get("input", {})
        if payload.get("kind") != "subnet":
            continue
        tags = payload.get("tags", {})
        for key, value in required_platform_tags.items():
            assert tags.get(key) == value, f"Missing required platform tag {key}={value}"
        assert tags.get(cluster_tag_key) == EKS_TAG_CONTRACT["cluster_tag_value"]
        tier = tags.get("Tier")
        if tier == "public":
            for key, value in EKS_TAG_CONTRACT["public_subnet_tags"].items():
                assert tags.get(key) == value
        elif tier == "private":
            for key, value in EKS_TAG_CONTRACT["private_subnet_tags"].items():
                assert tags.get(key) == value
        else:
            raise AssertionError(f"Unexpected subnet tier tag: {tier}")


@pytest.fixture(scope="module")
def check_all() -> None:
    env = os.environ.copy()
    env["PATH"] = env["PATH"]
    subprocess.run(
        ["bash", str(SCRIPTS_DIR / "check_all.sh")],
        cwd=WORKSPACE,
        text=True,
        check=True,
        env=env,
    )


class TestModuleContract:
    def test_live_roots_consume_shared_module(self, check_all):
        expected_module_dir = MODULE_DIR.resolve()
        for env_name in ("staging", "prod"):
            root_dir = WORKSPACE / "live" / env_name
            block = module_block_from_directory(root_dir)
            source = block["source"].strip('"')
            resolved = (root_dir / source).resolve()
            assert resolved == expected_module_dir
            text = read_tf_text(root_dir)
            for marker in (
                'resource "terraform_data"',
            ):
                assert marker not in text

    def test_module_required_files_and_contract(self, check_all):
        for required_file in MODULE_CONTRACT["required_files"]:
            assert (MODULE_DIR / required_file).exists()

        variables_text = (MODULE_DIR / "variables.tf").read_text(encoding="utf-8")
        outputs_text = (MODULE_DIR / "outputs.tf").read_text(encoding="utf-8")
        versions_text = (MODULE_DIR / "versions.tf").read_text(encoding="utf-8")
        readme_text = (MODULE_DIR / "README.md").read_text(encoding="utf-8")
        module_test_files = sorted((MODULE_DIR / "tests").glob("*.tftest.hcl"))

        for var in MODULE_CONTRACT["required_variables"]:
            assert f'variable "{var["name"]}"' in variables_text
        for output_name in MODULE_CONTRACT["required_outputs"]:
            assert f'output "{output_name}"' in outputs_text
        assert "required_version" in versions_text
        assert "TODO" not in readme_text
        assert len(readme_text.strip().splitlines()) >= 5
        assert module_test_files, "terraform-modules/aws/vpc/tests must include at least one Terraform test file"

    def test_example_consumes_shared_module(self, check_all):
        example_dir = WORKSPACE / "examples" / "complete"
        assert all_tf_files(example_dir), "examples/complete must contain at least one Terraform file"
        example_text = read_tf_text(example_dir)
        assert 'module "vpc"' in example_text


class TestVisibleBlueprintPlans:
    @pytest.mark.parametrize(
        "env_name,expected_public,expected_private,expected_nat",
        [
            ("staging", 2, 2, 1),
            ("prod", 3, 3, 3),
        ],
    )
    def test_environment_plans_match_blueprints(self, check_all, env_name, expected_public, expected_private, expected_nat):
        root_dir = WORKSPACE / "live" / env_name
        plan = plan_root(root_dir)
        resources = collect_resources(plan["planned_values"]["root_module"])

        public_subnets = [r for r in resources if r["type"] == "terraform_data" and r["values"].get("input", {}).get("kind") == "subnet" and r["values"].get("input", {}).get("tier") == "public"]
        private_subnets = [r for r in resources if r["type"] == "terraform_data" and r["values"].get("input", {}).get("kind") == "subnet" and r["values"].get("input", {}).get("tier") == "private"]
        nat_gateways = [r for r in resources if r["type"] == "terraform_data" and r["values"].get("input", {}).get("kind") == "nat_gateway"]
        internet_gateways = [r for r in resources if r["type"] == "terraform_data" and r["values"].get("input", {}).get("kind") == "internet_gateway"]
        public_route_tables = [r for r in resources if r["type"] == "terraform_data" and r["values"].get("input", {}).get("kind") == "route_table" and r["values"].get("input", {}).get("tier") == "public"]
        private_route_tables = [r for r in resources if r["type"] == "terraform_data" and r["values"].get("input", {}).get("kind") == "route_table" and r["values"].get("input", {}).get("tier") == "private"]

        assert len(public_subnets) == expected_public
        assert len(private_subnets) == expected_private
        assert len(nat_gateways) == expected_nat
        assert len(internet_gateways) == 1
        assert len(public_route_tables) == 1
        assert len(private_route_tables) == expected_private

        blueprint = json.loads((DATA_DIR / "environment_blueprints" / f"{env_name}.json").read_text(encoding="utf-8"))
        assert_subnet_tags(resources, blueprint["cluster_name"])


class TestHiddenQABlueprint:
    def test_hidden_qa_blueprint_works(self, check_all):
        qa_blueprint = {
            "region": "us-west-2",
            "name": "platform-qa",
            "cidr_block": "10.126.0.0/16",
            "availability_zones": ["us-west-2a", "us-west-2b"],
            "public_subnet_cidrs": ["10.126.0.0/24", "10.126.1.0/24"],
            "private_subnet_cidrs": ["10.126.10.0/24", "10.126.11.0/24"],
            "single_nat_gateway": False,
            "enable_dns_support": True,
            "enable_dns_hostnames": True,
            "cluster_name": "platform-qa-eks",
            "tags": {
                "Environment": "qa",
                "Application": "platform",
                "CostCenter": "eng-platform"
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            root_dir = build_hidden_root(Path(tmp), qa_blueprint)
            plan = plan_root(root_dir)
        resources = collect_resources(plan["planned_values"]["root_module"])
        public_subnets = [r for r in resources if r["type"] == "terraform_data" and r["values"].get("input", {}).get("kind") == "subnet" and r["values"].get("input", {}).get("tier") == "public"]
        private_subnets = [r for r in resources if r["type"] == "terraform_data" and r["values"].get("input", {}).get("kind") == "subnet" and r["values"].get("input", {}).get("tier") == "private"]
        nat_gateways = [r for r in resources if r["type"] == "terraform_data" and r["values"].get("input", {}).get("kind") == "nat_gateway"]

        assert len(public_subnets) == 2
        assert len(private_subnets) == 2
        assert len(nat_gateways) == 2
        assert_subnet_tags(resources, qa_blueprint["cluster_name"])
