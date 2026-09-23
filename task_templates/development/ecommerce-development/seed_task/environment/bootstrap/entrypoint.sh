#!/bin/bash
set -euo pipefail

/opt/bootstrap/start_stack.sh

if [ "$#" -eq 0 ]; then
  exec /bin/bash
elif [ "$#" -eq 1 ]; then
  exec /bin/bash -lc "$1"
else
  exec "$@"
fi
