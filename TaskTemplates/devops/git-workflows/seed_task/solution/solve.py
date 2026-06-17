from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(os.environ.get("TASK_REPO_ROOT", "/app/repo"))
DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
REQUEST = json.loads((DATA_ROOT / "hotfix_request.json").read_text(encoding="utf-8"))


def run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def main() -> None:
    worktree_root = REPO_ROOT / ".worktrees" / REQUEST["hotfix_branch"]
    if worktree_root.exists():
        shutil.rmtree(worktree_root)

    worktree_root.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "git",
            "worktree",
            "add",
            "-b",
            REQUEST["hotfix_branch"],
            str(worktree_root),
            REQUEST["release_branch"],
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
    )

    pricing_path = worktree_root / "src/meridian_checkout/pricing.py"
    text = pricing_path.read_text(encoding="utf-8")
    updated = text.replace("taxable_cents = subtotal_cents", "taxable_cents = discounted_subtotal_cents")
    if updated == text:
        raise RuntimeError("expected release-branch pricing regression was not found")
    pricing_path.write_text(updated, encoding="utf-8")

    subprocess.run(["git", "add", "src/meridian_checkout/pricing.py"], cwd=worktree_root, check=True, text=True)
    subprocess.run(["git", "commit", "-m", "fix(checkout): restore hotfix pricing calculation"], cwd=worktree_root, check=True, text=True)
    subprocess.run(["bash", "ops/hotfix/run_hotfix.sh"], cwd=worktree_root, check=True, text=True)


if __name__ == "__main__":
    main()
