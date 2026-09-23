#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
import os
import subprocess
from pathlib import Path

workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
output_file = Path(os.environ.get("TASK_OUTPUT_FILE", "/app/output/release_readiness_report.json"))
output_file.parent.mkdir(parents=True, exist_ok=True)

package = workspace_root / "package"
contract = json.loads((workspace_root / "contracts" / "release_contract.json").read_text(encoding="utf-8"))

def run(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", "-lc", command],
        cwd=package,
        text=True,
        capture_output=True,
        check=False,
    )

checks = {
    "buildability": ("npm run build", run("npm run build")),
    "type_safety": ("npm run typecheck", run("npm run typecheck")),
    "style_checks": ("npm run lint", run("npm run lint")),
    "test_suite": ("npm test -- --coverage", run("npm test -- --coverage")),
    "security_scan": (
        "grep -R -n 'console\\.log' --include='*.ts' --include='*.js' src",
        run("grep -R -n 'console\\.log' --include='*.ts' --include='*.js' src"),
    ),
    "diff_review": ("git diff --name-only", run("git diff --name-only")),
}

gates = []
blocking_issues = []
release_ready = True

for gate in contract["required_gate_order"]:
    name = gate["name"]
    command, result = checks[name]
    if name == "security_scan":
        passed = result.returncode != 0
    elif name == "diff_review":
        passed = not result.stdout.strip()
    else:
        passed = result.returncode == 0

    if name == "security_scan":
        evidence = result.stdout.strip().splitlines()[0] if result.stdout.strip() else "No exposure markers found."
    elif name == "diff_review":
        evidence = result.stdout.strip().splitlines()[0] if result.stdout.strip() else "Working tree is clean."
    else:
        combined = (result.stdout + "\n" + result.stderr).strip()
        evidence = combined.splitlines()[-1] if combined else "Command completed without additional output."

    status = "pass" if passed else "fail"
    gates.append(
        {
            "name": name,
            "status": status,
            "command": command,
            "evidence": evidence,
            "blocking": gate["blocking"],
        }
    )
    if gate["blocking"] and not passed:
        release_ready = False
        blocking_issues.append({"gate": name, "summary": evidence})

report = {
    "project_id": contract["project_id"],
    "release_ready": release_ready,
    "summary": "Candidate is not ready for promotion because the security scan and diff review gates are still failing." if not release_ready else "Candidate satisfies the configured release gates.",
    "gates": gates,
    "blocking_issues": blocking_issues,
    "publishable_artifacts": [],
}

output_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
PY
