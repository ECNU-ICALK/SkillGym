#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 4 ]; then
  echo "usage: render_release.sh <release-key> <output-path> [release-name] [namespace]" >&2
  exit 64
fi

release_key="$1"
output_path="$2"
release_name="${3:-$release_key}"

app_root="${TASK_APP_ROOT:-/app}"
chart_dir="$app_root/workspace/chart"
values_file="$app_root/workspace/releases/${release_key}.yaml"

if [ ! -f "$values_file" ]; then
  echo "missing release values: $values_file" >&2
  exit 66
fi

if [ "$#" -ge 4 ]; then
  namespace="$4"
else
  namespace="$(python3 - "$values_file" <<'PY'
import sys
import yaml

with open(sys.argv[1], encoding="utf-8") as handle:
    print(yaml.safe_load(handle)["namespace"])
PY
)"
fi

helm template "$release_name" "$chart_dir" \
  --namespace "$namespace" \
  -f "$chart_dir/values.yaml" \
  -f "$values_file" \
  > "$output_path"
