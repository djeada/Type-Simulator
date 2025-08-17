#!/usr/bin/env bash

outfile="commands.txt"
script_name="$(basename "$0")"

> "$outfile"  # clear/create output

for f in *; do
  # Only regular files, and skip the output + this script file
  if [ -f "$f" ] && [ "$f" != "$outfile" ] && [ "$f" != "$script_name" ]; then
    {
      echo "vim $f{<enter>}"
      echo "i"

      # 1) Put { and } on their own lines
      # 2) Strip leading whitespace
      # 3) Remove blank line(s) immediately after {
      sed -E '
        s/[[:space:]]*\{[[:space:]]*/\
{\
/g
        s/[[:space:]]*\}[[:space:]]*/\
}\
/g
        s/^[[:space:]]+//g
      ' -- "$f" | awk '
        prev == "{" && NF == 0 { next }  # skip empty line right after {
        { print; prev=$0 }
      '

      echo "{<esc>}"
      echo ":wq!{<enter>}"
      echo
      echo
    } >> "$outfile"
  fi
done
