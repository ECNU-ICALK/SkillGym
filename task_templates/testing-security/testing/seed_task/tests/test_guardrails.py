from __future__ import annotations

import os
from pathlib import Path

from common import (
    baseline_data_manifest,
    baseline_workspace_manifest,
    current_data_manifest,
    current_workspace_manifest,
    workspace_test_text,
)


def test_application_files_outside_test_area_are_unchanged() -> None:
    assert current_workspace_manifest() == baseline_workspace_manifest()


def test_input_data_files_are_unchanged() -> None:
    assert current_data_manifest() == baseline_data_manifest()


def test_suite_does_not_replace_repository_server_wiring() -> None:
    text = workspace_test_text()
    tests_root = Path(os.environ.get("AIRPORT_WORKSPACE_ROOT", "/app/workspace")) / "tests"

    forbidden_markers = (
        "child_process",
        "spawn(",
        "fork(",
        "execFile(",
        "server-control",
        "startServer(",
        "server.js",
    )

    assert all(marker not in text for marker in forbidden_markers)
    assert not any(path.name == "server-control.js" for path in tests_root.rglob("*.js"))
