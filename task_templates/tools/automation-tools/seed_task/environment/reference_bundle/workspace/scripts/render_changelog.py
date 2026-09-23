from __future__ import annotations

import json
import os
import re
from datetime import datetime, UTC
from pathlib import Path


BUNDLE_ROOT = Path(os.environ.get("TASK_BUNDLE_ROOT", "/environment/reference_bundle"))
WORKSPACE_ROOT = BUNDLE_ROOT / "workspace"
DOCS_ROOT = WORKSPACE_ROOT / "docs" / "changelogs"
RELEASE_ROOT = BUNDLE_ROOT / "release_payload"
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/environment/output"))
SKILL_ROOT = Path(os.environ.get("TASK_SKILL_ROOT", "/environment/skills/docs-changelog"))


def load_release() -> dict[str, str]:
    version = (RELEASE_ROOT / "version.txt").read_text(encoding="utf-8").strip()
    released_at = (RELEASE_ROOT / "released_at.txt").read_text(encoding="utf-8").strip()
    body = (RELEASE_ROOT / "body.md").read_text(encoding="utf-8")
    return {
        "version": version,
        "released_at": released_at,
        "body": body,
    }


def release_channel(version: str) -> str:
    return "preview" if "preview" in version else "stable"


def release_kind(version: str) -> str:
    return "minor" if version.endswith(".0") else "patch"


def month_day_year(timestamp: str) -> str:
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(UTC)
    return dt.strftime("%B %d, %Y")


def iso_date(timestamp: str) -> str:
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(UTC)
    return dt.strftime("%Y-%m-%d")


def extract_full_changelog(body: str) -> str:
    match = re.search(r"\*\*Full Changelog\*\*:\s*(\S+)", body)
    return match.group(1) if match else ""


def extract_whats_changed(body: str) -> list[str]:
    lines = body.splitlines()
    started = False
    out: list[str] = []
    for line in lines:
        if line.strip() == "## What's Changed":
            started = True
            continue
        if not started:
            continue
        if line.startswith("**Full Changelog**:"):
            break
        if line.startswith("* "):
            out.append("- " + line[2:])
        elif out and line.strip():
            out[-1] += "\n  " + line.strip()
    return out


def naive_highlights(items: list[str]) -> list[str]:
    highlights: list[str] = []
    for item in items:
        if "chore(release)" in item.lower():
            continue
        text = re.sub(r"\s+by @[^ ]+.*$", "", item[2:])
        text = re.sub(r"https://github.com/\S+", "", text).strip()
        title = text.split(":")[0].strip().strip("`").title()
        if not title:
            title = "Release Update"
        highlights.append(f"- **{title}:** {text}.")
        if len(highlights) == 3:
            break
    return highlights or ["- **Release Update:** Review the bundled changelog for the latest changes."]


def render_stable_minor(release: dict[str, str], base_index: str) -> tuple[str, str]:
    items = extract_whats_changed(release["body"])
    highlights = naive_highlights(items)
    latest_template = (SKILL_ROOT / "references" / "latest_template.md").read_text(encoding="utf-8")
    latest = latest_template
    latest = latest.replace("{{version}}", release["version"])
    latest = latest.replace("{{release_date_month_dd_yyyy}}", month_day_year(release["released_at"]))
    latest = latest.replace("{{highlights_content}}", "\n".join(highlights))
    latest = latest.replace("{{changelog_list}}", "\n".join(items))
    latest = latest.replace("{{full_changelog_link}}", extract_full_changelog(release["body"]))
    return latest, base_index


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    release = load_release()
    current_latest = (DOCS_ROOT / "latest.md").read_text(encoding="utf-8")
    current_preview = (DOCS_ROOT / "preview.md").read_text(encoding="utf-8")
    current_index = (DOCS_ROOT / "index.md").read_text(encoding="utf-8")

    if release_channel(release["version"]) == "stable" and release_kind(release["version"]) == "minor":
        latest_out, index_out = render_stable_minor(release, current_index)
        preview_out = current_preview
        updated = ["latest.md"]
        highlights = naive_highlights(extract_whats_changed(release["body"]))
    else:
        latest_out = current_latest
        preview_out = current_preview
        index_out = current_index
        updated = []
        highlights = []

    (OUTPUT_ROOT / "latest.md").write_text(latest_out.rstrip() + "\n", encoding="utf-8")
    (OUTPUT_ROOT / "preview.md").write_text(preview_out.rstrip() + "\n", encoding="utf-8")
    (OUTPUT_ROOT / "index.md").write_text(index_out.rstrip() + "\n", encoding="utf-8")
    manifest = {
        "version": release["version"],
        "release_channel": release_channel(release["version"]),
        "release_kind": release_kind(release["version"]),
        "release_date_iso": iso_date(release["released_at"]),
        "release_date_long": month_day_year(release["released_at"]),
        "updated_files": updated,
        "announcement_prs": [],
        "highlight_titles": [re.sub(r"^- \*\*|\:\*\*.*$", "", item) for item in highlights],
        "full_changelog_url": extract_full_changelog(release["body"]),
    }
    (OUTPUT_ROOT / "release_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
