#!/bin/bash
set -euo pipefail

copy_skill_dir() {
  local source_root="$1"
  local target_root="$2"
  [ -d "$source_root" ] || return 0
  mkdir -p "$target_root"
  shopt -s nullglob
  for skill_dir in "$source_root"/*; do
    [ -d "$skill_dir" ] || continue
    local skill_name
    skill_name="$(basename "$skill_dir")"
    rm -rf "$target_root/$skill_name"
    cp -R "$skill_dir" "$target_root/$skill_name"
  done
}

copy_system_skill_bundle() {
  local source_root="/tmp/codex-home/skills/.system"
  local target_root="/logs/agent/skills/.system"
  [ -d "$source_root" ] || return 0
  mkdir -p "/logs/agent/skills"
  rm -rf "$target_root"
  cp -R "$source_root" "$target_root"
}

copy_workspace_skill_guides() {
  local source_root="/app/skills"
  local workspace_root="/app/workspace"
  [ -d "$source_root" ] || return 0
  [ -d "$workspace_root" ] || return 0

  shopt -s nullglob
  for skill_dir in "$source_root"/*; do
    [ -d "$skill_dir" ] || continue
    local skill_name
    skill_name="$(basename "$skill_dir")"
    rm -rf "$workspace_root/$skill_name"
    cp -R "$skill_dir" "$workspace_root/$skill_name"
  done
}

mkdir -p /logs/agent/skills /tmp/codex-home/skills /logs/verifier

copy_skill_dir /root/.codex/skills /logs/agent/skills
copy_skill_dir /root/.codex/skills /tmp/codex-home/skills
copy_workspace_skill_guides
copy_system_skill_bundle

exec "$@"
