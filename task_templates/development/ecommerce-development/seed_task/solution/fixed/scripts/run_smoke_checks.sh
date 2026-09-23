#!/bin/bash
set -euo pipefail

bash /opt/bootstrap/start_stack.sh
php /app/workspace/scripts/reseed.php
curl -fsS http://127.0.0.1/wp-json/harbor-printshop/v1/launch-feed >/dev/null
