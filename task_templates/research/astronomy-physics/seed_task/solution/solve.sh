#!/usr/bin/env bash
set -euo pipefail

cp /solution/fixed/build_m101_review.py /root/environment/pipeline/build_m101_review.py
chmod +x /root/environment/pipeline/build_m101_review.py
python /root/environment/pipeline/build_m101_review.py --data /root/environment/data --output /root/answer
