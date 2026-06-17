from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
BUNDLE_ROOT = Path(os.environ.get("TASK_BUNDLE_ROOT", ROOT_DIR / "environment" / "reference_bundle"))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", ROOT_DIR / ".tmp_test_output"))
SKILL_ROOT = Path(os.environ.get("TASK_SKILL_ROOT", ROOT_DIR / "environment" / "skills" / "docs-changelog"))
FIXTURES_ROOT = ROOT_DIR / "tests" / "fixtures"
CONTRACT = json.loads((BUNDLE_ROOT / "contracts" / "changelog_contract.json").read_text(encoding="utf-8"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_build(bundle_root: Path = BUNDLE_ROOT, output_root: Path = OUTPUT_ROOT) -> subprocess.CompletedProcess[str]:
    script = bundle_root / "workspace" / "scripts" / "render_changelog.py"
    output_root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TASK_BUNDLE_ROOT"] = str(bundle_root)
    env["TASK_OUTPUT_ROOT"] = str(output_root)
    env["TASK_SKILL_ROOT"] = str(SKILL_ROOT)
    return subprocess.run(
        ["python3", str(script)],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def make_bundle_copy(fixture_name: str | None = None) -> tuple[Path, Path]:
    tmp_root = Path(tempfile.mkdtemp(prefix="changelog-fixture-"))
    bundle_copy = tmp_root / "reference_bundle"
    shutil.copytree(BUNDLE_ROOT, bundle_copy)
    if fixture_name:
        fixture_root = FIXTURES_ROOT / fixture_name
        if (fixture_root / "workspace").exists():
            shutil.rmtree(bundle_copy / "workspace" / "docs" / "changelogs")
            shutil.copytree(fixture_root / "workspace" / "docs" / "changelogs", bundle_copy / "workspace" / "docs" / "changelogs")
        if (fixture_root / "release_payload").exists():
            shutil.rmtree(bundle_copy / "release_payload")
            shutil.copytree(fixture_root / "release_payload", bundle_copy / "release_payload")
    output_root = tmp_root / "output"
    output_root.mkdir(parents=True, exist_ok=True)
    return bundle_copy, output_root


def read_output(output_root: Path, name: str) -> str:
    return (output_root / name).read_text(encoding="utf-8")


def read_manifest(output_root: Path) -> dict:
    return read_json(output_root / "release_manifest.json")


def sha256_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def release_payload(bundle_root: Path) -> dict[str, str]:
    release_root = bundle_root / "release_payload"
    return {
        "version": (release_root / "version.txt").read_text(encoding="utf-8").strip(),
        "released_at": (release_root / "released_at.txt").read_text(encoding="utf-8").strip(),
        "body": (release_root / "body.md").read_text(encoding="utf-8"),
        "release_url": (release_root / "release_url.txt").read_text(encoding="utf-8").strip() if (release_root / "release_url.txt").exists() else "",
    }


def release_channel(version: str) -> str:
    return "preview" if "preview" in version else "stable"


def release_kind(version: str) -> str:
    if "preview" in version:
        return "minor" if version.endswith("preview.0") else "patch"
    return "minor" if version.endswith(".0") else "patch"


def short_date(timestamp: str) -> str:
    return timestamp[:10]


def long_date(timestamp: str) -> str:
    from datetime import datetime, UTC

    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(UTC)
    return dt.strftime("%B %d, %Y")


def extract_full_changelog(body: str) -> str:
    match = re.search(r"\*\*Full Changelog\*\*:\s*(\S+)", body)
    return match.group(1) if match else ""


def processed_items(body: str) -> list[str]:
    lines = body.splitlines()
    started = False
    skip_contributors = False
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "## What's Changed":
            started = True
            skip_contributors = False
            continue
        if not started:
            continue
        if stripped.startswith("## New Contributors"):
            skip_contributors = True
            continue
        if stripped.startswith("**Full Changelog**:"):
            break
        if skip_contributors:
            continue
        if line.startswith("* "):
            item = "- " + line[2:].strip()
            item = re.sub(
                r"https://github.com/google-gemini/gemini-cli/pull/(\d+)",
                lambda m: f"[#{m.group(1)}]({m.group(0)})",
                item,
            )
            items.append(item)
        elif items and stripped:
            items[-1] += "\n  " + stripped
    return items


def top_announcement_header(version: str, released_at: str) -> str:
    return f"## Announcements: {version} - {short_date(released_at)}"

