#!/bin/bash
# Video Player Launcher Script for Ubuntu/Raspberry Pi
# Supports: start, play, stop, exit commands

# Set strict error handling
set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
PYTHON_CMD="python3"
MAIN_SCRIPT="run.py"

# Fix Qt platform plugin issues
export QT_QPA_PLATFORM_PLUGIN_PATH=""
export QT_DEBUG_PLUGINS=0
unset QT_PLUGIN_PATH

# Ensure DISPLAY is set
if [ -z "${DISPLAY:-}" ]; then
    export DISPLAY=:0
fi

# Function to show usage
show_usage() {
    echo "Video Player Launcher"
    echo "====================="
    echo "Usage:"
    echo "  $0 start <background_image>  - Start GUI with background (auto-restart if running)"
    echo "  $0 play <file> <duration>    - Play file for duration seconds"
    echo "  $0 stop                      - Stop playback and return to background"
    echo "  $0 exit                      - Exit GUI"
    echo ""
    echo "Examples:"
    echo "  sudo -u pi $0 start /home/pi/background.jpg"
    echo "  sudo -u pi $0 play /home/pi/data/test1.mp4 10"
    echo "  sudo -u pi $0 stop"
    echo "  sudo -u pi $0 exit"
    echo ""
}

# Check if script exists
if [ ! -f "$MAIN_SCRIPT" ]; then
    echo "Error: $MAIN_SCRIPT not found in $SCRIPT_DIR"
    exit 1
fi

# Check arguments
if [ $# -lt 1 ]; then
    show_usage
    exit 1
fi

COMMAND="$1"

# Handle commands
case "$COMMAND" in
    "start")
        if [ $# -lt 2 ]; then
            echo "Error: background image path required"
            show_usage
            exit 1
        fi
        BACKGROUND_IMAGE="$2"

        # Validate background image exists
        if [ ! -f "$BACKGROUND_IMAGE" ]; then
            echo "Warning: Background image '$BACKGROUND_IMAGE' not found"
            # Continue anyway - run.py will handle it
        fi

        echo "Starting Video Player GUI with background: $BACKGROUND_IMAGE"

        # --single-instance flag will auto-restart if already running
        # Run in background and capture output
        $PYTHON_CMD "$MAIN_SCRIPT" --start "$BACKGROUND_IMAGE" --single-instance > /tmp/video_player.log 2>&1 &
        GUI_PID=$!

        # Wait and verify it started
        sleep 2

        if ps -p $GUI_PID > /dev/null 2>&1; then
            echo "GUI started successfully (PID: $GUI_PID)"
            echo "View logs: tail -f /tmp/video_player.log"
        else
            echo "ERROR: GUI failed to start!"
            echo ""
            echo "Error log:"
            echo "=========================================="
            cat /tmp/video_player.log
            echo "=========================================="
            exit 1
        fi
        ;;

    "play")
        if [ $# -lt 3 ]; then
            echo "Error: file path and duration required"
            show_usage
            exit 1
        fi
        FILE_PATH="$2"
        DURATION="$3"

        # Validate file exists
        if [ ! -f "$FILE_PATH" ]; then
            echo "Error: File '$FILE_PATH' not found"
            exit 1
        fi

        # Validate duration is a number
        if ! [[ "$DURATION" =~ ^[0-9]+$ ]]; then
            echo "Error: Duration must be a positive integer (seconds)"
            exit 1
        fi

        echo "Playing: $FILE_PATH for $DURATION seconds"
        $PYTHON_CMD "$MAIN_SCRIPT" --play "$FILE_PATH" "$DURATION" --single-instance
        ;;

    "stop")
        echo "Stopping playback..."
        $PYTHON_CMD "$MAIN_SCRIPT" --stop
        echo "Playback stopped. Returned to background."
        ;;

    "exit")
        echo "Exiting GUI..."
        $PYTHON_CMD "$MAIN_SCRIPT" --exit

        # Wait for clean shutdown
        sleep 0.5
        echo "GUI closed."
        ;;

    *)
        echo "Error: Unknown command '$COMMAND'"
        show_usage
        exit 1
        ;;
esac

exit 0
