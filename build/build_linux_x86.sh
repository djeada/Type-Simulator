#!/usr/bin/env bash
# build/build_linux_x86.sh
#
# Exit on any error, undefined var, or pipeline failure
set -euo pipefail

echo "=== Build Linux x86 Executable with Nuitka ==="

# Default to specified Nuitka command or fall back to nuitka3
NUITKA_CMD="${1:-nuitka3}"
shift || true
echo "Using Nuitka command: $NUITKA_CMD"

# 1) Verify Nuitka is installed
if ! command -v "$NUITKA_CMD" &>/dev/null; then
  echo "Error: $NUITKA_CMD not found. Please install Nuitka (pip install nuitka)."
  exit 1
fi

# 2) Check that the source file exists
SRC="../src/main.py"
if [[ ! -f "$SRC" ]]; then
  echo "Error: source file $SRC not found."
  exit 1
fi
echo "Found source file: $SRC"

# 3) Check Python dependencies against requirements.txt
REQ_FILE="../requirements.txt"
echo "Checking Python dependencies from $REQ_FILE..."
if [[ -f "$REQ_FILE" ]]; then
  missing=0
  # Read each non-comment, non-blank line
  while read -r pkg _; do
    [[ "$pkg" =~ ^# ]] && continue
    if ! pip show "$pkg" &>/dev/null; then
      echo "  [MISSING] $pkg"
      missing=1
    else
      echo "  [FOUND]   $pkg"
    fi
  done < <(grep -vE '^\s*#' "$REQ_FILE" | sed '/^\s*$/d' | cut -d'=' -f1)

  if [[ $missing -ne 0 ]]; then
    echo "One or more dependencies are missing. Install with: pip install -r $REQ_FILE"
    exit 1
  fi
else
  echo "Warning: $REQ_FILE not found; skipping dependency check."
fi

# 4) Perform the actual build
if [[ $# -eq 0 ]]; then
  echo "Running default build: standalone, onefile -> dist/"
  "$NUITKA_CMD" \
    --standalone \
    --onefile \
    --output-dir=dist \
    "$SRC"
else
  echo "Running custom build: $NUITKA_CMD $*"
  "$NUITKA_CMD" "$@"
fi

# 5) Summary
echo "Build complete! Check the 'dist' directory for the resulting executable."
