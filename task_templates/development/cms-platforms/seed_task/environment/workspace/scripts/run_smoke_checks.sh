#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
npm run reseed
echo "seed completed"
