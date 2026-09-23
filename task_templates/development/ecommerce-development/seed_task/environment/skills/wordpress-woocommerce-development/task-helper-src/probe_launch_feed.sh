#!/bin/bash
set -euo pipefail

bash /opt/bootstrap/start_stack.sh >/tmp/harbor-skill-probe.log 2>&1

BASE_URL="${BASE_URL:-http://127.0.0.1}"

echo "[default]"
curl -fsS "$BASE_URL/wp-json/harbor-printshop/v1/launch-feed"
echo
echo "[collection=portrait-studio]"
curl -fsS "$BASE_URL/wp-json/harbor-printshop/v1/launch-feed?collection=portrait-studio"
echo
echo "[department=asian-art]"
curl -fsS "$BASE_URL/wp-json/harbor-printshop/v1/launch-feed?department=asian-art"
echo
