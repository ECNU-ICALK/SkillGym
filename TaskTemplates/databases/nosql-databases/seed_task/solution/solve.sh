#!/bin/bash
set -euo pipefail

cp /solution/fixed/planner/engine.py /app/workspace/planner/engine.py
cp /solution/fixed/planner/redis_runtime.py /app/workspace/planner/redis_runtime.py

cd /app/workspace
./bin/run_dispatch_prep.sh
