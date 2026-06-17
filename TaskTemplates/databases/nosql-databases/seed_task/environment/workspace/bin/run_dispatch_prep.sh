#!/bin/bash
set -euo pipefail

mkdir -p /app/output

python3 -m planner.run_dispatch_prep
