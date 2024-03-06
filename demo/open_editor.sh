#!/bin/bash

WIDTH=60
HEIGHT=25
XOFF=300
YOFF=50

# Open a new GNOME terminal window with specified geometry
gnome-terminal --geometry=${WIDTH}x${HEIGHT}+${XOFF}+${YOFF} &
