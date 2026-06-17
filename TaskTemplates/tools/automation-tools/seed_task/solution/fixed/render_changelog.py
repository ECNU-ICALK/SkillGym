from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path


BUNDLE_ROOT = Path(os.environ.get("TASK_BUNDLE_ROOT", "/environment/reference_bundle"))
WORKSPACE_ROOT = BUNDLE_ROOT / "workspace"
DOCS_ROOT = WORKSPACE_ROOT / "docs" / "changelogs"
RELEASE_ROOT = BUNDLE_ROOT / "release_payload"
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", "/environment/output"))
SKILL_ROOT = Path(os.environ.get("TASK_SKILL_ROOT", "/environment/skills/docs-changelog"))


@dataclass
class ChangelogItem:
    raw_text: str
    summary: str
    pr_number: str | None
    pr_url: str | None
    author: str | None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_release() -> dict[str, str]:
    return {
        "version": read_text(RELEASE_ROOT / "version.txt").strip(),
        "released_at": read_text(RELEASE_ROOT / "released_at.txt").strip(),
        "body": read_text(RELEASE_ROOT / "body.md"),
    }


def load_templates() -> dict[str, str]:
    refs = SKILL_ROOT / "references"
    return {
        "index": read_text(refs / "index_template.md"),
        "latest": read_text(refs / "latest_template.md"),
        "preview": read_text(refs / "preview_template.md"),
    }


def release_channel(version: str) -> str:
    if "nightly" in version:
        return "nightly"
    return "preview" if "preview" in version else "stable"


def release_kind(version: str) -> str:
    if "preview" in version:
        return "minor" if version.endswith("preview.0") else "patch"
    return "minor" if version.endswith(".0") else "patch"


