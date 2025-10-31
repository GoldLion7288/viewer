#!/bin/bash

# Setup environment for X display (required for GUI)
export DISPLAY=:0
export XAUTHORITY=/home/pi/.Xauthority

# Wait for X server to be ready
sleep 5

# Use absolute paths (~ doesn't work in cron)
VIEWER="/home/pi/viewer/run.sh"
DATA="/home/pi/data"

# Log start time
echo "========================================" >> /home/pi/hand.log
echo "Starting at: $(date)" >> /home/pi/hand.log

# Check if viewer script exists
if [ ! -f "$VIEWER" ]; then
    echo "ERROR: $VIEWER not found!" >> /home/pi/hand.log
    exit 1
fi

# Run the playlist
"$VIEWER" start "$DATA/background.jpg" 1
"$VIEWER" play "$DATA/test1.mp4" 5
"$VIEWER" play "$DATA/test2.mp4" 8
"$VIEWER" play "$DATA/test3.mp4" 10
"$VIEWER" play "$DATA/test4.mp4" 10
"$VIEWER" stop
"$VIEWER" exit

echo "Finished at: $(date)" >> /home/pi/hand.log
