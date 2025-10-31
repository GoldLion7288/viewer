#!/bin/bash

set -euo pipefail

# Use /etc/adver.def as the single source of configuration
# Expected format (by line number):
# 1: SERVICE_NAME (unused here)
# 2: (unused)
# 3: (unused)
# 4: BASE_URL (unused)
# 5: EXEC_DIR (e.g., /home/pi/)
# 6: DATA_DIR (e.g., /home/pi/data/)
# 7: DOWNLOAD_DIR (unused)
# 8: TRIGGER (unused)
# 9: CRON (unused)
# 10: USERNAME (unused here)

CONF="/etc/adver.def"
if [ ! -f "$CONF" ]; then
  echo "Error: $CONF not found."
  exit 1
fi

readarray -t data < "$CONF"

SERVICE_NAME=${data[0]:-}
EXEC_DIR=${data[4]:-}
DATA_DIR=${data[5]:-}

# Normalize directories to always end with '/'
[[ -n "$EXEC_DIR" && "${EXEC_DIR: -1}" != "/" ]] && EXEC_DIR+="/"
[[ -n "$DATA_DIR" && "${DATA_DIR: -1}" != "/" ]] && DATA_DIR+="/"

LAUNCHER="${EXEC_DIR}viewer/run.sh"

if [ ! -x "$LAUNCHER" ]; then
  echo "Error: launcher not found or not executable: $LAUNCHER"
  exit 1
fi

BG="${DATA_DIR}background.jpg"

echo "[$SERVICE_NAME] Starting playlist using: $LAUNCHER"

# Start GUI with background (run.sh expects only the image path for 'start')
"$LAUNCHER" start "$BG"

# Example playlist; adjust files/durations to your needs
"$LAUNCHER" play "${DATA_DIR}test1.mp4" 20
"$LAUNCHER" play "${DATA_DIR}test2.mp4" 20
"$LAUNCHER" play "${DATA_DIR}test3.mp4" 20
"$LAUNCHER" play "${DATA_DIR}test4.mp4" 20

# Return to background and then cleanly exit
"$LAUNCHER" stop
"$LAUNCHER" exit

exit 0
