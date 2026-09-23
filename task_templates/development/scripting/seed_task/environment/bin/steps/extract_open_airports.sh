#!/usr/bin/env bash
set -eu

INPUT_FILE=$1
OUTPUT_FILE=$2

awk -F $'\t' 'BEGIN { OFS = FS } NR == 1 { print; next } $2 != "closed" { print }' "$INPUT_FILE" > "$OUTPUT_FILE"
