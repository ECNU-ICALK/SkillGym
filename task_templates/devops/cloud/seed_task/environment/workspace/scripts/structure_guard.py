from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "terraform-modules" / "aws" / "vpc"
LIVE_DIRS = [
    ROOT / "live" / "staging",
    ROOT / "live" / "prod",
]
MODULE_TESTS_DIR = MODULE_DIR / "tests"
NETWORK_RESOURCE_MARKERS = (
    'resource "terraform_data"',
)


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def read_tf_text(directory: Path) -> str:
    parts = []
    for path in sorted(directory.glob("*.tf")):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def main() -> None:
    required_files = [
        MODULE_DIR / "main.tf",
        MODULE_DIR / "variables.tf",
        MODULE_DIR / "outputs.tf",
        MODULE_DIR / "versions.tf",
        MODULE_DIR / "README.md",
    ]
    for path in required_files:
        if not path.exists():
            fail(f"Missing required module artifact: {path}")

    for live_dir in LIVE_DIRS:
        text = read_tf_text(live_dir)
        if 'module "vpc"' not in text:
            fail(f"{live_dir} must consume the shared module via module \\\"vpc\\\".")
        for marker in NETWORK_RESOURCE_MARKERS:
            if marker in text:
                fail(f"{live_dir} still defines direct network resources instead of consuming the shared module.")

    example_tf_files = list((ROOT / "examples" / "complete").glob("*.tf"))
    if not example_tf_files:
        fail("examples/complete must contain at least one Terraform file.")
    example_text = read_tf_text(ROOT / "examples" / "complete")
    if 'module "vpc"' not in example_text:
        fail("examples/complete must include a shared module usage example.")

    if not MODULE_TESTS_DIR.exists():
        fail("terraform-modules/aws/vpc/tests must exist.")
    if not list(MODULE_TESTS_DIR.glob("*.tftest.hcl")):
        fail("terraform-modules/aws/vpc/tests must include at least one Terraform test file.")


if __name__ == "__main__":
    main()
