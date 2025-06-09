#!/usr/bin/env bash
set -euo pipefail

# start tests under a throw-away X server
xvfb-run --auto-servernum --server-args='-screen 0 1024x768x16 -ac' \
  python3 -m pytest tests/e2e "$@"
