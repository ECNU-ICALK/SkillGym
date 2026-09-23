#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


def resolve_src_root() -> Path:
    candidates = [
        Path("/opt/productivity-tools-task-env"),
        Path("/opt/productivity-tools-task-env/environment"),
    ]
    for candidate in candidates:
        if (candidate / "release_watch").exists() and (candidate / "workspace").exists():
            return candidate
    raise FileNotFoundError("Unable to locate bundled environment sources")


def ensure_dirs(paths: list[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, dirs_exist_ok=True)


def write_release_watch_baseline() -> None:
    baseline = Path("/opt/task-baselines/release-watch.sha256")
    release_root = Path("/app/release-watch")
    lines: list[str] = []
    for file_path in sorted(path for path in release_root.rglob("*") if path.is_file()):
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        relpath = file_path.relative_to(release_root).as_posix()
        lines.append(f"{digest}  {relpath}")
    baseline.write_text("\n".join(lines) + "\n", encoding="utf-8")
    baseline.chmod(0o644)


def main() -> int:
    src_root = resolve_src_root()

    ensure_dirs(
        [
            Path("/app/release-watch"),
            Path("/app/workspace"),
            Path("/app/output"),
            Path("/opt/task-baselines"),
        ]
    )

    copy_tree(src_root / "release_watch", Path("/app/release-watch"))
    copy_tree(src_root / "workspace", Path("/app/workspace"))

    for path in [
        Path("/app/workspace/build_digest.py"),
        Path("/app/workspace/seed_watch_db.py"),
    ]:
        path.chmod(0o755)

    write_release_watch_baseline()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
