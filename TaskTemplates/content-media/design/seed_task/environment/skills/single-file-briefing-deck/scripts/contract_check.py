#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


POWER_BRIEF_ROOT = Path("/app/power_brief")


def main() -> int:
    contract = json.loads((POWER_BRIEF_ROOT / "contracts" / "layout_contract.json").read_text(encoding="utf-8"))
    outlines = json.loads((POWER_BRIEF_ROOT / "outlines" / "slide_outline.json").read_text(encoding="utf-8"))
    notes = (POWER_BRIEF_ROOT / "notes" / "editorial_notes.md").read_text(encoding="utf-8")
    outline_index = {page["page_id"]: page for page in outlines["pages"]}

    print("Page checklist")
    print("==============")
    for position, page_id in enumerate(contract["page_order"], start=1):
        page = next(item for item in contract["required_pages"] if item["page_id"] == page_id)
        outline = outline_index[page_id]
        print(f"{position}. {page_id} :: {page['title']}")
        print(f"   wireframe: {page['wireframe']}")
        print(f"   modules : {', '.join(page['required_modules'])}")
        print(f"   charts  : {', '.join(page['required_chart_ids']) if page['required_chart_ids'] else '(none)'}")
        print(f"   note    : {outline['note_summary']}")
    print("\nViewport profiles")
    for profile in contract["viewport_profiles"]:
        print(f"- {profile['name']}: {profile['width']}x{profile['height']}")
    print("\nEditorial note excerpt")
    print(notes.splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
