from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


WORKSPACE = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
PACKAGE = WORKSPACE / "package"
OUTPUT = Path(os.environ.get("TASK_OUTPUT_FILE", "/app/output/release_readiness_report.json"))
CONTRACT = WORKSPACE / "contracts" / "release_contract.json"
OUTPUT_CONTRACT = WORKSPACE / "contracts" / "output_contract.json"
SKILLS_ROOT = Path(os.environ.get("SKILLS_ROOT", "/root/.codex/skills"))
DATA_BASELINE_FILE = Path(os.environ.get("DATA_BASELINE_FILE", "/opt/toolchain-data.sha256"))
PACKAGE_DIFF_BASELINE_FILE = Path(os.environ.get("PACKAGE_DIFF_BASELINE_FILE", "/opt/toolchain-package.diff.sha256"))


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


def run_shell(command: str) -> CommandResult:
    completed = subprocess.run(
        ["/bin/bash", "-lc", command],
        text=True,
        capture_output=True,
        cwd=str(PACKAGE),
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def read_report() -> dict:
    return json.loads(OUTPUT.read_text(encoding="utf-8"))


def read_release_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def read_output_contract() -> dict:
    return json.loads(OUTPUT_CONTRACT.read_text(encoding="utf-8"))


def gate_map(report: dict) -> dict[str, dict]:
    return {gate["name"]: gate for gate in report["gates"]}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def current_data_manifest() -> dict[str, str]:
    root = WORKSPACE / "data"
    return {
        str(path.relative_to(root)): file_sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def baseline_data_manifest() -> dict[str, str]:
    manifest: dict[str, str] = {}
    for line in DATA_BASELINE_FILE.read_text(encoding="utf-8").splitlines():
        digest, path = line.split(maxsplit=1)
        manifest[str(Path(path).relative_to(WORKSPACE / "data"))] = digest
    return manifest


def current_package_diff_hash() -> str:
    current = subprocess.run(
        ["/bin/bash", "-lc", "git diff --binary"],
        cwd=str(PACKAGE),
        text=True,
        capture_output=True,
        check=True,
    ).stdout.encode("utf-8")
    return hashlib.sha256(current).hexdigest()


def baseline_package_diff_hash() -> str:
    return PACKAGE_DIFF_BASELINE_FILE.read_text(encoding="utf-8").strip()
