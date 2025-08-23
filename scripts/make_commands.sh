#!/usr/bin/env bash

set -euo pipefail

# ---- config via CLI ----
n=0  # default: 0 empty lines after "{"
while getopts ":n:" opt; do
  case "$opt" in
    n)
      if [[ "${OPTARG}" =~ ^[0-9]+$ ]]; then
        n="${OPTARG}"
      else
        echo "Error: -n must be a non-negative integer" >&2
        exit 1
      fi
      ;;
    \?)
      echo "Usage: $0 [-n NUM]" >&2
      exit 1
      ;;
    :)
      echo "Error: Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

outfile="commands.txt"
script_name="$(basename "$0")"

: > "$outfile"  # clear/create output

for f in *; do
  # Only regular files; skip output file and this script
  if [ -f "$f" ] && [ "$f" != "$outfile" ] && [ "$f" != "$script_name" ]; then
    {
      echo "vim $f{<enter>}"
      echo "i"

      # 1) Put { and } on their own lines
      # 2) Strip leading whitespace
      # 3) Ensure EXACTLY N blank lines after each "{"
sed -E '
  # --- remove comment-only lines (after left trim) ---
  /^[[:space:]]*\/\//d

  # --- protect "} ;" so we never split it ---
  s/\}[[:space:]]*;/__RBRACE_SEMI__/g

  # --- put { and } on their own lines (except protected "} ;") ---
  s/[[:space:]]*\{[[:space:]]*/\
{\
/g
  s/[[:space:]]*\}[[:space:]]*/\
}\
/g

  # --- restore "};" (squashes any spaces between } and ;) ---
  s/__RBRACE_SEMI__/};/g

  # --- strip leading whitespace ---
  s/^[[:space:]]+//g
' -- "$f" | awk -v N="$n" '
  {
    if (pending_after_brace) {
      if (NF == 0) next
      for (i = 0; i < N; i++) print ""
      pending_after_brace = 0
    }
    print
    if ($0 == "{") pending_after_brace = 1
  }
  END {
    if (pending_after_brace) for (i = 0; i < N; i++) print ""
  }
'
      echo "{<esc>}"
      echo ":wq!{<enter>}"
      echo
      echo
    } >> "$outfile"
  fi
done
