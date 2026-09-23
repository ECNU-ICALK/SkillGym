#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "${SCRIPT_DIR}/fixed_run_pipeline.py" /root/environment/project/run_pipeline.py
chmod +x /root/environment/project/run_pipeline.py
python /root/environment/project/run_pipeline.py \
  --data-dir /root/environment/data/phase_sequences \
  --contract-dir /root/environment/data/contracts \
  --output /root/answer
