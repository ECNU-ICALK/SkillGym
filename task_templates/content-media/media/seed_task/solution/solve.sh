#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cp "$SCRIPT_DIR/fixed/build_packet.py" /app/workspace/build_packet.py
python3 /app/workspace/build_packet.py
