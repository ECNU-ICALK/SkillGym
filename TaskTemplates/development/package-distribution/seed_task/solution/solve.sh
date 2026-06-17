#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/workspace}"
REPO_ROOT="$WORKSPACE_ROOT/pkgmeta-kit"
OUT_DIR="$WORKSPACE_ROOT/out"
SOLUTION_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fixed"

rm -rf "$REPO_ROOT/src"
mkdir -p "$REPO_ROOT/src/pkgmeta_kit/data" "$OUT_DIR"

cp "$SOLUTION_ROOT/pyproject.toml" "$REPO_ROOT/pyproject.toml"
cp "$SOLUTION_ROOT/README.md" "$REPO_ROOT/README.md"
cp "$SOLUTION_ROOT/src/pkgmeta_kit/__init__.py" "$REPO_ROOT/src/pkgmeta_kit/__init__.py"
cp "$SOLUTION_ROOT/src/pkgmeta_kit/__main__.py" "$REPO_ROOT/src/pkgmeta_kit/__main__.py"
cp "$SOLUTION_ROOT/src/pkgmeta_kit/catalog.py" "$REPO_ROOT/src/pkgmeta_kit/catalog.py"
cp "$SOLUTION_ROOT/src/pkgmeta_kit/cli.py" "$REPO_ROOT/src/pkgmeta_kit/cli.py"
cp "$SOLUTION_ROOT/src/pkgmeta_kit/py.typed" "$REPO_ROOT/src/pkgmeta_kit/py.typed"
cp "$SOLUTION_ROOT/src/pkgmeta_kit/reporting.py" "$REPO_ROOT/src/pkgmeta_kit/reporting.py"
cp "$REPO_ROOT/data/licenses.json" "$REPO_ROOT/src/pkgmeta_kit/data/licenses.json"
cp "$REPO_ROOT/data/trove_classifiers.py" "$REPO_ROOT/src/pkgmeta_kit/data/trove_classifiers.py"

cd "$REPO_ROOT"
rm -rf dist build *.egg-info
python3 -m build

python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path

workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/workspace"))
repo = workspace_root / "pkgmeta-kit"
dist = repo / "dist"
out = workspace_root / "out"
artifacts = sorted(path.name for path in dist.iterdir() if path.suffix == ".whl" or path.name.endswith(".tar.gz"))
checksums = {}
for name in artifacts:
    digest = hashlib.sha256()
    with (dist / name).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    checksums[name] = digest.hexdigest()

manifest = {
    "package_name": "pkgmeta-kit",
    "version": "0.3.0",
    "build_backend": "setuptools.build_meta",
    "python_requires": ">=3.12",
    "console_entrypoint": "pkgmeta-kit",
    "produced_artifacts": artifacts,
    "artifact_sha256": checksums,
    "shipped_data_files": [
        "pkgmeta_kit/data/licenses.json",
        "pkgmeta_kit/data/trove_classifiers.py",
    ],
}
(out / "release_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
