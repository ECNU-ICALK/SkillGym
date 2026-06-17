#!/bin/bash
set -euo pipefail

/usr/local/bin/start-wellness-planner

if [ "$#" -eq 0 ]; then
  exec /bin/bash
elif [ "$#" -eq 1 ]; then
  exec /bin/bash -lc "$1"
else
  exec "$@"
fi
