#!/usr/bin/env bash
set -euo pipefail

cd /app/workspace/airdesk
make help >/dev/null
make python-init
make release
