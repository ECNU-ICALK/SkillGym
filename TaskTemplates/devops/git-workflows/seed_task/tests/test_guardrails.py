from __future__ import annotations

import os
import subprocess
from pathlib import Path

from common import (
    BASELINE_ROOT,
    REPO_ROOT,
    REQUEST,
    assert_primary_checkout_unchanged,
    expected_worktree_root,
    find_hotfix_worktree,
    git,
    parse_worktrees,
)


def test_primary_checkout_state_is_unchanged() -> None:
    assert_primary_checkout_unchanged()


def test_target_branch_runs_in_linked_worktree_not_primary_checkout() -> None:
    worktree = find_hotfix_worktree()
    assert worktree != REPO_ROOT, "Hotfix branch was completed in the primary checkout instead of a linked worktree"
    assert worktree == expected_worktree_root(), "Hotfix worktree does not use the expected hidden repo-local worktree directory"


def test_hidden_repo_local_worktree_directory_is_used() -> None:
    worktree = find_hotfix_worktree()
    assert worktree.parent == REPO_ROOT / ".worktrees", "Hotfix worktree should live under the hidden .worktrees directory"


def test_release_branch_ancestry_is_preserved() -> None:
    worktree = find_hotfix_worktree()
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", REQUEST["release_branch"], "HEAD"],
        cwd=worktree,
        text=True,
    )
    assert result.returncode == 0, "Hotfix branch is not based on the requested release branch"


def test_input_data_was_not_modified() -> None:
    data_root = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
    data_hash_path = Path(os.environ.get("TASK_DATA_HASH_PATH", str(BASELINE_ROOT / "data.sha256")))
    current_data = subprocess.check_output(
        f"find {data_root} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_data = data_hash_path.read_text(encoding="utf-8")
    assert current_data == expected_data, "Input data under /root/data was modified"


def test_linked_worktree_is_registered() -> None:
    worktrees = parse_worktrees()
    target = REQUEST["hotfix_branch"]
    matching = [item for item in worktrees if item.get("branch", "").endswith("/" + target) or item.get("branch") == f"refs/heads/{target}"]
    assert matching, f"No registered linked worktree found for {target}"


def test_hotfix_commit_scope_stays_on_checkout_logic_and_test_bootstrap() -> None:
    worktree = find_hotfix_worktree()
    changed = {
        line.strip()
        for line in git("diff", "--name-only", f"{REQUEST['release_branch']}...HEAD", cwd=worktree).splitlines()
        if line.strip()
    }
    allowed = {
        "src/meridian_checkout/pricing.py",
        "tests/test_pricing.py",
        "tests/conftest.py",
    }
    assert "src/meridian_checkout/pricing.py" in changed, "Hotfix branch did not change the checkout pricing implementation"
    unexpected = sorted(changed - allowed)
    assert not unexpected, f"Hotfix branch modified unrelated release-chain files: {unexpected}"
