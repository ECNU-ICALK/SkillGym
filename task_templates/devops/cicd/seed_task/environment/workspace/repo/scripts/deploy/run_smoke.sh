#!/bin/bash
set -euo pipefail

ENV_NAME="${1:-staging}"
MANIFEST="deploy/manifests/checkout-deployment.yaml"

test -f "$MANIFEST"
grep -q "name: saturn-checkout" "$MANIFEST"
grep -q "containerPort: 8080" "$MANIFEST"
grep -q "path: /healthz" "$MANIFEST"

echo "smoke checks passed for $ENV_NAME"
