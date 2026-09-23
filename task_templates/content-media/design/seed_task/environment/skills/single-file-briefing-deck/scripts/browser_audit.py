#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: browser_audit.py /path/to/site.html", file=sys.stderr)
        return 2

    html_path = Path(sys.argv[1]).resolve()
    contract = json.loads(Path("/app/power_brief/contracts/layout_contract.json").read_text(encoding="utf-8"))
    failures: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(html_path.as_uri())
        page.wait_for_timeout(300)

        page_ids = page.locator("[data-page-id]").evaluate_all("(nodes) => nodes.map((node) => node.getAttribute('data-page-id'))")
        if page_ids != contract["page_order"]:
            failures.append(f"page order mismatch: {page_ids}")

        if page.locator("#nav-prev").count() != 1:
            failures.append("missing #nav-prev")
        if page.locator("#nav-next").count() != 1:
            failures.append("missing #nav-next")
        if page.locator('[data-role=\"progress\"]').count() != 1:
            failures.append("missing progress label")

        for profile in contract["viewport_profiles"]:
            page.set_viewport_size({"width": profile["width"], "height": profile["height"]})
            page.wait_for_timeout(150)
            overflows = page.locator("[data-page-id]").evaluate_all(
                """
                (nodes) => nodes.map((node) => {
                  const rect = node.getBoundingClientRect();
                  return {
                    id: node.getAttribute('data-page-id'),
                    overflowY: node.scrollHeight > node.clientHeight + 1,
                    overflowX: node.scrollWidth > node.clientWidth + 1,
                    offscreen: rect.height > window.innerHeight + 1 || rect.width > window.innerWidth + 1
                  };
                })
                """
            )
            for result in overflows:
                if result["overflowY"] or result["overflowX"] or result["offscreen"]:
                    failures.append(f"{profile['name']} overflow: {result['id']}")
        browser.close()

    if failures:
        print(json.dumps({"ok": False, "failures": failures}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "pages": contract["page_order"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
