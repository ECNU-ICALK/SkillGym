#!/bin/bash
set -euo pipefail

SOURCE_ROOT="${1:-/opt/task-skills}"

if [ ! -d "$SOURCE_ROOT" ]; then
  exit 0
fi

shopt -s nullglob

TARGETS=(
  "/root/.codex/skills"
  "/app/workspace/app/.claude/skills"
  "/app/workspace/app/.codex/skills"
  "/app/workspace/app/.agents/skills"
  "/app/workspace/app/.cursor/skills"
  "/root/.gemini/skills"
)

for skill_dir in "$SOURCE_ROOT"/*; do
  [ -d "$skill_dir" ] || continue
  skill_name="$(basename "$skill_dir")"
  for target in "${TARGETS[@]}"; do
    mkdir -p "$target"
    rm -rf "$target/$skill_name"
    cp -R "$skill_dir" "$target/$skill_name"
  done
done
