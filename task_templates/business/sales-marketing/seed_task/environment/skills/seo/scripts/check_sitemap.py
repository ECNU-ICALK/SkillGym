#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request


for path in ["/api/sitemap", "/api/link-graph"]:
    req = urllib.request.Request(f"http://127.0.0.1:8139{path}", headers={"X-Client": "skill-seo-discovery"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    print(json.dumps(payload, indent=2, sort_keys=True))
