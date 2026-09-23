from __future__ import annotations

import json
import subprocess

from common import (
    REQUEST,
    expected_release_notes,
    find_hotfix_worktree,
    import_pricing_module,
    load_report,
    release_notes_path,
    report_path,
)


def test_required_output_files_exist() -> None:
    assert report_path().exists(), "Missing artifacts/hotfix_report.json in the hotfix worktree"
    assert release_notes_path().exists(), "Missing artifacts/release_notes.md in the hotfix worktree"


def test_hotfix_script_reruns_successfully() -> None:
    worktree = find_hotfix_worktree()
    result = subprocess.run(
        ["bash", "ops/hotfix/run_hotfix.sh"],
        cwd=worktree,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, f"Hotfix script failed on rerun:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


def test_bare_pytest_succeeds_in_hotfix_worktree() -> None:
    worktree = find_hotfix_worktree()
    result = subprocess.run(
        ["pytest", "-q", "tests/test_pricing.py"],
        cwd=worktree,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, f"Bare pytest should succeed in the hotfix worktree:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


def test_release_notes_match_expected_content() -> None:
    assert release_notes_path().read_text(encoding="utf-8") == expected_release_notes()


def test_report_matches_expected_business_facts() -> None:
    report = load_report()
    worktree = find_hotfix_worktree()

    assert report["service"] == REQUEST["service"]
    assert report["release_version"] == REQUEST["release_version"]
    assert report["release_branch"] == REQUEST["release_branch"]
    assert report["hotfix_branch"] == REQUEST["hotfix_branch"]
    assert report["current_branch"] == REQUEST["hotfix_branch"]
    assert report["smoke_checks_passed"] is True
    assert report["worktree_path"] == str(worktree)
    assert report["release_notes_path"].endswith("/artifacts/release_notes.md")
    assert len(report["git_head"]) == 40


def test_hidden_pricing_regression_cases_pass() -> None:
    calculate_checkout_total = import_pricing_module(find_hotfix_worktree())

    hidden_cases = [
        (10000, 2500, 875, 500, {"tax_cents": 656, "total_cents": 8656}),
        (5200, 1200, 915, 0, {"tax_cents": 366, "total_cents": 4366}),
        (900, 1500, 725, 0, {"tax_cents": 0, "total_cents": 0}),
        (4200, 0, 825, 300, {"tax_cents": 347, "total_cents": 4847}),
    ]
    for subtotal, discount, tax_rate_bps, shipping, expected in hidden_cases:
        result = calculate_checkout_total(subtotal, discount, tax_rate_bps, shipping)
        for key, value in expected.items():
            assert result[key] == value, json.dumps({"inputs": [subtotal, discount, tax_rate_bps, shipping], "result": result})
