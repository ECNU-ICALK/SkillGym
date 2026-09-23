#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

status=0
pytest -q /tests/test_outputs.py /tests/test_guardrails.py \
  --json-report \
  --json-report-file=/logs/verifier/report.json || status=$?

python3 - <<'PY'
import json
from pathlib import Path

report_path = Path("/logs/verifier/report.json")
reward_path = Path("/logs/verifier/reward.txt")
ctrf_path = Path("/logs/verifier/ctrf.json")

if report_path.exists():
    report = json.loads(report_path.read_text(encoding="utf-8"))
else:
    report = {"tests": [], "summary": {"passed": 0, "failed": 1, "total": 1}}

summary = report.get("summary", {})
failed = summary.get("failed", 0)
reward = 1.0 if failed == 0 else 0.0
reward_path.write_text(f"{reward:.1f}\n", encoding="utf-8")

ctrf = {
    "results": {
        "summary": {
            "tests": summary.get("total", 0),
            "passed": summary.get("passed", 0),
            "failed": failed
        }
    }
}
ctrf_path.write_text(json.dumps(ctrf, indent=2) + "\n", encoding="utf-8")
PY

exit "$status"
