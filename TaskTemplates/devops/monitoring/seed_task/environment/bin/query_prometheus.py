#!/usr/bin/env python3
import json
import sys
import urllib.parse
import urllib.request

expr = sys.argv[1]
params = urllib.parse.urlencode({"query": expr})
with urllib.request.urlopen(f"http://127.0.0.1:9090/api/v1/query?{params}", timeout=5) as response:
    payload = json.load(response)
print(json.dumps(payload, indent=2, sort_keys=True))
