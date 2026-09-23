from __future__ import annotations

from pathlib import Path

from conftest import BASELINE_SHA256_PATH, CAMPAIGN_ROOT, OUTPUT_ROOT, campaign_integrity_listing, read_text, run_build


def test_input_and_skill_payload_are_unchanged() -> None:
    assert BASELINE_SHA256_PATH.exists()
    expected = BASELINE_SHA256_PATH.read_text(encoding="utf-8")
    actual = campaign_integrity_listing(CAMPAIGN_ROOT)
    assert actual == expected

    skill_root = Path("/app/skills/article-writing")
    if skill_root.exists():
        assert (skill_root / "SKILL.md").exists()


def test_output_inventory_is_restricted() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == {
        "newsletter_intro.md",
        "linkedin_post.md",
        "thread.md",
        "video_script.md",
        "content_manifest.json",
    }


def test_outputs_do_not_contain_placeholder_or_verifier_strings() -> None:
    result = run_build()
    assert result.returncode == 0, result.stderr or result.stdout
    for name in [
        "newsletter_intro.md",
        "linkedin_post.md",
        "thread.md",
        "video_script.md",
        "content_manifest.json",
    ]:
        text = read_text(OUTPUT_ROOT / name).lower()
        assert "verifier" not in text
        assert "todo" not in text
        assert "tbd" not in text
        assert "{{" not in text
