#!/bin/bash
set -euo pipefail

cd /root/app
exec python3 -m http.server 4173
