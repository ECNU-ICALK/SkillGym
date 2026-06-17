from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
TASK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE_ROOT = Path("/app/release-watch")
DEFAULT_WORKSPACE_ROOT = Path("/app/workspace")
DEFAULT_OUTPUT_ROOT = Path("/app/output")

BUNDLE_ROOT = Path(os.environ.get("TASK_BUNDLE_ROOT", DEFAULT_BUNDLE_ROOT))
WORKSPACE_ROOT = Path(os.environ.get("TASK_WORKSPACE_ROOT", DEFAULT_WORKSPACE_ROOT))
OUTPUT_ROOT = Path(os.environ.get("TASK_OUTPUT_ROOT", DEFAULT_OUTPUT_ROOT))

if not BUNDLE_ROOT.exists():
    BUNDLE_ROOT = TASK_ROOT / "environment" / "release_watch"
if not WORKSPACE_ROOT.exists():
    WORKSPACE_ROOT = TASK_ROOT / "environment" / "workspace"
if not OUTPUT_ROOT.parent.exists():
    OUTPUT_ROOT = TASK_ROOT / ".tmp_test_output"

BUILD_ENTRYPOINT = WORKSPACE_ROOT / "build_digest.py"


@dataclass(frozen=True)
class Source:
    source_id: str
    label: str
    priority_tier: str
    homepage_url: str
    homepage_snapshot: str
    feed_override_url: str
    feed_override_snapshot: str


@dataclass(frozen=True)
class ReopenTarget:
    source_id: str
    label: str
    url: str
    reason: str


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def contract(bundle_root: Path = BUNDLE_ROOT) -> dict[str, Any]:
    return load_json(bundle_root / "contracts" / "digest_contract.json")


def seed_state(bundle_root: Path = BUNDLE_ROOT) -> dict[str, Any]:
    return load_json(bundle_root / contract(bundle_root)["seed_state_file"])


def load_sources(bundle_root: Path = BUNDLE_ROOT) -> list[Source]:
    rows: list[Source] = []
    with (bundle_root / "data" / "watch_targets.csv").open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                Source(
                    source_id=row["source_id"],
                    label=row["label"],
                    priority_tier=row["priority_tier"],
                    homepage_url=row["homepage_url"],
                    homepage_snapshot=row["homepage_snapshot"],
                    feed_override_url=row["feed_override_url"],
                    feed_override_snapshot=row["feed_override_snapshot"],
                )
            )
    return rows


def load_reopen_targets(bundle_root: Path = BUNDLE_ROOT) -> list[ReopenTarget]:
    rows: list[ReopenTarget] = []
    with (bundle_root / contract(bundle_root)["reopen_targets_file"]).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                ReopenTarget(
                    source_id=row["source_id"],
                    label=row["label"],
                    url=row["url"],
                    reason=row["reason"],
                )
            )
    return rows


