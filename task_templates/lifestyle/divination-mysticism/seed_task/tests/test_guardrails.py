from __future__ import annotations

import os
import subprocess
from pathlib import Path

from test_helpers import ACCESS_LOG, access_records


AGENT_LOG = Path("/logs/agent/codex.txt")
TASK_ROOT = Path(os.environ.get("DIVINATION_TASK_ROOT", "/root"))
ARCHIVE_ROOT = Path(os.environ.get("DIVINATION_ARCHIVE_ROOT", "/root/.x-cmd.root/data"))
ARCHIVE_PATH = Path(os.environ.get("DIVINATION_ARCHIVE_PATH", "/root/.x-cmd.root/data/ccal/data/ccal-data-v0.0.6.tar.xz"))
DATA_HASH_PATH = Path(os.environ.get("DIVINATION_DATA_HASH_PATH", "/opt/divination-data.sha256"))
ARCHIVE_HASH_PATH = Path(os.environ.get("DIVINATION_ARCHIVE_HASH_PATH", "/opt/divination-archive.sha256"))
TOOL_HASH_PATH = Path(os.environ.get("DIVINATION_TOOL_HASH_PATH", "/opt/divination-tool.sha256"))
TOOL_PATH = Path(os.environ.get("DIVINATION_TOOL_PATH", "/usr/local/bin/x"))


def test_solver_used_canonical_archive_chain_before_verifier() -> None:
    records = access_records()
    assert records, "No archive access was recorded"
    zuz_calls = [record for record in records if record.get("command") == "x zuz cat"]
    assert zuz_calls, "Solver did not use the canonical x zuz cat workflow"
    archive_paths = {record.get("archive") for record in zuz_calls}
    assert archive_paths == {str(ARCHIVE_PATH)}
    month_reads = {
        str(record.get("member"))
        for record in zuz_calls
        if str(record.get("member", "")).startswith("ccal-data/lunar/2026_")
    }
    assert len(month_reads) >= 8, f"Expected broad month coverage, got {len(month_reads)} month files"


def test_inputs_and_archive_were_not_modified() -> None:
    current_data = subprocess.check_output(
        f"find {TASK_ROOT / 'environment' / 'data'} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    assert current_data == DATA_HASH_PATH.read_text(encoding="utf-8"), "Input data under /root/environment/data was modified"

    current_archive = subprocess.check_output(
        f"find {ARCHIVE_ROOT} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    assert current_archive == ARCHIVE_HASH_PATH.read_text(encoding="utf-8"), "Provisioned archive files were modified"

    current_tool = subprocess.check_output(f"sha256sum {TOOL_PATH}", shell=True, text=True)
    assert current_tool == TOOL_HASH_PATH.read_text(encoding="utf-8"), "The x helper command was modified"


def test_outputs_are_not_shortcuts() -> None:
    assert ACCESS_LOG.exists() and ACCESS_LOG.read_text(encoding="utf-8").strip(), "Access log is empty"


def test_solver_did_not_read_solution_files() -> None:
    if not AGENT_LOG.exists():
        return
    text = AGENT_LOG.read_text(encoding="utf-8")
    forbidden_snippets = [
        "/solution/",
        "prepare_schedule.py",
    ]
    for snippet in forbidden_snippets:
        assert snippet not in text, f"Solver read solution material: {snippet}"


def test_bound_skill_workflow_was_consulted_if_present() -> None:
    skill_md = Path("/logs/agent/skills/ccal/SKILL.md")
    if not skill_md.exists():
        return
    if not AGENT_LOG.exists():
        return
    text = AGENT_LOG.read_text(encoding="utf-8")
    assert "/logs/agent/skills/ccal/SKILL.md" in text, "Solver did not consult the bundled ccal workflow"
