from __future__ import annotations

import filecmp
import os
import shutil
import subprocess
from pathlib import Path


DATA_ROOT = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
SKILL_ROOT = Path(os.environ.get("CODEX_SKILLS_DIR", "/root/.codex/skills"))
WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/root/workspace"))
WORKSPACE_ENTRYPOINT = Path(os.environ.get("WORKSPACE_ENTRYPOINT", str(WORKSPACE_ROOT / "run_marine_heat_intake.py")))
DATA_HASH_PATH = Path(os.environ.get("TASK_DATA_HASH", "/opt/task-data.sha256"))
SKILL_HASH_PATH = Path(os.environ.get("TASK_SKILLS_HASH", "/opt/task-skills.sha256"))


def sha_listing(root: Path) -> str:
    if not root.exists():
        return ""
    has_files = subprocess.run(
        ["find", str(root), "-type", "f", "-print", "-quit"],
        check=False,
        capture_output=True,
        text=True,
    )
    if not has_files.stdout.strip():
        return ""
    return subprocess.check_output(
        f"find {root} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )


def test_inputs_and_bound_skills_were_not_modified() -> None:
    expected_data_hash = DATA_HASH_PATH.read_text(encoding="utf-8") if DATA_HASH_PATH.exists() else sha_listing(DATA_ROOT)
    expected_skill_hash = SKILL_HASH_PATH.read_text(encoding="utf-8") if SKILL_HASH_PATH.exists() else sha_listing(SKILL_ROOT)
    assert sha_listing(DATA_ROOT) == expected_data_hash, "Input data under /root/data was modified"
    assert sha_listing(SKILL_ROOT) == expected_skill_hash, "Bound skill files under /root/.codex/skills were modified"


def test_only_expected_output_files_exist() -> None:
    expected = {
        "analysis_intake.md",
        "input_summary.tsv",
        "data_issues.tsv",
        "daily_merged_panel.csv",
        "candidate_windows.csv",
    }
    actual = {path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()}
    assert actual == expected, f"Unexpected output files: {sorted(actual - expected)}; missing: {sorted(expected - actual)}"


def test_workspace_code_discovers_core_inputs() -> None:
    source = WORKSPACE_ENTRYPOINT.read_text(encoding="utf-8")
    for needle in ["screening_contract.json", "metadata", "grids", "buoys"]:
        assert needle in source, f"Workspace solution does not reference required input scope: {needle}"
    assert any(token in source for token in ['glob("*.xml")', "glob('*.xml')", 'glob("*.txt")', "glob('*.txt')"])


def test_official_entrypoint_regenerates_identical_outputs() -> None:
    replay_root = Path("/tmp/marine_heat_replay")
    shutil.rmtree(replay_root, ignore_errors=True)
    replay_root.mkdir(parents=True)
    subprocess.run(
        [
            "python3",
            str(WORKSPACE_ENTRYPOINT),
            "--data",
            str(DATA_ROOT),
            "--output",
            str(replay_root),
        ],
        check=True,
        timeout=180,
    )
    for filename in [
        "analysis_intake.md",
        "input_summary.tsv",
        "data_issues.tsv",
        "daily_merged_panel.csv",
        "candidate_windows.csv",
    ]:
        assert filecmp.cmp(OUTPUT_ROOT / filename, replay_root / filename, shallow=False), f"Replayed output mismatch for {filename}"
