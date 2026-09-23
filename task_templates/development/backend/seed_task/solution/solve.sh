#!/bin/bash
set -euo pipefail

cp /solution/fixed/server.js /app/workspace/server.js
cp /solution/fixed/service/app.js /app/workspace/service/app.js
cp /solution/fixed/service/dataStore.js /app/workspace/service/dataStore.js
cp /solution/fixed/scripts/reset_runtime_state.js /app/workspace/scripts/reset_runtime_state.js

cd /app/workspace
node scripts/reset_runtime_state.js
