#!/bin/bash
set -euo pipefail

cp /solution/fixed/build_surveillance.py /app/workspace/marketwatch/build_surveillance.py
python3 /app/workspace/marketwatch/build_surveillance.py
