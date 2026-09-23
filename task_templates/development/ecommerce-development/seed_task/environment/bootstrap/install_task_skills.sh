#!/bin/bash
set -euo pipefail

SRC_ROOT=/opt/task-skills-src

install_root() {
  local dest_root="$1"
  mkdir -p "$dest_root"

  if [ ! -d "$SRC_ROOT" ]; then
    return 0
  fi

  find "$SRC_ROOT" -mindepth 1 -maxdepth 1 -type d | while read -r skill_dir; do
    local skill_name
    skill_name="$(basename "$skill_dir")"
    local dest_dir="$dest_root/$skill_name"
    mkdir -p "$dest_dir"

    if [ -f "$skill_dir/SKILL.md" ]; then
      if head -n 1 "$skill_dir/SKILL.md" | grep -qx -- '---'; then
        cp "$skill_dir/SKILL.md" "$dest_dir/SKILL.md"
      else
        local raw_description
        local yaml_description
        raw_description="$(
          awk 'NF && $0 !~ /^#/ { print; exit }' "$skill_dir/SKILL.md"
        )"
        if [ -z "$raw_description" ]; then
          raw_description="Task-bound workflow for $skill_name."
        fi
        yaml_description="$(printf "%s" "$raw_description" | sed "s/'/''/g")"
        cat > "$dest_dir/SKILL.md" <<EOF
---
name: $skill_name
description: '$yaml_description'
---

EOF
        if [ -d "$skill_dir/task-helper-src" ]; then
          cat >> "$dest_dir/SKILL.md" <<'EOF'
## Task Quickstart

For this task, run these helper probes before large edits and after each substantial reseed:

1. `bash scripts/task_checklist.sh`
2. `bash scripts/probe_store_state.sh`
3. `bash scripts/probe_launch_feed.sh`

Critical task-specific feed checks:

- `department` must use the task's department slug from `met_print_seed.csv`, not a display label.
- `collection` must use the task's collection key from `collection_plan.json`, not a display label.
- Feed SKU / price / availability should follow the primary size option in `collection_plan.json`.

EOF
        fi
        cat "$skill_dir/SKILL.md" >> "$dest_dir/SKILL.md"
      fi
    fi

    find "$skill_dir" -mindepth 1 -maxdepth 1 ! -name 'SKILL.md' ! -name 'task-helper-src' -exec cp -R {} "$dest_dir/" \;

    if [ -d "$skill_dir/task-helper-src" ]; then
      mkdir -p "$dest_dir/scripts"
      find "$skill_dir/task-helper-src" -mindepth 1 -maxdepth 1 -type f -exec cp {} "$dest_dir/scripts/" \;
      chmod +x "$dest_dir"/scripts/* 2>/dev/null || true

      mkdir -p /app/workspace/scripts
      find "$skill_dir/task-helper-src" -mindepth 1 -maxdepth 1 -type f -exec cp {} /app/workspace/scripts/ \;
      chmod +x /app/workspace/scripts/* 2>/dev/null || true
    fi
  done
}

rm -rf /root/.codex/skills /logs/agent/skills
install_root /root/.codex/skills
install_root /logs/agent/skills
