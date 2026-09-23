#!/bin/bash
set -euo pipefail

cp /solution/fixed/build_decision_packet.py /root/workspace/build_decision_packet.py
chmod 755 /root/workspace/build_decision_packet.py
python /root/workspace/build_decision_packet.py --data /root/data --output /root/output
