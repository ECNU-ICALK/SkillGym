#!/bin/bash
set -euo pipefail

API_ROOT="${API_ROOT:-/services/citibike-api}"
CITIBIKE_DATA_DIR="${CITIBIKE_DATA_DIR:-/app/workspace/data}"
CITIBIKE_API_PORT="${CITIBIKE_API_PORT:-3001}"

cd "$API_ROOT"
export CITIBIKE_DATA_DIR CITIBIKE_API_PORT
exec npm start
