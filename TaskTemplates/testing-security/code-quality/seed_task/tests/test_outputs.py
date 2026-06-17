from __future__ import annotations

from common import (
    OUTPUT,
    gate_map,
    read_output_contract,
    read_release_contract,
    read_report,
    run_shell,
)


def test_report_exists_and_matches_contract_shape() -> None:
    assert OUTPUT.is_file(), "release_readiness_report.json was not created"
    report = read_report()
    output_contract = read_output_contract()

    assert sorted(report.keys()) == sorted(output_contract["required_top_level_fields"])
    assert isinstance(report["release_ready"], bool)
    assert isinstance(report["summary"], str) and report["summary"].strip()
    assert isinstance(report["gates"], list) and report["gates"]
    assert isinstance(report["blocking_issues"], list)
    assert isinstance(report["publishable_artifacts"], list)


def test_gate_order_matches_release_contract() -> None:
    report = read_report()
    contract = read_release_contract()
    expected = [gate["name"] for gate in contract["required_gate_order"]]
    actual = [gate["name"] for gate in report["gates"]]
    assert actual == expected


def test_release_readiness_decision_and_expected_gate_statuses() -> None:
    report = read_report()
    gates = gate_map(report)

    assert report["project_id"] == "code-quality__toolchain-release-readiness-audit"
    assert report["release_ready"] is False
    assert gates["buildability"]["status"] == "pass"
    assert gates["type_safety"]["status"] == "pass"
    assert gates["style_checks"]["status"] == "pass"
    assert gates["test_suite"]["status"] == "pass"
    assert gates["security_scan"]["status"] == "fail"
    assert gates["diff_review"]["status"] == "fail"


def test_report_matches_independent_command_results() -> None:
    report = read_report()
    gates = gate_map(report)

    build = run_shell("npm run build")
    typecheck = run_shell("npm run typecheck")
    lint = run_shell("npm run lint")
    tests = run_shell("npm test -- --coverage")
    exposure = run_shell("grep -R -n 'console\\.log' --include='*.ts' --include='*.js' src")
    dirty = run_shell("git diff --name-only")

    assert build.exit_code == 0, build.stdout + build.stderr
    assert typecheck.exit_code == 0, typecheck.stdout + typecheck.stderr
    assert lint.exit_code == 0, lint.stdout + lint.stderr
    assert tests.exit_code == 0, tests.stdout + tests.stderr
    assert exposure.exit_code == 0, "Expected at least one exposure marker in tracked source files"
    assert dirty.exit_code == 0 and dirty.stdout.strip(), "Expected tracked modifications in the working tree"

    assert gates["buildability"]["command"].strip()
    assert gates["type_safety"]["command"].strip()
    assert gates["style_checks"]["command"].strip()
    assert gates["test_suite"]["command"].strip()
    assert gates["security_scan"]["command"].strip()
    assert gates["diff_review"]["command"].strip()

    source_command = gates["security_scan"]["command"].lower()
    assert any(marker in source_command for marker in ("grep", "rg"))
    assert "console" in source_command

    change_command = gates["diff_review"]["command"].lower()
    assert "git" in change_command
    assert any(marker in change_command for marker in ("diff", "status"))

    exposure_evidence = gates["security_scan"]["evidence"].lower()
    assert any(
        marker in exposure_evidence
        for marker in (
            "console",
            "frame.ts",
            "logs",
            "debug output",
        )
    )

    hygiene_evidence = gates["diff_review"]["evidence"].lower()
    assert any(marker in hygiene_evidence for marker in ("releasemessaging.ts", "git diff", "tracked"))


def test_blocking_issues_cover_failing_gates() -> None:
    report = read_report()
    issue_gates = {issue["gate"] for issue in report["blocking_issues"]}
    assert {"security_scan", "diff_review"}.issubset(issue_gates)
