#!/usr/bin/env bash
set -euo pipefail

app_root="${TASK_APP_ROOT:-/app}"
task_root="$app_root/workspace"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

solution_root=""
for candidate in \
  "/solution/fixed" \
  "$app_root/solution/fixed" \
  "$script_dir/fixed"
do
  if [ -d "$candidate/chart" ] && [ -d "$candidate/releases" ]; then
    solution_root="$candidate"
    break
  fi
done

if [ -z "$solution_root" ]; then
  echo "Unable to locate fixed chart solution assets" >&2
  exit 1
fi

rm -rf "$task_root/chart" "$task_root/releases"
mkdir -p "$task_root/chart" "$task_root/releases"

cp -R "$solution_root/chart/." "$task_root/chart/"
cp -R "$solution_root/releases/." "$task_root/releases/"

chmod +x "$task_root/scripts/render_release.sh"
