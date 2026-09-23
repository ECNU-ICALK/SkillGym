from __future__ import annotations

from pathlib import Path

from conftest import APP_ROOT, DATA_ROOT, stable_hash


EXPECTED_DATA_HASHES = {
    "countries.tsv": "644108cdc9b71485a2569eacb8255d41d165958c0114cc11bbf572131af0a5b1",
    "regions.tsv": "b0a8268af30a988d4cef18660603d7cce7e0c303b2c877d8e652c77c5af1e183",
    "airports.tsv": "751555dd06e295d154cd488ac604ca58a34b64c9ae9e2f7e04ad886badb0712c",
    "runways.tsv": "a70fc1ff5f24c88556f110deef6c1105bca802d548341f1b5dcfd282f6f0263e",
}


def test_input_data_unchanged() -> None:
    for filename, expected_hash in EXPECTED_DATA_HASHES.items():
        assert stable_hash(DATA_ROOT / filename) == expected_hash, filename


def test_shell_chain_is_present_and_executable() -> None:
    scripts = [
        APP_ROOT / "bin" / "rebuild_airport_reports.sh",
        APP_ROOT / "bin" / "steps" / "extract_open_airports.sh",
        APP_ROOT / "bin" / "steps" / "join_runway_stats.sh",
        APP_ROOT / "bin" / "steps" / "build_reports.sh",
    ]
    for script in scripts:
        assert script.exists(), f"missing script: {script}"
        assert script.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")
        assert script.stat().st_mode & 0o111, f"script is not executable: {script}"


def test_bound_skill_assets_are_available_if_present() -> None:
    skill_md = Path("/logs/agent/skills/bash-defensive-patterns/SKILL.md")
    playbook_md = Path("/logs/agent/skills/bash-defensive-patterns/resources/implementation-playbook.md")
    if not skill_md.exists():
        return
    assert skill_md.read_text(encoding="utf-8").strip()
    assert playbook_md.exists()
    assert playbook_md.read_text(encoding="utf-8").strip()
