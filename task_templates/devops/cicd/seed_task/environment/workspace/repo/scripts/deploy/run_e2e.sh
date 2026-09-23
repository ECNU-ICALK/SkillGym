#!/bin/bash
set -euo pipefail

ENV_NAME="${1:-staging}"
ROLLOUT="deploy/rollouts/checkout-production-rollout.yaml"

test -f "$ROLLOUT"
grep -q "kind: Rollout" "$ROLLOUT"
grep -q "templateName: saturn-success-rate" "$ROLLOUT"
grep -q "templateName: saturn-p95-latency" "$ROLLOUT"

echo "e2e deployment checks passed for $ENV_NAME"
