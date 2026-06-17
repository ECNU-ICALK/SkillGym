#!/bin/bash
set -euo pipefail

cp /solution/fixed/service/app.js /app/workspace/service/app.js
cp /solution/fixed/service/dataStore.js /app/workspace/service/dataStore.js

cd /app/workspace
node scripts/reset_runtime_state.js