def parse_timestamp(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(UTC)


def long_date(timestamp: str) -> str:
    return parse_timestamp(timestamp).strftime("%B %d, %Y")


def short_date(timestamp: str) -> str:
    return parse_timestamp(timestamp).strftime("%Y-%m-%d")


def normalize_pr_links(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        number = match.group(1)
        url = match.group(0)
        return f"[#{number}]({url})"

    return re.sub(r"https://github.com/google-gemini/gemini-cli/pull/(\d+)", repl, text)


def parse_release_body(body: str) -> tuple[list[ChangelogItem], str]:
    full_link_match = re.search(r"\*\*Full Changelog\*\*:\s*(\S+)", body)
    full_link = full_link_match.group(1) if full_link_match else ""

    in_changes = False
    raw_items: list[str] = []
    skip_contributors = False

    for line in body.splitlines():
        stripped = line.strip()
        if stripped == "## What's Changed":
            in_changes = True
            skip_contributors = False
            continue
        if not in_changes:
            continue
        if stripped.startswith("## New Contributors"):
            skip_contributors = True
            continue
        if stripped.startswith("**Full Changelog**:"):
            break
        if skip_contributors:
            continue
        if line.startswith("* "):
            raw_items.append(normalize_pr_links("- " + line[2:].strip()))
        elif raw_items and stripped:
            raw_items[-1] += "\n  " + stripped

    items: list[ChangelogItem] = []
    for item in raw_items:
        compact = re.sub(r"\s+", " ", item)
        pr_match = re.search(r"\[#(\d+)\]\((https://github.com/google-gemini/gemini-cli/pull/\d+)\)", compact)
        author_match = re.search(r" by (@[A-Za-z0-9_.-]+)", compact)
        summary = compact[2:]
        if author_match:
            summary = summary[: author_match.start() - 2].strip()
        elif pr_match:
            summary = summary[: pr_match.start() - 2].strip()
        items.append(
            ChangelogItem(
                raw_text=item,
                summary=summary.rstrip("."),
                pr_number=pr_match.group(1) if pr_match else None,
                pr_url=pr_match.group(2) if pr_match else None,
                author=author_match.group(1) if author_match else None,
            )
        )
    return items, full_link


def semantic_title(summary: str) -> str:
    text = summary
    text = re.sub(r"^[A-Za-z0-9_-]+(?:\([^)]+\))?:\s*", "", text)
    text = text.replace("`", "")
    title_source = text.split(" and ")[0]
    words = re.findall(r"[A-Za-z0-9/.+-]+", title_source)
    words = words[:5]
    if not words:
        return "Release Update"
    title = " ".join(words)
    return title[:1].upper() + title[1:]


def build_highlights(items: list[ChangelogItem], channel: str, limit: int = 5) -> list[str]:
    highlights: list[str] = []
    for item in items:
        lower = item.summary.lower()
        if "changelog for " in lower or "chore(release)" in lower:
            continue
        if channel == "stable" and ("experimental" in lower or "preview" in lower):
            continue
        title = semantic_title(item.summary)
        sentence = item.summary
        if not sentence.endswith("."):
            sentence += "."
        highlights.append(f"- **{title}:** {sentence}")
        if len(highlights) == limit:
            break
    return highlights[: max(3, min(len(highlights), limit))]


def build_announcement(items: list[ChangelogItem], limit: int = 3) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    picked_prs: list[str] = []
    for item in items:
        lower = item.summary.lower()
        if "changelog for " in lower or "chore(release)" in lower:
            continue
        title = semantic_title(item.summary)
        detail = item.summary
        pr_text = ""
        if item.pr_number and item.pr_url:
            picked_prs.append(item.pr_number)
            if item.author:
                pr_text = f" ([#{item.pr_number}]({item.pr_url}) by {item.author})."
            else:
                pr_text = f" ([#{item.pr_number}]({item.pr_url}))."
        else:
            pr_text = "."
        lines.append(f"- **{title}:** {detail}{pr_text}")
        if len(lines) == limit:
            break
    return lines, picked_prs


def insert_announcement(base_index: str, version: str, released_at: str, announcement_lines: list[str], template: str) -> str:
    block = template.replace("{{version}}", version)
    block = block.replace("{{release_date_yyyy_mm_dd}}", short_date(released_at))
    block = block.replace("{{announcement_content}}", "\n".join(announcement_lines))
    marker = "## Announcements:"
    idx = base_index.find(marker)
    if idx == -1:
        return base_index.rstrip() + "\n\n" + block.strip() + "\n"
    return base_index[:idx].rstrip() + "\n\n" + block.strip() + "\n\n" + base_index[idx:].lstrip()


def render_minor_page(template: str, version: str, released_at: str, highlights: list[str], items: list[ChangelogItem], full_link: str) -> str:
    output = template
    output = output.replace("{{version}}", version)
    output = output.replace("{{release_date_month_dd_yyyy}}", long_date(released_at))
    output = output.replace("{{highlights_content}}", "\n".join(highlights))
    output = output.replace("{{changelog_list}}", "\n".join(item.raw_text for item in items))
    output = output.replace("{{full_changelog_link}}", full_link)
    return output.rstrip() + "\n"


def update_patch_page(base_page: str, version: str, released_at: str, items: list[ChangelogItem], full_link: str, header_prefix: str) -> str:
    lines = base_page.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            lines[i] = f"{header_prefix}{version}"
            break
    for i, line in enumerate(lines):
        if line.startswith("Released: "):
            lines[i] = f"Released: {long_date(released_at)}"
            break

    new_block = "\n".join(item.raw_text for item in items).strip()
    heading = "## What's Changed"
    match = re.search(r"## What's Changed\s*\n(?P<body>[\s\S]*?)\n\*\*Full Changelog\*\*:", "\n".join(lines))
    if match:
        old_body = match.group("body").strip()
        combined = f"{new_block}\n{old_body}".strip() if new_block else old_body
        page = re.sub(
            r"## What's Changed\s*\n[\s\S]*?\n\*\*Full Changelog\*\*:",
            f"{heading}\n\n{combined}\n\n**Full Changelog**:",
            "\n".join(lines),
            count=1,
        )
    else:
        page = "\n".join(lines).rstrip() + f"\n\n{heading}\n\n{new_block}\n\n**Full Changelog**: {full_link}\n"

    page = re.sub(r"\*\*Full Changelog\*\*:\s*\S+", f"**Full Changelog**: {full_link}", page, count=1)
    return page.rstrip() + "\n"


def manifest_payload(version: str, channel: str, kind: str, released_at: str, updated_files: list[str], announcement_prs: list[str], highlight_titles: list[str], full_link: str) -> dict[str, object]:
    return {
        "version": version,
        "release_channel": channel,
        "release_kind": kind,
        "release_date_iso": short_date(released_at),
        "release_date_long": long_date(released_at),
        "updated_files": sorted(updated_files),
        "announcement_prs": announcement_prs,
        "highlight_titles": highlight_titles,
        "full_changelog_url": full_link,
    }


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    release = load_release()
    templates = load_templates()
    latest_base = read_text(DOCS_ROOT / "latest.md")
    preview_base = read_text(DOCS_ROOT / "preview.md")
    index_base = read_text(DOCS_ROOT / "index.md")
    channel = release_channel(release["version"])
    kind = release_kind(release["version"])
    items, full_link = parse_release_body(release["body"])

    latest_out = latest_base
    preview_out = preview_base
    index_out = index_base
    updated_files: list[str] = []
    announcement_prs: list[str] = []
    highlight_titles: list[str] = []

    if channel == "stable" and kind == "minor":
        highlights = build_highlights(items, channel)
        highlight_titles = [re.sub(r"^- \*\*(.+?):\*\* .*", r"\1", line) for line in highlights]
        announcement_lines, announcement_prs = build_announcement(items)
        latest_out = render_minor_page(templates["latest"], release["version"], release["released_at"], highlights, items, full_link)
        index_out = insert_announcement(index_base, release["version"], release["released_at"], announcement_lines, templates["index"])
        updated_files = ["latest.md", "index.md"]
    elif channel == "preview" and kind == "minor":
        highlights = build_highlights(items, channel)
        highlight_titles = [re.sub(r"^- \*\*(.+?):\*\* .*", r"\1", line) for line in highlights]
        preview_out = render_minor_page(templates["preview"], release["version"], release["released_at"], highlights, items, full_link)
        updated_files = ["preview.md"]
    elif channel == "stable" and kind == "patch":
        latest_out = update_patch_page(latest_base, release["version"], release["released_at"], items, full_link, "# Latest stable release: ")
        updated_files = ["latest.md"]
    elif channel == "preview" and kind == "patch":
        preview_out = update_patch_page(preview_base, release["version"], release["released_at"], items, full_link, "# Preview release: ")
        updated_files = ["preview.md"]
    else:
        raise RuntimeError(f"Unsupported release path for version {release['version']}")

    (OUTPUT_ROOT / "latest.md").write_text(latest_out, encoding="utf-8")
    (OUTPUT_ROOT / "preview.md").write_text(preview_out, encoding="utf-8")
    (OUTPUT_ROOT / "index.md").write_text(index_out, encoding="utf-8")
    manifest = manifest_payload(
        release["version"],
        channel,
        kind,
        release["released_at"],
        updated_files,
        announcement_prs,
        highlight_titles,
        full_link,
    )
    (OUTPUT_ROOT / "release_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
