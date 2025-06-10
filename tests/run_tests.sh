#!/usr/bin/env bash
set -euo pipefail

# Tell all Python processes to flush stdout immediately
export PYTHONUNBUFFERED=1

MODE="${1:-e2e}"

if [[ "$MODE" == "unit" ]]; then
    echo "[INFO] Running unit tests inside Xvfb..."
    xvfb-run --auto-servernum \
        --server-args='-screen 0 1024x768x16 -ac' \
        pytest -s -vv tests/unit_tests
elif [[ "$MODE" == "e2e" ]]; then
    echo "[INFO] Running E2E tests inside Xvfb..."
    xvfb-run --auto-servernum \
        --server-args='-screen 0 1024x768x16 -ac' \
        pytest -s -vv tests/e2e
else
    echo "[ERROR] Unknown test mode: $MODE. Use 'unit' or 'e2e'."
    exit 1
fi
