#!/bin/bash

WIDTH=60
HEIGHT=25
XOFF=300
YOFF=50

# Open a new GNOME terminal window with specified geometry and run vi or nano on the provided file
if command -v gnome-terminal >/dev/null 2>&1; then
    if command -v vi >/dev/null 2>&1; then
        gnome-terminal --geometry=${WIDTH}x${HEIGHT}+${XOFF}+${YOFF} -- bash -c "vi '$1'"
    elif command -v nano >/dev/null 2>&1; then
        gnome-terminal --geometry=${WIDTH}x${HEIGHT}+${XOFF}+${YOFF} -- bash -c "nano '$1'"
    else
        echo "No vi or nano found!" >&2
        exit 1
    fi
else
    # Fallback: just run vi or nano in the current terminal
    if command -v vi >/dev/null 2>&1; then
        vi "$1"
    elif command -v nano >/dev/null 2>&1; then
        nano "$1"
    else
        echo "No vi or nano found!" >&2
        exit 1
    fi
fi
