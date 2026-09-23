#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request


req = urllib.request.Request("http://127.0.0.1:8139/api/release-gate", headers={"X-Client": "skill-seo-release-gate"})
with urllib.request.urlopen(req, timeout=10) as resp:
    print(json.dumps(json.loads(resp.read().decode("utf-8")), indent=2, sort_keys=True))
