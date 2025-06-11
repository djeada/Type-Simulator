#!/usr/bin/env bash
set -euo pipefail

echo "=== Build Linux x86 Executable with Nuitka ==="

# 0) Allow override: pass "nuitka" or "nuitka3" as first arg
NUITKA_CMD="${1:-nuitka}"
shift || true

# 1) Fallback to the other binary if missing
if ! command -v "$NUITKA_CMD" &>/dev/null; then
  alt="nuitka"
  [[ "$NUITKA_CMD" == "nuitka" ]] && alt="nuitka3"
  echo "[warning] '$NUITKA_CMD' not found, trying '$alt'…"
  NUITKA_CMD="$alt"
fi

echo "Using Nuitka command: $NUITKA_CMD"
if ! command -v "$NUITKA_CMD" &>/dev/null; then
  echo "Error: $NUITKA_CMD not found. Install with: pip install -r requirements-dev.txt"
  exit 1
fi

# 2) Auto-discover project root & main script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SRC_FILE="$PROJECT_ROOT/src/main.py"
if [[ ! -f "$SRC_FILE" ]]; then
  echo "Error: source file not found at $SRC_FILE"
  exit 1
fi
echo "Found source file: $SRC_FILE"

# 3) Build
BIN_NAME="type_simulator"
echo "Running default build: standalone, onefile → dist/$BIN_NAME"
"$NUITKA_CMD" \
  --standalone \
  --onefile \
  --output-dir=dist \
  --output-filename="$BIN_NAME" \
  "$SRC_FILE"

echo "Build complete! Artifacts in: $PROJECT_ROOT/dist/"
