#!/bin/bash
set -euo pipefail

STATE_DIR="${STATE_DIR:-/app/workspace/state}"
mkdir -p "$STATE_DIR"
printf '[]\n' > "$STATE_DIR/shortlist.json"
