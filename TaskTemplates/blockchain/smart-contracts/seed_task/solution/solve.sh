#!/bin/bash
set -euo pipefail

ROOT_DIR="/root/environment"
OUTPUT_DIR="/root/answer"
FIXED_DIR="$(cd "$(dirname "$0")" && pwd)/fixed"

mkdir -p "${OUTPUT_DIR}"
cp "${FIXED_DIR}/review_core.py" "${ROOT_DIR}/pipeline/review_core.py"
cp "${FIXED_DIR}/run_token_onboarding_review.py" "${ROOT_DIR}/pipeline/run_token_onboarding_review.py"

python "${ROOT_DIR}/pipeline/run_token_onboarding_review.py" --output "${OUTPUT_DIR}"
