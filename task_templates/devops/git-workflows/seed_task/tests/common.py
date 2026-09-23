from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(os.environ.get("TASK_REPO_ROOT", "/app/repo"))
DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
BASELINE_ROOT = Path(os.environ.get("TASK_BASELINE_ROOT", "/opt/task-baselines"))
REQUEST = json.loads((DATA_ROOT / "hotfix_request.json").read_text(encoding="utf-8"))
METADATA = json.loads((BASELINE_ROOT / "repo_metadata.json").read_text(encoding="utf-8"))


def run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def git(*args: str, cwd: Path | None = None) -> str:
    return run(["git", *args], cwd=cwd or REPO_ROOT)


def parse_worktrees() -> list[dict[str, str]]:
    output = git("worktree", "list", "--porcelain")
    blocks = [block.strip().splitlines() for block in output.split("\n\n") if block.strip()]
    parsed = []
    for block in blocks:
        item: dict[str, str] = {}
        for line in block:
            if " " not in line:
                item[line] = "true"
                continue
            key, value = line.split(" ", 1)
            item[key] = value
        parsed.append(item)
    return parsed


def find_hotfix_worktree() -> Path:
    target_branch = REQUEST["hotfix_branch"]
    for worktree in parse_worktrees():
        branch = worktree.get("branch", "")
        if branch.endswith("/" + target_branch) or branch == f"refs/heads/{target_branch}":
            return Path(worktree["worktree"])
    raise AssertionError(f"No linked worktree found for branch {target_branch}")


def expected_worktree_root() -> Path:
    return Path(METADATA["preferred_worktree_root"]) / REQUEST["hotfix_branch"]


def release_notes_path() -> Path:
    return find_hotfix_worktree() / "artifacts" / "release_notes.md"


def report_path() -> Path:
    return find_hotfix_worktree() / "artifacts" / "hotfix_report.json"


def expected_release_notes() -> str:
    grouped: dict[str, list[str]] = {"Fixes": [], "Risks": [], "Validation": []}
    for line in (DATA_ROOT / "changelog_fragments.ndjson").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["release_version"] != REQUEST["release_version"]:
            continue
        if not row.get("include", True):
            continue
        grouped.setdefault(row["section"], []).append(row["text"])

    lines = [
        f"# {REQUEST['notes_title']}",
        "",
        f"Base branch: `{REQUEST['release_branch']}`",
        f"Target branch: `{REQUEST['hotfix_branch']}`",
        "",
    ]
    for section in ["Fixes", "Risks", "Validation"]:
        entries = grouped.get(section, [])
        if not entries:
            continue
        lines.append(f"## {section}")
        for entry in entries:
            lines.append(f"- {entry}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def load_report() -> dict:
    return json.loads(report_path().read_text(encoding="utf-8"))


def assert_primary_checkout_unchanged() -> None:
    expected_branch = (BASELINE_ROOT / "root_branch.txt").read_text(encoding="utf-8").strip()
    expected_status = (BASELINE_ROOT / "root_status.txt").read_text(encoding="utf-8").strip()
    expected_diff = (BASELINE_ROOT / "root_diff.patch").read_text(encoding="utf-8").strip()

    current_branch = git("branch", "--show-current", cwd=REPO_ROOT).strip()
    current_status = git("status", "--short", cwd=REPO_ROOT).strip()
    current_diff = git(
        "diff",
        "--",
        "src/meridian_checkout/pricing.py",
        "audit/investigation.md",
        cwd=REPO_ROOT,
    ).strip()

    assert current_branch == expected_branch, "Primary checkout branch changed"
    assert current_status == expected_status, "Primary checkout status changed"
    assert current_diff == expected_diff, "Primary checkout dirty diff changed"


def import_pricing_module(worktree: Path):
    sys.path.insert(0, str(worktree / "src"))
    from meridian_checkout.pricing import calculate_checkout_total

    return calculate_checkout_total
