#!/usr/bin/env bash
set -euo pipefail

APP_ROOT=/app
RUNTIME_ROOT="$APP_ROOT/runtime"
STATE_FILE="$RUNTIME_ROOT/state/publisher_state.json"
CONTEXT_FILE="$RUNTIME_ROOT/state/console_recovery_context.json"
TASK_STATE_DIR=/usr/local/share/debian-digest-recovery
SESSION_META_FILE="$TASK_STATE_DIR/live_tmux_session.json"
SKILL_ENV_FILE="$TASK_STATE_DIR/tmux_skill_env.sh"
PROBE_DIR_BASE=/tmp/.debian-digest-live
DECOY_SOCKET_DIR=/tmp/nanobot-tmux-sockets
TMUX_LABEL_SOCKET_ROOT="/tmp/tmux-$(id -u)"
CODEx_SKILL_DIR=/root/.codex/skills/tmux
CAPABILITY_FILENAME=.debian-digest-recovery-capability
SKILL_AUTH_FILENAME=.harbor-skill-auth
SKILL_AUTH_HASH=2b483d4e08197865dd9fb02b950135081cd11bf6af2c05b67fcca8c1f0dccc50

mkdir -p "$TASK_STATE_DIR" "$DECOY_SOCKET_DIR"

rand_hex() {
  python3 - <<'PY'
import secrets
print(secrets.token_hex(6))
PY
}

wait_for_text_label() {
  local label="$1"
  local target="$2"
  local pattern="$3"
  local timeout="${4:-20}"
  local start
  start="$(date +%s)"
  while true; do
    local pane
    pane="$(tmux -L "$label" capture-pane -p -J -t "$target" -S -400 2>/dev/null || true)"
    if printf '%s\n' "$pane" | grep -E -- "$pattern" >/dev/null 2>&1; then
      return 0
    fi
    if (( $(date +%s) - start >= timeout )); then
      return 1
    fi
    sleep 0.5
  done
}

write_skill_env_file() {
  local probe_dir="$1"
  local skill_env_content
  skill_env_content="export NANOBOT_TMUX_SOCKET_DIR=\"$probe_dir\""

  if has_valid_skill_auth; then
    skill_env_content="$skill_env_content"$'\n'"export NANOBOT_RECOVERY_CAP_FILE=\"$CODEx_SKILL_DIR/$CAPABILITY_FILENAME\""
  fi

  printf '%s\n' "$skill_env_content" > "$SKILL_ENV_FILE"
}

write_capability_file() {
  local capability_token="$1"
  if has_valid_skill_auth; then
    printf '%s\n' "$capability_token" > "$CODEx_SKILL_DIR/$CAPABILITY_FILENAME"
    chmod 600 "$CODEx_SKILL_DIR/$CAPABILITY_FILENAME"
  fi
}

has_valid_skill_auth() {
  local auth_file="$CODEx_SKILL_DIR/$SKILL_AUTH_FILENAME"
  if [[ ! -f "$auth_file" ]]; then
    return 1
  fi

  local auth_hash
  auth_hash="$(
    AUTH_FILE="$auth_file" python3 - <<'PY'
import hashlib
import os
from pathlib import Path

content = Path(os.environ["AUTH_FILE"]).read_text(encoding="utf-8").strip()
print(hashlib.sha256(content.encode("utf-8")).hexdigest())
PY
  )"
  [[ "$auth_hash" == "$SKILL_AUTH_HASH" ]]
}

capability_hash() {
  local capability_token="$1"
  CAPABILITY_TOKEN_INPUT="$capability_token" python3 - <<'PY'
import hashlib
import os

print(hashlib.sha256(os.environ["CAPABILITY_TOKEN_INPUT"].encode("utf-8")).hexdigest())
PY
}

ensure_decoy_socket() {
  local socket="$1"
  local session="$2"
  if ! tmux -S "$socket" has-session -t "$session" 2>/dev/null; then
    tmux -S "$socket" new-session -d -s "$session" -n shell
  fi
}

if [[ -f "$SESSION_META_FILE" ]]; then
  if mapfile -t meta_lines < <(
      SESSION_META_FILE="$SESSION_META_FILE" python3 - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["SESSION_META_FILE"]).read_text(encoding="utf-8"))
