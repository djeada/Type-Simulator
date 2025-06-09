#!/bin/bash
# Minimal E2E runner for graphical editor typing using Xvfb
set -e

XVFB_DISPLAY=":99"
export DISPLAY=$XVFB_DISPLAY

# Ensure .Xauthority exists to avoid Xlib error
if [ ! -f "$HOME/.Xauthority" ]; then
    touch "$HOME/.Xauthority"
fi

# Start Xvfb in the background
Xvfb $XVFB_DISPLAY -screen 0 1024x768x16 &
XVFB_PID=$!

# Give Xvfb a moment to start
sleep 2

# Run the E2E test
python3 tests/e2e/test_typing_e2e.py
TEST_RESULT=$?

# Stop Xvfb
kill $XVFB_PID

exit $TEST_RESULT
