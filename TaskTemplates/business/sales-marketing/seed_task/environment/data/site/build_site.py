#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PAGES_DIR = SRC / "pages"
DIST = ROOT / "dist"
CONFIG_PATH = ROOT / "site_config.json"
REDIRECTS_PATH = SRC / "redirects.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(path: str) -> str:
    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and not path.endswith("/"):
        path += "/"
    return path


def path_to_fs(path: str) -> Path:
    path = normalize_path(path)
    if path == "/":
        return DIST / "index.html"
    return DIST / path.strip("/") / "index.html"


def load_pages() -> dict[str, dict]:
    pages = {}
    for path in sorted(PAGES_DIR.glob("*.json")):
        page = load_json(path)
        page["source_file"] = str(path.relative_to(ROOT))
        page["path"] = normalize_path(page["path"])
        pages[page["page_id"]] = page
    return pages


def source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(
        [CONFIG_PATH, REDIRECTS_PATH] + list(sorted(PAGES_DIR.glob("*.json")))
    ):
        rel = path.relative_to(ROOT).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def render_blocks(blocks: list[dict]) -> str:
    parts = []
    for block in blocks:
        kind = block["type"]
        if kind == "paragraph":
            parts.append(f"<p>{escape(block['text'])}</p>")
        elif kind == "links":
            items = []
            for link in block["links"]:
                items.append(
                    f'<li><a href="{escape(normalize_path(link["href"]))}">{escape(link["label"])}</a></li>'
                )
            parts.append("<ul>" + "".join(items) + "</ul>")
        elif kind == "heading":
            level = int(block.get("level", 2))
            parts.append(f"<h{level}>{escape(block['text'])}</h{level}>")
    return "\n".join(parts)


def page_title(page: dict, config: dict) -> str:
    return f"{page['title']} | {config['site_name']}"


def render_page(page: dict, config: dict) -> str:
    canonical_path = config.get("canonical_overrides", {}).get(page["page_id"], page["canonical_path"])
    canonical_url = config["base_url"] + normalize_path(canonical_path)
    meta_description = page.get("meta_description", "")
    robots = "index,follow" if page.get("indexable", True) else "noindex,nofollow"
    structured_data = page.get("structured_data", [])
    if not structured_data:
        structured_data = [{"@context": "https://schema.org", "@type": "WebPage", "name": page["h1"]}]
    body_html = render_blocks(page.get("body_blocks", []))
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(page_title(page, config))}</title>
    <meta name="description" content="{escape(meta_description)}" />
    <meta name="robots" content="{robots}" />
    <link rel="canonical" href="{escape(canonical_url)}" />
    <script type="application/ld+json">{json.dumps(structured_data, ensure_ascii=False)}</script>
  </head>
  <body data-page-id="{escape(page['page_id'])}">
    <header>
      <nav>
        <a href="/">Home</a>
        <a href="/docs/">Docs</a>
        <a href="/pricing/">Pricing</a>
      </nav>
    </header>
    <main>
      <h1>{escape(page['h1'])}</h1>
      {body_html}
    </main>
    <footer>
      <a href="/pricing/">Pricing</a>
    </footer>
  </body>
</html>
"""


def render_redirect(source_path: str, target_path: str, config: dict) -> str:
    canonical_url = config["base_url"] + normalize_path(target_path)
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta http-equiv="refresh" content="0; url={escape(normalize_path(target_path))}" />
    <meta name="robots" content="noindex,nofollow" />
    <link rel="canonical" href="{escape(canonical_url)}" />
    <title>Moved</title>
  </head>
  <body data-redirect-source="{escape(normalize_path(source_path))}">
    <p>This page moved to <a href="{escape(normalize_path(target_path))}">{escape(normalize_path(target_path))}</a>.</p>
  </body>
</html>
"""


def build_site() -> dict:
    config = load_json(CONFIG_PATH)
    pages = load_pages()
    redirects = {normalize_path(k): normalize_path(v) for k, v in load_json(REDIRECTS_PATH).items()}
    sitemap_allowlist = {
        normalize_path(path)
        for path in config.get("sitemap_allowlist", [])
    }
    DIST.mkdir(parents=True, exist_ok=True)

    for old in DIST.rglob("*"):
        if old.is_file():
            old.unlink()

    built_paths = []
    sitemap_urls = []
    for page in pages.values():
        page_path = page["path"]
        if page_path in redirects:
            continue
        out_path = path_to_fs(page_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(render_page(page, config), encoding="utf-8")
        built_paths.append(page_path)
        in_allowlist = not sitemap_allowlist or page_path in sitemap_allowlist
        if page.get("include_in_sitemap", False) and in_allowlist:
            sitemap_urls.append(config["base_url"] + page_path)

    for source_path, target_path in redirects.items():
        out_path = path_to_fs(source_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(render_redirect(source_path, target_path, config), encoding="utf-8")
        built_paths.append(source_path)

    sitemap = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in sitemap_urls:
        sitemap.append(f"  <url><loc>{escape(url)}</loc></url>")
    sitemap.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    (DIST / "redirects.json").write_text(json.dumps(redirects, indent=2, sort_keys=True), encoding="utf-8")

    meta = {
        "site_id": config["site_id"],
        "source_hash": source_hash(),
        "page_count": len(built_paths),
        "sitemap_url_count": len(sitemap_urls),
    }
    (DIST / ".build-meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    return meta


if __name__ == "__main__":
    print(json.dumps(build_site(), indent=2, sort_keys=True))
