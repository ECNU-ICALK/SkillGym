#!/usr/bin/env bash
set -euo pipefail

SKILL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CAPABILITY_FILE="$SKILL_ROOT/.debian-digest-recovery-capability"
SOCKET_DIR="${NANOBOT_TMUX_SOCKET_DIR:-}"

if [[ -z "$SOCKET_DIR" ]]; then
  echo "NANOBOT_TMUX_SOCKET_DIR is not set" >&2
  exit 1
fi

if [[ ! -f "$CAPABILITY_FILE" ]]; then
  echo "Recovery capability file not found: $CAPABILITY_FILE" >&2
  exit 1
fi

CAPABILITY_TOKEN="$(tr -d '\r\n' < "$CAPABILITY_FILE")"

cat <<EOF
socket_dir=$SOCKET_DIR
capability_token=$CAPABILITY_TOKEN
EOF
