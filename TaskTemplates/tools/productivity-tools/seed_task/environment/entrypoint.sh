#!/bin/bash
set -euo pipefail

export CODEX_HOME=/logs/agent

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

mkdir -p "$CODEX_HOME/skills" /logs/verifier

copy_skill_dir /root/.codex/skills "$CODEX_HOME/skills"
copy_skill_dir /root/.codex/skills /tmp/codex-home/skills

if [ -d /tmp/codex-home/skills/.system ] && [ ! -d "$CODEX_HOME/skills/.system" ]; then
  mkdir -p "$CODEX_HOME/skills"
  cp -R /tmp/codex-home/skills/.system "$CODEX_HOME/skills/.system"
fi

exec "$@"
