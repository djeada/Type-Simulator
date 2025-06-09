#!/usr/bin/env bash
set -euo pipefail

# Tell all Python processes to flush stdout immediately
export PYTHONUNBUFFERED=1

# Run the E2E suite inside Xvfb & let pytest show ALL stdout/stderr (-s)
xvfb-run --auto-servernum \
         --server-args='-screen 0 1024x768x16 -ac' \
         pytest -s -vv tests/e2e
