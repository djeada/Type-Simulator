#!/usr/bin/env bash

outfile="commands.txt"
> "$outfile"  # clear/create output

for f in *; do
  if [ -f "$f" ]; then
    {
      echo "vim $f{<enter>}"
      echo "i"

      # Filter:
      # 1. Put { and } on their own line
      # 2. Strip leading whitespace
      # 3. Remove blank line(s) right after {
      sed -E '
        s/[[:space:]]*\{[[:space:]]*/\
{\
/g
        s/[[:space:]]*\}[[:space:]]*/\
}\
/g
        s/^[[:space:]]+//g
      ' -- "$f" | awk '
        # if previous line was "{", skip empty lines
        prev == "{" && NF == 0 { next }
        { print; prev=$0 }
      '

      echo "{<esc>}"
      echo ":wq!{<enter>}"
      echo
      echo
    } >> "$outfile"
  fi
done
