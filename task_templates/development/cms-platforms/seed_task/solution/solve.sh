#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cp -R "$ROOT/solution/fixed/." /app/workspace/
