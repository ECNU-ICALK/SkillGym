from __future__ import annotations

from pathlib import Path

from conftest import BRIEFING_ROOT, OUTPUT_ROOT, briefing_integrity, document_markdown, run_packet


EXPECTED_BRIEFING_SHA256 = "01bb72cc29cab5ae20d89ef4bb60640d6e6992ca3ce06557027e149316b5a94f"


def test_input_payload_is_unchanged() -> None:
    integrity = briefing_integrity()
    assert integrity["briefing_sha256"] == EXPECTED_BRIEFING_SHA256


def test_with_skill_agent_reads_shipped_docx_skill_when_available() -> None:
    skill_root = Path("/app/skills/docx")
    agent_log = Path("/logs/agent/codex.txt")
    if not skill_root.exists() or not agent_log.exists():
        return

    log_text = agent_log.read_text(encoding="utf-8", errors="ignore")
    assert "/logs/agent/skills/docx/SKILL.md" in log_text
    assert (
        "/logs/agent/skills/docx/ooxml.md" in log_text
        or "/logs/agent/skills/docx/ooxml/scripts/unpack.py" in log_text
    )


def test_output_inventory_is_restricted() -> None:
    result = run_packet()
    assert result.returncode == 0, result.stderr or result.stdout
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == {"north_america_energy_briefing.docx", "briefing_manifest.json"}


def test_outputs_do_not_contain_placeholder_or_verifier_strings() -> None:
    result = run_packet()
    assert result.returncode == 0, result.stderr or result.stdout

    markdown = document_markdown(OUTPUT_ROOT / "north_america_energy_briefing.docx").lower()
    manifest = (OUTPUT_ROOT / "briefing_manifest.json").read_text(encoding="utf-8").lower()
    assert "placeholder" not in markdown
    for text in [markdown, manifest]:
        assert "verifier" not in text
        assert "todo" not in text
        assert "{{" not in text
        assert "review comment:" not in text
