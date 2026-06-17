#!/usr/bin/env bash
set -Eeuo pipefail

INPUT_FILE="$1"
OUTPUT_FILE="$2"

[[ -f "$INPUT_FILE" ]] || {
  printf 'missing airports input: %s\n' "$INPUT_FILE" >&2
  exit 1
}

awk -F $'\t' 'BEGIN { OFS = FS } NR == 1 { print; next } $2 != "closed" { print }' "$INPUT_FILE" > "$OUTPUT_FILE"
