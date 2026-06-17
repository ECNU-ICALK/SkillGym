#!/bin/bash
set -euo pipefail

TESTS_ROOT="${TESTS_ROOT:-/tests}"
VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-/app/workspace}"
EXTENSION_ROOT="${EXTENSION_ROOT:-/app/workspace/extension}"
DATA_ROOT="${DATA_ROOT:-/app/data}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$WORKSPACE_ROOT/output}"

mkdir -p "$VERIFIER_LOG_ROOT"
rm -f "$WORKSPACE_ROOT/output/"*.md "$WORKSPACE_ROOT/output/"*.vsix 2>/dev/null || true

cd "$EXTENSION_ROOT"
npm install --silent > "$VERIFIER_LOG_ROOT/npm-install.log" 2>&1
npm run build > "$VERIFIER_LOG_ROOT/build.log" 2>&1
RELEASE_BRIEFING_DATA_ROOT="$DATA_ROOT" RELEASE_BRIEFING_OUTPUT_ROOT="$OUTPUT_ROOT" npm run export > "$VERIFIER_LOG_ROOT/export.log" 2>&1
npm run package > "$VERIFIER_LOG_ROOT/package.log" 2>&1

set +e
python3 <<'PY' 2>&1 | tee "$VERIFIER_LOG_ROOT/test-output.txt"
from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback
from pathlib import Path

tests_root = Path(os.environ.get("TESTS_ROOT", "/tests"))
log_root = Path(os.environ.get("VERIFIER_LOG_ROOT", "/logs/verifier"))
sys.path.insert(0, str(tests_root))
results = []

for filename in ["test_outputs.py", "test_guardrails.py"]:
    path = tests_root / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    for name in sorted(dir(module)):
        if not name.startswith("test_"):
            continue
        fn = getattr(module, name)
        if not callable(fn):
            continue
        nodeid = f"{filename}::{name}"
        try:
            fn()
            results.append({"nodeid": nodeid, "outcome": "passed"})
            print(f"PASS {nodeid}")
        except Exception as exc:
            results.append(
                {
                    "nodeid": nodeid,
                    "outcome": "failed",
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
            print(f"FAIL {nodeid}: {exc}")
            traceback.print_exc()

report = {
    "tests": results,
    "summary": {
        "passed": sum(r["outcome"] == "passed" for r in results),
        "total": len(results),
    },
}
(log_root / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
(log_root / "ctrf.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
raise SystemExit(0 if all(r["outcome"] == "passed" for r in results) else 1)
PY
TEST_EXIT=${PIPESTATUS[0]}
set -e

if [ "$TEST_EXIT" -eq 0 ]; then
  echo 1 > "$VERIFIER_LOG_ROOT/reward.txt"
else
  echo 0 > "$VERIFIER_LOG_ROOT/reward.txt"
fi

exit 0
