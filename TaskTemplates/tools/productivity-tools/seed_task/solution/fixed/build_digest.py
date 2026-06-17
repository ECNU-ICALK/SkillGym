#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


LINK_PATTERN = re.compile(
    r'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']application/(?P<fmt>rss|atom)\+xml["\'][^>]+href=["\'](?P<href>[^"\']+)["\']',
    re.I,
)
REQUIRED_OUTPUTS = {
    "engineering_release_digest.md",
    "feed_inventory.json",
    "delivery_manifest.json",
}


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


@dataclass(frozen=True)
class ResolvedSource:
    source: Source
    homepage_local_url: str
    feed_local_url: str
    resolved_feed_reference: str
    content_format: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the engineering release digest.")
    parser.add_argument("--bundle-root", default="/app/release-watch")
    parser.add_argument("--workspace-root", default="/app/workspace")
    parser.add_argument("--output-root", default="/app/output")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def cleanup_output_dir(output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    for path in output_root.iterdir():
        if path.name not in REQUIRED_OUTPUTS:
            if path.is_dir():
                raise ValueError(f"Unexpected directory in output root: {path}")
            path.unlink()


def load_sources(bundle_root: Path) -> list[Source]:
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


def load_reopen_targets(bundle_root: Path, contract: dict[str, Any]) -> list[ReopenTarget]:
    rows: list[ReopenTarget] = []
    with (bundle_root / contract["reopen_targets_file"]).open("r", encoding="utf-8", newline="") as handle:
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


def replace_block(text: str, tier: str, lines: list[str]) -> str:
    start_marker = f"<!-- DIGEST-START:{tier} -->"
    end_marker = f"<!-- DIGEST-END:{tier} -->"
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker)
    return text[:start] + "\n" + "\n".join(lines) + "\n" + text[end:]


def cleanup_digest_text(text: str, cleanup_tokens: list[str]) -> str:
    cleaned: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        lowered = line.lower()
        if line.startswith("<!-- DIGEST-START:") or line.startswith("<!-- DIGEST-END:"):
            continue
        if any(token in lowered for token in cleanup_tokens):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip() + "\n"


def blogwatcher_binary() -> str:
    binary = shutil.which("blogwatcher")
    if not binary:
        raise FileNotFoundError("blogwatcher is required in PATH")
    return binary


def append_audit_log(audit_log: Path, stage: str, args: list[str]) -> None:
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    with audit_log.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "stage": stage,
                    "args": args,
                }
            )
            + "\n"
        )


