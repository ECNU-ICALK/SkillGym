#!/usr/bin/env bash
set -euo pipefail

FIND_SESSIONS="/root/.codex/skills/tmux/scripts/find-sessions.sh"
GET_RECOVERY_CONTEXT="/root/.codex/skills/tmux/scripts/get-recovery-context.sh"

cleanup() {
  :
}
trap cleanup EXIT

/app/bootstrap/bootstrap_staged_session.sh >/app/runtime/logs/bootstrap-oracle.log 2>&1 || true
if [[ -f /usr/local/share/debian-digest-recovery/tmux_skill_env.sh ]]; then
  # Oracle runs in a non-login shell, so source the task-local tmux discovery env explicitly.
  # Without this, find-sessions.sh would only scan the decoy sockets.
  . /usr/local/share/debian-digest-recovery/tmux_skill_env.sh
fi

eval "$("$GET_RECOVERY_CONTEXT")"

wait_for_text() {
  local socket="$1"
  local target="$2"
  local pattern="$3"
  local timeout="${4:-20}"
  local start
  start="$(date +%s)"
  while true; do
    local pane
    pane="$(tmux -S "$socket" capture-pane -p -J -t "$target" -S -400 2>/dev/null || true)"
    if printf '%s\n' "$pane" | grep -E -- "$pattern" >/dev/null 2>&1; then
      return 0
    fi
    if (( $(date +%s) - start >= timeout )); then
      printf 'Timed out waiting for pattern: %s\n' "$pattern" >&2
      printf 'Last pane output:\n%s\n' "$pane" >&2
      return 1
    fi
    sleep 0.5
  done
}

DISCOVERY="$("$FIND_SESSIONS" --all)"
SOCKET="$(DISCOVERY_TEXT="$DISCOVERY" python3 - <<'PY'
import os
import re

sock = ""
current = ""
for line in os.environ["DISCOVERY_TEXT"].splitlines():
    m = re.match(r"Sessions on socket path '([^']+)':", line)
    if m:
        current = m.group(1)
        continue
    if line.lstrip().startswith("- ") and current:
        sock = current
        break
print(sock)
PY
)"

if [[ -z "$SOCKET" ]]; then
  printf 'Failed to locate staged recovery session.\n%s\n' "$DISCOVERY" >&2
  exit 1
fi

SESSION="$(tmux -S "$SOCKET" list-sessions -F '#{session_name}' | head -n 1)"
TARGET="$SESSION:0.0"

if [[ -z "$SESSION" ]]; then
  printf 'Failed to read live session name from %s.\n' "$SOCKET" >&2
  exit 1
fi

wait_for_text "$SOCKET" "$TARGET" 'Publish token:' 20

PANE="$(tmux -S "$SOCKET" capture-pane -p -J -t "$TARGET" -S -200)"
TOKEN="$(printf '%s\n' "$PANE" | awk '/Publish token:/ {print $3}' | tail -n 1)"

if [[ -z "$TOKEN" ]]; then
  echo "Failed to capture publish token" >&2
  exit 1
fi

tmux -S "$SOCKET" send-keys -t "$TARGET" -l -- "publish-digest $TOKEN"
tmux -S "$SOCKET" send-keys -t "$TARGET" -l -- " $capability_token"
tmux -S "$SOCKET" send-keys -t "$TARGET" Enter

wait_for_text "$SOCKET" "$TARGET" 'Publication complete\.' 20

tmux -S "$SOCKET" send-keys -t "$TARGET" -l -- "write-report /app/output/recovery_report.json $capability_token"
tmux -S "$SOCKET" send-keys -t "$TARGET" Enter

wait_for_text "$SOCKET" "$TARGET" 'Wrote report to /app/output/recovery_report\.json' 20

tmux -S "$SOCKET" send-keys -t "$TARGET" -l -- "exit"
tmux -S "$SOCKET" send-keys -t "$TARGET" Enter