print(meta["real_label"])
print(meta["real_session"])
print(meta["probe_dir"])
print(meta["probe_socket_path"])
PY
    ); then
    REAL_LABEL="${meta_lines[0]}"
    REAL_SESSION="${meta_lines[1]}"
    PROBE_DIR="${meta_lines[2]}"
    PROBE_SOCKET_PATH="${meta_lines[3]}"
    if tmux -L "$REAL_LABEL" has-session -t "$REAL_SESSION" 2>/dev/null; then
      mkdir -p "$PROBE_DIR"
      ln -snf "$TMUX_LABEL_SOCKET_ROOT/$REAL_LABEL" "$PROBE_SOCKET_PATH"
      write_skill_env_file "$PROBE_DIR"
      exit 0
    fi
  fi
fi

REAL_LABEL="live$(rand_hex)"
REAL_SESSION="ops$(rand_hex)"
REAL_TARGET="$REAL_SESSION:0.0"
PROBE_DIR="$PROBE_DIR_BASE.$(rand_hex)"
PROBE_SOCKET_PATH="$PROBE_DIR/recovery.sock"
CAPABILITY_TOKEN="$(rand_hex)"
CAPABILITY_HASH="$(capability_hash "$CAPABILITY_TOKEN")"

mkdir -p "$PROBE_DIR"
ln -snf "$TMUX_LABEL_SOCKET_ROOT/$REAL_LABEL" "$PROBE_SOCKET_PATH"
write_capability_file "$CAPABILITY_TOKEN"
write_skill_env_file "$PROBE_DIR"

for name in shared maintenance cache rescue; do
  ensure_decoy_socket "$DECOY_SOCKET_DIR/$name.sock" "$name"
done

tmux -L "$REAL_LABEL" new-session -d -s "$REAL_SESSION" -n console env NANOBOT_RECOVERY_CAP_HASH="$CAPABILITY_HASH" /app/ops/recovery-console
wait_for_text_label "$REAL_LABEL" "$REAL_TARGET" 'recovery-console>' 20

for cmd in resume-pipeline clear-stale-lock rebuild-digest status; do
  tmux -L "$REAL_LABEL" send-keys -t "$REAL_TARGET" -l -- "$cmd"
  tmux -L "$REAL_LABEL" send-keys -t "$REAL_TARGET" Enter
  sleep 0.2
done

wait_for_text_label "$REAL_LABEL" "$REAL_TARGET" 'Publish token:' 20
wait_for_text_label "$REAL_LABEL" "$REAL_TARGET" 'session_id:' 20

PANE_OUTPUT="$(tmux -L "$REAL_LABEL" capture-pane -p -J -t "$REAL_TARGET" -S -300)"
STAGED_CONSOLE_SESSION_ID="$(printf '%s\n' "$PANE_OUTPUT" | awk '/session_id:/ {print $2}' | tail -n 1)"

if [[ -z "$STAGED_CONSOLE_SESSION_ID" ]]; then
  echo "Failed to capture staged recovery console session id" >&2
  exit 1
fi

STAGED_CONSOLE_SESSION_ID="$STAGED_CONSOLE_SESSION_ID" python3 - <<'PY'
import json
import os
from pathlib import Path

state_path = Path("/app/runtime/state/publisher_state.json")
state = json.loads(state_path.read_text(encoding="utf-8"))
state["pipeline_mode"] = "active"
state["stale_lock"] = False
state["draft_ready"] = True
state["published"] = False
state["last_error"] = "publication pending in the existing live recovery session"
state["recovery_owner_session_id"] = os.environ["STAGED_CONSOLE_SESSION_ID"]
state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

context = {
    "staged_console_session_id": state["recovery_owner_session_id"],
    "bootstrap_mode": "pre_staged_tmux_session",
}
Path("/app/runtime/state/console_recovery_context.json").write_text(
    json.dumps(context, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

SESSION_META_FILE="$SESSION_META_FILE" REAL_LABEL="$REAL_LABEL" REAL_SESSION="$REAL_SESSION" PROBE_DIR="$PROBE_DIR" PROBE_SOCKET_PATH="$PROBE_SOCKET_PATH" python3 - <<'PY'
import json
import os
from pathlib import Path

meta = {
    "real_label": os.environ["REAL_LABEL"],
    "real_session": os.environ["REAL_SESSION"],
    "probe_dir": os.environ["PROBE_DIR"],
    "probe_socket_path": os.environ["PROBE_SOCKET_PATH"],
}
Path(os.environ["SESSION_META_FILE"]).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
PY
