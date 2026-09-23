from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


APP_ROOT = Path(os.environ.get("TASK_APP_ROOT", "/app"))
WORKSPACE = APP_ROOT / "workspace"
DATA_DIR = APP_ROOT / "data"
AGENT_LOG_CANDIDATES = [
    Path("/logs/agent/codex-task.txt"),
    Path("/logs/agent/codex.txt"),
]

EXPECTED_INPUT_HASHES = {
    "app_contract.json": "8b0c872db9d54b264450cbb4617ff294be7ab11593d9edcd26cad41790f0c3a5",
    "release_matrix.yaml": "2b6b6892d672476900add98e2fa62ebc82622817b4d2807e712f057be4d480f0",
    "platform_labels.json": "c96efa1a502768bfe25feda43032b24222c4b4d03193147454ced5d39cc284a3",
    "render_contract.json": "f91b5c6ec69b96b6a480003dec21e9bfa06ff08167b49a3db1d2340701a0d6e5",
}

EXPECTED_SCRIPT_HASHES = {
    "render_release.sh": "f9f091dd18bc77bb1bf347d0fc1479ace0015b52a3b34d6e7e78f64508994e05",
}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_input_contracts_are_unchanged() -> None:
    for relative, expected in EXPECTED_INPUT_HASHES.items():
        path = DATA_DIR / relative
        assert path.exists(), f"Missing protected input: {relative}"
        assert sha256(path) == expected, f"Protected input changed: {relative}"


def test_render_entrypoint_is_unchanged() -> None:
    for relative, expected in EXPECTED_SCRIPT_HASHES.items():
        path = WORKSPACE / "scripts" / relative
        assert path.exists(), f"Missing required script: {relative}"
        assert sha256(path) == expected, f"Protected script changed: {relative}"


def test_templates_use_helm_expressions() -> None:
    template_dir = WORKSPACE / "chart" / "templates"
    required_templates = [
        "_helpers.tpl",
        "configmap.yaml",
        "deployment.yaml",
        "service.yaml",
        "serviceaccount.yaml",
        "ingress.yaml",
        "hpa.yaml",
        "pdb.yaml",
    ]
    for relative in required_templates:
        path = template_dir / relative
        assert path.exists(), f"Missing template: {relative}"
        text = path.read_text(encoding="utf-8")
        assert "{{" in text, f"Template lacks Helm expressions: {relative}"


def test_workspace_does_not_store_rendered_release_artifacts() -> None:
    forbidden = []
    for path in WORKSPACE.rglob("*"):
        if not path.is_file():
            continue
        lower_name = path.name.lower()
        if lower_name.endswith((".rendered.yaml", ".rendered.yml", "-rendered.yaml", "-rendered.yml")):
            forbidden.append(str(path))
    assert not forbidden, f"Found rendered artifact files in workspace: {forbidden}"


def test_agent_does_not_modify_protected_runtime_artifacts() -> None:
    log_path = next((path for path in AGENT_LOG_CANDIDATES if path.exists()), None)
    if log_path is None:
        return

    log_text = log_path.read_text(encoding="utf-8")
    forbidden_markers = [
        '"type":"file_change","changes":[{"path":"/logs/agent/',
        '"type":"file_change","changes":[{"path":"/logs/verifier/',
        '"type":"file_change","changes":[{"path":"/root/.agents/skills/',
        '"type":"file_change","changes":[{"path":"/root/.codex/skills/',
        '"type":"file_change","changes":[{"path":"/logs/agent/skills/',
        '"type":"file_change","changes":[{"path":"/app/environment/skills/',
    ]
    offending = [marker for marker in forbidden_markers if marker in log_text]
    assert not offending, "agent modified protected runtime artifacts"


def test_agent_trace_consults_bound_helm_skill_before_editing() -> None:
    log_path = next((path for path in AGENT_LOG_CANDIDATES if path.exists()), None)
    if log_path is None:
        return

    skill_read_commands = [
        "/bin/bash -lc \"sed -n '1,220p' /root/.agents/skills/helm-chart-scaffolding/SKILL.md\"",
        "/bin/bash -lc \"sed -n '1,200p' /root/.agents/skills/helm-chart-scaffolding/SKILL.md\"",
        "/bin/bash -lc \"sed -n '1,220p' /root/.codex/skills/helm-chart-scaffolding/SKILL.md\"",
        "/bin/bash -lc \"sed -n '1,200p' /root/.codex/skills/helm-chart-scaffolding/SKILL.md\"",
        "/bin/bash -lc \"sed -n '1,220p' /app/environment/skills/helm-chart-scaffolding/SKILL.md\"",
        "/bin/bash -lc \"sed -n '1,200p' /app/environment/skills/helm-chart-scaffolding/SKILL.md\"",
        "/bin/bash -lc \"sed -n '1,220p' /logs/agent/skills/helm-chart-scaffolding/SKILL.md\"",
        "/bin/bash -lc \"sed -n '1,200p' /logs/agent/skills/helm-chart-scaffolding/SKILL.md\"",
    ]

    skill_line_index: int | None = None
    file_change_line_index: int | None = None

    for line_index, raw_line in enumerate(log_path.read_text(encoding="utf-8").splitlines()):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        item = event.get("item")
        if not isinstance(item, dict):
            continue

        if file_change_line_index is None and item.get("type") == "file_change":
            file_change_line_index = line_index

        if event.get("type") != "item.completed":
            continue
        if item.get("type") != "command_execution":
            continue

        command = item.get("command", "")
        if not isinstance(command, str):
            continue
        if command not in skill_read_commands:
            continue
        if item.get("exit_code") != 0:
            continue
        output = str(item.get("aggregated_output", ""))
        if "name: helm-chart-scaffolding" not in output and "# Helm Chart Scaffolding" not in output:
            continue

        skill_line_index = line_index
        break

    assert skill_line_index is not None, "agent trace did not record a successful read of the bound helm skill"
    if file_change_line_index is not None:
        assert skill_line_index < file_change_line_index, "agent edited chart files before consulting the bound helm skill"
