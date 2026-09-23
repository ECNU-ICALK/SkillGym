#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request


if len(sys.argv) != 2:
    raise SystemExit("usage: inspect_page.py <page-id>")

page_id = urllib.parse.quote(sys.argv[1], safe="")
req = urllib.request.Request(f"http://127.0.0.1:8139/api/page/{page_id}", headers={"X-Client": "skill-seo-page"})
with urllib.request.urlopen(req, timeout=10) as resp:
    print(json.dumps(json.loads(resp.read().decode("utf-8")), indent=2, sort_keys=True))