def run_blogwatcher(
    db_path: Path,
    args: list[str],
    audit_log: Path,
    stage: str = "build",
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["BLOGWATCHER_DB"] = str(db_path)
    append_audit_log(audit_log, stage, args)
    return subprocess.run(
        [blogwatcher_binary(), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


@contextmanager
def mirror_server(data_root: Path, port: int) -> Iterator[None]:
    process = subprocess.Popen(
        [
            "python3",
            "-m",
            "http.server",
            str(port),
            "--bind",
            "127.0.0.1",
            "--directory",
            str(data_root),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.8)
        yield
    finally:
        process.terminate()
        process.wait(timeout=10)


def local_url(port: int, rel_path: str) -> str:
    return f"http://127.0.0.1:{port}/{rel_path.lstrip('/')}"


def resolve_source(source: Source, bundle_root: Path, port: int) -> ResolvedSource:
    if source.feed_override_snapshot:
        return ResolvedSource(
            source=source,
            homepage_local_url=local_url(port, source.homepage_snapshot),
            feed_local_url=local_url(port, source.feed_override_snapshot),
            resolved_feed_reference=f"data/{source.feed_override_snapshot}",
            content_format="atom" if source.feed_override_snapshot.endswith(".atom") else "rss",
        )

    html = (bundle_root / "data" / source.homepage_snapshot).read_text(encoding="utf-8")
    match = LINK_PATTERN.search(html)
    if not match:
        raise ValueError(f"Unable to discover feed for {source.source_id}")
    href = match.group("href").lstrip("/")
    return ResolvedSource(
        source=source,
        homepage_local_url=local_url(port, source.homepage_snapshot),
        feed_local_url=local_url(port, href),
        resolved_feed_reference=f"data/{href}",
        content_format=match.group("fmt").lower(),
    )


def ensure_seed_db(bundle_root: Path, workspace_root: Path, db_path: Path) -> bool:
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            try:
                tables = {
                    row[0]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                }
            finally:
                conn.close()
            if {"blogs", "articles"}.issubset(tables):
                return False
        except sqlite3.DatabaseError:
            pass
        db_path.unlink(missing_ok=True)
    subprocess.run(
        [
            "python3",
            str(workspace_root / "seed_watch_db.py"),
            "--bundle-root",
            str(bundle_root),
            "--workspace-root",
            str(workspace_root),
            "--db-path",
            str(db_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return True


def tracked_blog_names(db_path: Path) -> list[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT name FROM blogs ORDER BY name").fetchall()
    finally:
        conn.close()
    return [row[0] for row in rows]


def reconcile_tracked_blogs(
    db_path: Path,
    resolved_sources: list[ResolvedSource],
    audit_log: Path,
) -> list[str]:
    expected_names = {item.source.label for item in resolved_sources}
    current_names = set(tracked_blog_names(db_path))
    removed_names = sorted(current_names - expected_names)
    for name in removed_names:
        run_blogwatcher(db_path, ["remove", name, "-y"], audit_log)

    current_names = set(tracked_blog_names(db_path))
    for item in resolved_sources:
        if item.source.label in current_names:
            continue
        run_blogwatcher(
            db_path,
            [
                "add",
                item.source.label,
                item.homepage_local_url,
                "--feed-url",
                item.feed_local_url,
            ],
            audit_log,
        )
    return removed_names


def scan_blogs(db_path: Path, audit_log: Path) -> None:
    run_blogwatcher(db_path, ["scan"], audit_log)


def query_articles(db_path: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
              a.id AS article_id,
              b.name AS label,
              a.title AS title,
              a.url AS url,
              a.published_date AS published_at,
              a.is_read AS is_read
            FROM articles a
            JOIN blogs b ON b.id = a.blog_id
            ORDER BY a.published_date DESC, a.id ASC
            """
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def load_reopen_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"applied_urls": []}
    return load_json(path)


def write_reopen_state(path: Path, applied_urls: list[str]) -> None:
    write_json(
        path,
        {
            "applied_urls": sorted(applied_urls),
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )


def apply_reopen_targets(
    db_path: Path,
    reopen_targets: list[ReopenTarget],
    reopen_state_path: Path,
    audit_log: Path,
) -> list[str]:
    articles_by_url = {row["url"]: row for row in query_articles(db_path)}
    state = load_reopen_state(reopen_state_path)
    applied_urls = set(state.get("applied_urls", []))
    reopened_urls: list[str] = []

    for target in reopen_targets:
        if target.url in applied_urls:
            continue
        row = articles_by_url.get(target.url)
        if not row:
            continue
        applied_urls.add(target.url)
        if int(row["is_read"]) == 1:
            run_blogwatcher(db_path, ["unread", str(row["article_id"])], audit_log)
            reopened_urls.append(target.url)

    write_reopen_state(reopen_state_path, sorted(applied_urls))
    return reopened_urls


def query_inventory_rows(
    db_path: Path,
    resolved_sources: list[ResolvedSource],
) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
              b.name AS label,
              COUNT(a.id) AS article_count,
              SUM(CASE WHEN a.is_read = 0 THEN 1 ELSE 0 END) AS unread_count,
              MAX(a.published_date) AS latest_published_at
            FROM blogs b
            LEFT JOIN articles a ON a.blog_id = b.id
            GROUP BY b.id, b.name
            ORDER BY b.name
            """
        ).fetchall()
    finally:
        conn.close()

    counts_by_label = {row["label"]: dict(row) for row in rows}
    inventory_rows: list[dict[str, Any]] = []
    for item in resolved_sources:
        counts = counts_by_label.get(item.source.label, {})
        inventory_rows.append(
            {
                "source_id": item.source.source_id,
                "label": item.source.label,
                "priority_tier": item.source.priority_tier,
                "homepage_url": item.source.homepage_url,
                "resolved_feed_reference": item.resolved_feed_reference,
                "content_format": item.content_format,
                "article_count": int(counts.get("article_count") or 0),
                "unread_count": int(counts.get("unread_count") or 0),
                "latest_published_at": counts.get("latest_published_at") or "",
            }
        )
    return inventory_rows


def build_unread_groups(
    article_rows: list[dict[str, Any]],
    resolved_sources: list[ResolvedSource],
    delivery_cap: int,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    if delivery_cap < 1:
        raise ValueError("per_source_delivery_cap must be at least 1")
    grouped_source_rows: dict[str, list[dict[str, Any]]] = {item.source.label: [] for item in resolved_sources}
    for row in article_rows:
        if int(row["is_read"]) != 0:
            continue
        if row["label"] not in grouped_source_rows:
            continue
        grouped_source_rows[row["label"]].append(row)
    for rows in grouped_source_rows.values():
        rows.sort(key=lambda row: (row["published_at"], row["article_id"]), reverse=True)

    grouped: dict[str, list[dict[str, Any]]] = {"high": [], "standard": []}
    delivered: list[dict[str, Any]] = []
    for item in resolved_sources:
        rows = grouped_source_rows[item.source.label][:delivery_cap]
        grouped[item.source.priority_tier].extend(rows)
        delivered.extend(rows)

    for rows in grouped.values():
        rows.sort(key=lambda row: (row["published_at"], row["article_id"]), reverse=True)
    return grouped, delivered


def render_digest(
    bundle_root: Path,
    contract: dict[str, Any],
    grouped: dict[str, list[dict[str, Any]]],
    removed_names: list[str],
) -> str:
    draft = (bundle_root / "drafts" / contract["output_file"]).read_text(encoding="utf-8")
    for section in contract["required_sections"]:
        tier = section["tier"]
        rows = grouped[tier]
        lines = [
            f"- {row['label']} | {row['title']} | {str(row['published_at'])[:10]} | {row['url']}"
            for row in rows
        ] or ["No new items."]
        draft = replace_block(draft, tier, lines)
    cleaned = cleanup_digest_text(draft, contract["cleanup_tokens"])
    if removed_names:
        cleaned = (
            cleaned.rstrip()
            + "\n\nRemoved legacy blogs for this run:\n"
            + "\n".join(f"- {name}" for name in removed_names)
            + "\n"
        )
    return cleaned


def mark_delivered_as_read(db_path: Path, delivered_rows: list[dict[str, Any]], audit_log: Path) -> None:
    for row in delivered_rows:
        run_blogwatcher(db_path, ["read", str(row["article_id"])], audit_log)


def build_source_files(bundle_root: Path, contract: dict[str, Any], sources: list[Source]) -> list[str]:
    files = {
        "contracts/digest_contract.json",
        "data/watch_targets.csv",
        contract["reopen_targets_file"],
        contract["seed_state_file"],
    }
    for source in sources:
        if source.feed_override_snapshot:
            files.add(f"data/{source.feed_override_snapshot}")
        else:
            files.add(f"data/{source.homepage_snapshot}")
            html = (bundle_root / "data" / source.homepage_snapshot).read_text(encoding="utf-8")
            match = LINK_PATTERN.search(html)
            if match:
                files.add(f"data/{match.group('href').lstrip('/')}")
    return sorted(files)


def main() -> int:
    args = parse_args()
    bundle_root = Path(args.bundle_root)
    workspace_root = Path(args.workspace_root)
    output_root = Path(args.output_root)
    contract = load_json(bundle_root / "contracts" / "digest_contract.json")
    cleanup_output_dir(output_root)
    audit_log = workspace_root / contract["audit_log_file"]
    reopen_state_path = workspace_root / contract["reopen_state_file"]

    db_path = workspace_root / contract["state_db_file"]
    if ensure_seed_db(bundle_root, workspace_root, db_path):
        reopen_state_path.unlink(missing_ok=True)
    sources = load_sources(bundle_root)
    reopen_targets = load_reopen_targets(bundle_root, contract)
    port = int(contract["local_server_port"])
    delivery_cap = int(contract["per_source_delivery_cap"])

    with mirror_server(bundle_root / "data", port):
        resolved_sources = [resolve_source(source, bundle_root, port) for source in sources]
        removed_names = reconcile_tracked_blogs(db_path, resolved_sources, audit_log)
        scan_blogs(db_path, audit_log)
        reopened_urls = apply_reopen_targets(db_path, reopen_targets, reopen_state_path, audit_log)
        article_rows = query_articles(db_path)
        grouped, delivered_rows = build_unread_groups(article_rows, resolved_sources, delivery_cap)
        inventory_rows = query_inventory_rows(db_path, resolved_sources)
        digest_text = render_digest(bundle_root, contract, grouped, removed_names)
        mark_delivered_as_read(db_path, delivered_rows, audit_log)

    (output_root / contract["output_file"]).write_text(digest_text, encoding="utf-8")
    write_json(
        output_root / contract["inventory_file"],
        {
            "tracked_sources": inventory_rows,
            "removed_blog_names": removed_names,
            "notes": [
                "Unread counts reflect the watch database before this run marked delivered items as read.",
                f"State database: {contract['state_db_file']}",
            ],
        },
    )
    write_json(
        output_root / contract["manifest_file"],
        {
            "digest_path": contract["output_file"],
            "delivered_article_urls": [row["url"] for row in delivered_rows],
            "read_marked_article_urls": [row["url"] for row in delivered_rows],
            "reopened_article_urls": reopened_urls,
            "tracked_source_ids": [source.source_id for source in sources],
            "removed_blog_names": removed_names,
            "source_files": build_source_files(bundle_root, contract, sources),
            "state_db_path": contract["state_db_file"],
            "reopen_state_file": contract["reopen_state_file"],
            "notes": [
                "Tracked blogs were reconciled to the registry before scanning.",
                "The one-time review reopen list was applied through blogwatcher unread before delivery selection.",
                "Delivered unread articles were marked read in the watch database after output generation.",
            ],
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