def run_build(
    bundle_root: Path = BUNDLE_ROOT,
    workspace_root: Path = WORKSPACE_ROOT,
    output_root: Path = OUTPUT_ROOT,
    clear_state: bool = False,
) -> subprocess.CompletedProcess[str]:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    audit_log_path(workspace_root, bundle_root).unlink(missing_ok=True)
    if clear_state:
        state_db_path(workspace_root, bundle_root).unlink(missing_ok=True)
        reopen_state_path(workspace_root, bundle_root).unlink(missing_ok=True)
    return subprocess.run(
        [
            "python3",
            str(BUILD_ENTRYPOINT),
            "--bundle-root",
            str(bundle_root),
            "--workspace-root",
            str(workspace_root),
            "--output-root",
            str(output_root),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        cwd=workspace_root,
    )


def state_db_path(workspace_root: Path = WORKSPACE_ROOT, bundle_root: Path = BUNDLE_ROOT) -> Path:
    return workspace_root / contract(bundle_root)["state_db_file"]


def audit_log_path(workspace_root: Path = WORKSPACE_ROOT, bundle_root: Path = BUNDLE_ROOT) -> Path:
    return workspace_root / contract(bundle_root)["audit_log_file"]


def reopen_state_path(workspace_root: Path = WORKSPACE_ROOT, bundle_root: Path = BUNDLE_ROOT) -> Path:
    return workspace_root / contract(bundle_root)["reopen_state_file"]


def read_audit_events(workspace_root: Path = WORKSPACE_ROOT, bundle_root: Path = BUNDLE_ROOT) -> list[dict[str, Any]]:
    path = audit_log_path(workspace_root, bundle_root)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_reopen_state(workspace_root: Path = WORKSPACE_ROOT, bundle_root: Path = BUNDLE_ROOT) -> dict[str, Any]:
    path = reopen_state_path(workspace_root, bundle_root)
    return load_json(path) if path.exists() else {}


def output_digest(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> Path:
    return output_root / contract(bundle_root)["output_file"]


def output_inventory(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> Path:
    return output_root / contract(bundle_root)["inventory_file"]


def output_manifest(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> Path:
    return output_root / contract(bundle_root)["manifest_file"]


def read_digest(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> str:
    return output_digest(output_root, bundle_root).read_text(encoding="utf-8")


def read_inventory(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> dict[str, Any]:
    return load_json(output_inventory(output_root, bundle_root))


def read_manifest(output_root: Path = OUTPUT_ROOT, bundle_root: Path = BUNDLE_ROOT) -> dict[str, Any]:
    return load_json(output_manifest(output_root, bundle_root))


def directory_listing(root: Path) -> str:
    if not root.exists():
        return ""
    lines: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(root).as_posix()}")
    return "\n".join(lines) + ("\n" if lines else "")


def normalize_listing_text(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        digest, _, rel_path = line.partition("  ")
        lines.append(f"{digest}  {rel_path.removeprefix('./')}")
    return "\n".join(lines) + ("\n" if lines else "")


def baseline_bundle_listing() -> str:
    candidate = Path("/opt/task-baselines/release-watch.sha256")
    if candidate.exists():
        return normalize_listing_text(candidate.read_text(encoding="utf-8"))
    return directory_listing(BUNDLE_ROOT)


def parse_datetime(text: str) -> str:
    if text.endswith("Z") and "T" in text:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return parsedate_to_datetime(text).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_feed(source: Source, bundle_root: Path = BUNDLE_ROOT) -> list[dict[str, str]]:
    if source.feed_override_snapshot:
        feed_path = bundle_root / "data" / source.feed_override_snapshot
        content_format = "atom" if source.feed_override_snapshot.endswith(".atom") else "rss"
        feed_reference = f"data/{source.feed_override_snapshot}"
    else:
        homepage_path = bundle_root / "data" / source.homepage_snapshot
        html = homepage_path.read_text(encoding="utf-8")
        if 'application/atom+xml' in html:
            href = html.split('href="', 1)[1].split('"', 1)[0].lstrip("/")
            content_format = "atom"
        else:
            href = html.split('href="', 1)[1].split('"', 1)[0].lstrip("/")
            content_format = "rss"
        feed_path = bundle_root / "data" / href
        feed_reference = f"data/{href}"

    root = ET.fromstring(feed_path.read_text(encoding="utf-8"))
    articles: list[dict[str, str]] = []
    if content_format == "rss":
        for item in root.findall("./channel/item"):
            articles.append(
                {
                    "title": (item.findtext("title") or "").strip(),
                    "url": (item.findtext("link") or "").strip(),
                    "published_at": parse_datetime((item.findtext("pubDate") or "").strip()),
                }
            )
    else:
        for entry in root.findall("atom:entry", ATOM_NS):
            link = entry.find("atom:link", ATOM_NS)
            published = (
                entry.findtext("atom:updated", default="", namespaces=ATOM_NS)
                or entry.findtext("atom:published", default="", namespaces=ATOM_NS)
            ).strip()
            articles.append(
                {
                    "title": (entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").strip(),
                    "url": (link.attrib.get("href") if link is not None else "").strip(),
                    "published_at": parse_datetime(published),
                }
            )
    articles.sort(key=lambda row: row["published_at"], reverse=True)
    for row in articles:
        row["resolved_feed_reference"] = feed_reference
        row["content_format"] = content_format
    return articles


def expected_runs(bundle_root: Path = BUNDLE_ROOT) -> list[dict[str, Any]]:
    seed_payload = seed_state(bundle_root)
    read_by_label: dict[str, set[str]] = {}
    for blog in seed_payload["seeded_blogs"]:
        read_by_label[blog["name"]] = set(blog["mark_read_urls"])

    payload = contract(bundle_root)
    delivery_cap = int(payload["per_source_delivery_cap"])
    sources = load_sources(bundle_root)
    reopen_targets = load_reopen_targets(bundle_root)
    seed_read_urls = {url for urls in read_by_label.values() for url in urls}
    already_read_urls = set(seed_read_urls)
    reopen_consumed = False
    current_blog_names = {
        blog["name"] for blog in seed_payload["seeded_blogs"]
    } | {
        blog["name"] for blog in seed_payload["legacy_blogs"]
    }
    expected_blog_names = {source.label for source in sources}
    runs: list[dict[str, Any]] = []

    while True:
        removed_blog_names = sorted(current_blog_names - expected_blog_names)
        current_blog_names = set(expected_blog_names)
        reopened_urls: list[str] = []
        if not reopen_consumed:
            for target in reopen_targets:
                if target.url in already_read_urls:
                    already_read_urls.remove(target.url)
                    reopened_urls.append(target.url)
            reopen_consumed = True
        grouped: dict[str, list[dict[str, str]]] = {"high": [], "standard": []}
        inventory_rows: list[dict[str, Any]] = []
        delivered_urls: list[str] = []
        remaining_unread_urls: list[str] = []
        for source in sources:
            articles = parse_feed(source, bundle_root)
            unread_articles = [row for row in articles if row["url"] not in already_read_urls]
            delivered_rows = unread_articles[:delivery_cap]
            backlog_rows = unread_articles[delivery_cap:]
            grouped[source.priority_tier].extend(
                [
                    {
                        "label": source.label,
                        "title": row["title"],
                        "url": row["url"],
                        "published_at": row["published_at"],
                    }
                    for row in delivered_rows
                ]
            )
            delivered_urls.extend(row["url"] for row in delivered_rows)
            remaining_unread_urls.extend(row["url"] for row in backlog_rows)
            inventory_rows.append(
                {
                    "source_id": source.source_id,
                    "label": source.label,
                    "priority_tier": source.priority_tier,
                    "homepage_url": source.homepage_url,
                    "resolved_feed_reference": articles[0]["resolved_feed_reference"] if articles else "",
                    "content_format": articles[0]["content_format"] if articles else "",
                    "article_count": len(articles),
                    "unread_count": len(unread_articles),
                    "latest_published_at": articles[0]["published_at"] if articles else "",
                }
            )

        grouped["high"].sort(key=lambda row: row["published_at"], reverse=True)
        grouped["standard"].sort(key=lambda row: row["published_at"], reverse=True)
        runs.append(
            {
                "grouped": grouped,
                "inventory_rows": inventory_rows,
                "delivered_urls": delivered_urls,
                "remaining_unread_urls": sorted(remaining_unread_urls),
                "reopened_urls": reopened_urls,
                "tracked_source_ids": [source.source_id for source in sources],
                "removed_blog_names": removed_blog_names,
                "source_files": expected_source_files(bundle_root),
                "seed_read_urls": sorted(seed_read_urls),
            }
        )
        if not delivered_urls:
            break
        already_read_urls.update(delivered_urls)

    return runs


def expected_first_run(bundle_root: Path = BUNDLE_ROOT) -> dict[str, Any]:
    return expected_runs(bundle_root)[0]


def expected_source_files(bundle_root: Path = BUNDLE_ROOT) -> list[str]:
    files = {
        "contracts/digest_contract.json",
        "data/watch_targets.csv",
        contract(bundle_root)["reopen_targets_file"],
        contract(bundle_root)["seed_state_file"],
    }
    for source in load_sources(bundle_root):
        if source.feed_override_snapshot:
            files.add(f"data/{source.feed_override_snapshot}")
        else:
            files.add(f"data/{source.homepage_snapshot}")
            html = (bundle_root / "data" / source.homepage_snapshot).read_text(encoding="utf-8")
            href = html.split('href="', 1)[1].split('"', 1)[0].lstrip("/")
            files.add(f"data/{href}")
    return sorted(files)


def digest_bullets(digest: str, heading: str) -> list[str]:
    marker = f"## {'High Priority' if heading == 'high' else 'Standard Priority'}"
    start = digest.index(marker)
    end = digest.find("\n## ", start + len(marker))
    section = digest[start:end if end != -1 else None]
    return [line for line in section.splitlines() if line.startswith("- ")]


def watch_db_rows(workspace_root: Path = WORKSPACE_ROOT, bundle_root: Path = BUNDLE_ROOT) -> tuple[list[sqlite3.Row], list[sqlite3.Row]]:
    conn = sqlite3.connect(state_db_path(workspace_root, bundle_root))
    conn.row_factory = sqlite3.Row
    try:
        blogs = conn.execute("SELECT name, url, feed_url, last_scanned FROM blogs ORDER BY name").fetchall()
        articles = conn.execute(
            """
            SELECT b.name AS label, a.url, a.title, a.published_date, a.is_read
            FROM articles a
            JOIN blogs b ON b.id = a.blog_id
            ORDER BY b.name, a.published_date DESC
            """
        ).fetchall()
    finally:
        conn.close()
    return blogs, articles


def make_alternate_bundle_copy() -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
    tmpdir = tempfile.TemporaryDirectory()
    root = Path(tmpdir.name)
    alt_bundle = root / "release-watch"
    alt_workspace = root / "workspace"
    shutil.copytree(BUNDLE_ROOT, alt_bundle)
    shutil.copytree(WORKSPACE_ROOT, alt_workspace)
    state_db_path(alt_workspace, alt_bundle).unlink(missing_ok=True)

    feed_path = alt_bundle / "data" / "mirror" / "nodejs-blog" / "feed.xml"
    original = feed_path.read_text(encoding="utf-8")
    injected = """
    <item>
      <title>Node.js 26.2.0 (Current)</title>
      <link>https://nodejs.org/en/blog/release/v26.2.0</link>
      <guid>https://nodejs.org/en/blog/release/v26.2.0</guid>
      <pubDate>Fri, 08 May 2026 10:09:15 GMT</pubDate>
    </item>
"""
    feed_path.write_text(original.replace("<item>\n      <title>Node.js 26.1.0 (Current)</title>", injected + "<item>\n      <title>Node.js 26.1.0 (Current)</title>", 1), encoding="utf-8")
    return tmpdir, alt_bundle, alt_workspace
