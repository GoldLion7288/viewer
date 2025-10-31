#!/bin/bash
# Alternative installation using cron @reboot
# Use this if you prefer cron over systemd

set -e

echo "=========================================="
echo "Advertisement Video Player"
echo "Cron-based Auto-Start Installation"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    echo "Please run: sudo bash $0"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Step 1: Create directories
echo "[1/4] Creating directories..."
mkdir -p /home/pi/viewer
mkdir -p /home/pi/data
mkdir -p /home/pi/download
chown -R pi:pi /home/pi/viewer /home/pi/data /home/pi/download
echo "  ✓ Done"
echo ""

# Step 2: Copy files
echo "[2/4] Copying files..."
cp "$SCRIPT_DIR"/{run.sh,run.py,video.sh} /home/pi/viewer/ 2>/dev/null || echo "  ⚠ Some files may be missing"
chmod +x /home/pi/viewer/*.sh
chown -R pi:pi /home/pi/viewer

if [ -f "$SCRIPT_DIR/adver.def" ]; then
    cp "$SCRIPT_DIR/adver.def" /etc/adver.def
    chmod 644 /etc/adver.def
fi

if [ -f "$SCRIPT_DIR/background.jpg" ]; then
    cp "$SCRIPT_DIR/background.jpg" /home/pi/background.jpg
    chown pi:pi /home/pi/background.jpg
fi
echo "  ✓ Done"
echo ""

# Step 3: Add cron entry
echo "[3/4] Adding cron entry..."

# Check if entry already exists
if crontab -l 2>/dev/null | grep -q "viewer/video.sh"; then
    echo "  ⚠ Cron entry already exists. Skipping."
else
    # Add new cron entry
    (crontab -l 2>/dev/null; echo "@reboot sleep 10 && /home/pi/viewer/video.sh > /tmp/video_player_cron.log 2>&1") | crontab -
    echo "  ✓ Cron entry added"
fi
echo ""

# Step 4: Show status
echo "[4/4] Installation complete!"
echo ""
echo "=========================================="
echo "Installation Summary"
echo "=========================================="
echo "✓ Files installed to: /home/pi/viewer/"
echo "✓ Cron job added for auto-start"
echo ""
echo "The video player will start automatically on next boot."
echo ""
echo "Commands:"
echo "  sudo crontab -l              # View cron entries"
echo "  sudo crontab -e              # Edit cron entries"
echo "  tail -f /tmp/video_player_cron.log  # View logs"
echo ""

read -p "Do you want to test the video player now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting video player..."
    /home/pi/viewer/video.sh &
    sleep 3
    echo ""
    if pgrep -f "run.py" > /dev/null; then
        echo "✓ Video player is running!"
        echo "  View logs: tail -f /tmp/video_player.log"
    else
        echo "⚠ Video player may not be running. Check logs:"
        echo "  tail /tmp/video_player.log"
    fi
else
    echo "Skipped. The player will start automatically on next boot."
fi

echo ""
echo "Installation complete!"
