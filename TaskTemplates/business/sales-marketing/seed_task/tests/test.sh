#!/bin/bash
set -euo pipefail

TESTS_ROOT="${TESTS_ROOT:-/tests}"
VERIFIER_LOG_ROOT="${VERIFIER_LOG_ROOT:-/logs/verifier}"

mkdir -p "$VERIFIER_LOG_ROOT"
if [ -x /opt/.seo-runtime/start_service.sh ]; then
  /opt/.seo-runtime/start_service.sh
elif command -v start-seo-audit >/dev/null 2>&1; then
  start-seo-audit
fi

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
            results.append({
                "nodeid": nodeid,
                "outcome": "failed",
                "message": str(exc),
                "traceback": traceback.format_exc(),
            })
            print(f"FAIL {nodeid}: {exc}")
            traceback.print_exc()

report = {"tests": results, "summary": {"passed": sum(r["outcome"] == "passed" for r in results), "total": len(results)}}
(log_root / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
(log_root / "ctrf.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
raise SystemExit(0 if all(r["outcome"] == "passed" for r in results) else 1)
PY
PYTEST_EXIT=${PIPESTATUS[0]}
set -e

if [ "$PYTEST_EXIT" -eq 0 ]; then
  echo 1 > "$VERIFIER_LOG_ROOT/reward.txt"
else
  echo 0 > "$VERIFIER_LOG_ROOT/reward.txt"
fi

exit 0
