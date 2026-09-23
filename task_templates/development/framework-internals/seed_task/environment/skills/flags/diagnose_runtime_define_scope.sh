#!/bin/bash
set -euo pipefail

SCENARIO_ID="${1:-${SCENARIO_ID:-docs-segment-cache}}"
SNAPSHOT_PATH="/app/workspace/output/build/${SCENARIO_ID}/runtime-define-snapshot.json"

if [ ! -f "$SNAPSHOT_PATH" ]; then
  exit 0
fi

python3 - "$SNAPSHOT_PATH" <<'PY'
import json
import sys

snapshot_path = sys.argv[1]
with open(snapshot_path, "r", encoding="utf-8") as handle:
    snapshot = json.load(handle)

app_keys = sorted(snapshot.get("app", {}).keys())
server_keys = sorted(snapshot.get("server", {}).keys())
app_only = [key for key in server_keys if key in {"__FRAMEWORK_APP_BUNDLE_ID__", "__FRAMEWORK_RUNTIME_VARIANT__"}]

print("[flags-skill] build diagnostics:")
print(f"[flags-skill]   app keys: {', '.join(app_keys) if app_keys else '(none)'}")
print(f"[flags-skill]   server keys: {', '.join(server_keys) if server_keys else '(none)'}")

if app_only:
    joined = ", ".join(app_only)
    print(f"[flags-skill] app-only define keys leaked into server scope: {joined}")
    print("[flags-skill] For separate app runtime bundles, inspect next-runtime.webpack-config.js scope for bundleType='app'.")
PY
