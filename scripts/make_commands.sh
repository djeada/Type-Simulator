#!/usr/bin/env bash

outfile="commands.txt"
> "$outfile"  # clear/create output

for f in *; do
  if [ -f "$f" ]; then
    {
      echo "vim $f{<enter>}"
      echo "i"

      # Filter: brace-per-line + strip leading whitespace
      sed -E '
        s/[[:space:]]*\{[[:space:]]*/\
{\
/g
        s/[[:space:]]*\}[[:space:]]*/\
}\
/g
        s/^[[:space:]]+//g
      ' -- "$f"

      echo "{<esc>}"
      echo ":wq!{<enter>}"
      echo
      echo
    } >> "$outfile"
  fi
done

