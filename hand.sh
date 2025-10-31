#!/bin/bash

# Setup environment for X display (required for GUI)
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority

# Use absolute paths (~ doesn't work in cron)
VIEWER="/home/pi/viewer/run.sh"
DATA="/home/pi/data"
IPC_SOCK="/tmp/video_player_ipc.sock"
MAX_RETRIES=3

# Function to wait for X server
wait_for_x() {
    local count=0
    while [ $count -lt 30 ]; do
        if xset q &>/dev/null; then
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    return 1
}

# Function to check if GUI is running
is_gui_running() {
    [ -S "$IPC_SOCK" ]
}

# Function to cleanup stale processes
cleanup() {
    pkill -f "video_player.py" 2>/dev/null
    rm -f "$IPC_SOCK" 2>/dev/null
    sleep 2
}

# Check if viewer script exists
if [ ! -f "$VIEWER" ]; then
    exit 1
fi

# Wait for X server to be ready
wait_for_x || exit 1

# Cleanup any stale processes
cleanup

# Try to start GUI with retries
for i in $(seq 1 $MAX_RETRIES); do
    "$VIEWER" start "$DATA/background.jpg" 1

    # Wait for GUI to actually start
    sleep 3

    if is_gui_running; then
        break
    fi

    # If last retry failed, exit
    if [ $i -eq $MAX_RETRIES ]; then
        exit 1
    fi

    # Cleanup before retry
    cleanup
done

# Wait a bit more to ensure GUI is fully ready
sleep 2

# Run the playlist
"$VIEWER" play "$DATA/test1.mp4" 20
"$VIEWER" play "$DATA/test2.mp4" 20
"$VIEWER" play "$DATA/test3.mp4" 10
"$VIEWER" play "$DATA/test4.mp4" 10

# Stop and exit
"$VIEWER" stop
"$VIEWER" exit
