from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/root/environment"))
DATA_ROOT = TASK_ROOT / "data"
CONTRACTS_ROOT = TASK_ROOT / "protocol" / "contracts"
PIPELINE_ROOT = TASK_ROOT / "pipeline"
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_DIR", "/root/answer"))

DATA_HASH_PATH = Path(os.environ.get("TASK_DATA_HASH_PATH", "/opt/token-review-data.sha256"))
SKILL_ROOT = Path(
    os.environ.get(
        "TASK_SKILL_ROOT",
        str(TASK_ROOT / "skills" / "token-integration-analyzer"),
    )
)


def sha256sum_style_listing(path: Path) -> str:
    return subprocess.check_output(
        f"find {path} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )


def run_review(task_root: Path = TASK_ROOT, output_root: Path = OUTPUT_ROOT, timeout_sec: int = 300) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(task_root / "pipeline")
    return subprocess.run(
        [
            sys.executable,
            str(task_root / "pipeline" / "run_token_onboarding_review.py"),
            "--root",
            str(task_root),
            "--output",
            str(output_root),
        ],
        text=True,
        capture_output=True,
        timeout=timeout_sec,
        env=env,
    )


def clone_task_root() -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="token-review-"))
    task_copy = temp_root / "environment"
    shutil.copytree(TASK_ROOT, task_copy)
    return task_copy


def run_review_in_temp(
    *,
    policy_override: dict | None = None,
    timeout_sec: int = 300,
) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    task_copy = clone_task_root()
    if policy_override is not None:
        (task_copy / "data" / "listing_policy.json").write_text(
            json.dumps(policy_override, indent=2) + "\n",
            encoding="utf-8",
        )
    output_root = task_copy.parent / "answer"
    output_root.mkdir(parents=True, exist_ok=True)
    result = run_review(task_root=task_copy, output_root=output_root, timeout_sec=timeout_sec)
    return result, task_copy, output_root


def output_bytes_map(output_root: Path) -> dict[str, bytes]:
    required = [
        "token_onboarding_review.md",
        "token_decisions.tsv",
        "token_behavior_findings.tsv",
        "guardrail_coverage.tsv",
        "evidence_index.json",
    ]
    return {name: (output_root / name).read_bytes() for name in required}
