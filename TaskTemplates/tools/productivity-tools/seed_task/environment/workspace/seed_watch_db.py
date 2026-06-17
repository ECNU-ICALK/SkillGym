#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore the local blogwatcher database from the bundled seed snapshot.")
    parser.add_argument("--bundle-root", default="/app/release-watch")
    parser.add_argument("--workspace-root", default="/app/workspace")
    parser.add_argument("--db-path", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_root = Path(args.bundle_root)
    workspace_root = Path(args.workspace_root)
    db_path = Path(args.db_path) if args.db_path else workspace_root / "blogwatcher.db"
    seed_snapshot = bundle_root / "seed" / "blogwatcher_seed.sqlite"

    if not seed_snapshot.exists():
        raise FileNotFoundError(f"Missing bundled seed snapshot: {seed_snapshot}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(seed_snapshot, db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
