from __future__ import annotations

from pathlib import Path

from conftest import BASELINE_ROOT, BRIEF_ROOT, OUTPUT_ROOT, current_hash_lines, run_site


def test_input_payload_is_unchanged() -> None:
    expected_input = (BASELINE_ROOT / "power-brief.sha256").read_text(encoding="utf-8")
    assert current_hash_lines(BRIEF_ROOT) == expected_input


def test_output_inventory_is_restricted() -> None:
    result = run_site()
    assert result.returncode == 0, result.stderr or result.stdout
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == {"north_america_power_mix_brief.html", "site_manifest.json"}


def test_outputs_do_not_contain_placeholder_or_verifier_strings() -> None:
    result = run_site()
    assert result.returncode == 0, result.stderr or result.stdout

    html = (OUTPUT_ROOT / "north_america_power_mix_brief.html").read_text(encoding="utf-8").lower()
    manifest = (OUTPUT_ROOT / "site_manifest.json").read_text(encoding="utf-8").lower()
    for text in [html, manifest]:
        assert "placeholder" not in text
        assert "verifier" not in text
        assert "todo" not in text
        assert "tbd" not in text
        assert "draft build output" not in text
    for token in ["/root/.codex/skills", "skill guidance", "runtime check", "checked /root/.codex"]:
        assert token not in manifest


def test_with_skill_logs_are_consistent_if_present() -> None:
    skill_path = Path("/root/.codex/skills/single-file-briefing-deck/SKILL.md")
    agent_log = Path("/logs/agent/codex.txt")
    if not skill_path.exists() or not agent_log.exists():
        return
    log_text = agent_log.read_text(encoding="utf-8", errors="ignore")
    if "single-file-briefing-deck" not in log_text:
        return
    assert (
        "/root/.codex/skills/single-file-briefing-deck/SKILL.md" in log_text
        or "/root/.codex/skills/single-file-briefing-deck/scripts/contract_check.py" in log_text
        or "/root/.codex/skills/single-file-briefing-deck/scripts/data_context.py" in log_text
        or "/root/.codex/skills/single-file-briefing-deck/scripts/browser_audit.py" in log_text
    )
