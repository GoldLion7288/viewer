#!/bin/bash
# Installation script for Advertisement Video Player Auto-Start
# This script sets up the system to automatically start on boot

set -e  # Exit on error

echo "=========================================="
echo "Advertisement Video Player Auto-Start"
echo "Installation Script"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    echo "Please run: sudo bash $0"
    exit 1
fi

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Script directory: $SCRIPT_DIR"
echo ""

# Step 1: Create required directories
echo "[1/7] Creating required directories..."
mkdir -p /home/pi/viewer
mkdir -p /home/pi/data
mkdir -p /home/pi/download
chown -R pi:pi /home/pi/viewer /home/pi/data /home/pi/download
echo "  ✓ Directories created"
echo ""

# Step 2: Copy configuration file
echo "[2/7] Installing configuration file..."
if [ -f "$SCRIPT_DIR/adver.def" ]; then
    cp "$SCRIPT_DIR/adver.def" /etc/adver.def
    chmod 644 /etc/adver.def
    echo "  ✓ /etc/adver.def installed"
else
    echo "  ⚠ Warning: adver.def not found in $SCRIPT_DIR"
    echo "  You will need to create /etc/adver.def manually"
fi
echo ""

# Step 3: Copy video player files
echo "[3/7] Copying video player files..."
VIEWER_FILES=("run.sh" "run.py" "video.sh")
for file in "${VIEWER_FILES[@]}"; do
    if [ -f "$SCRIPT_DIR/$file" ]; then
        cp "$SCRIPT_DIR/$file" /home/pi/viewer/
        chmod +x "/home/pi/viewer/$file"
        echo "  ✓ $file copied"
    else
        echo "  ⚠ Warning: $file not found"
    fi
done
chown -R pi:pi /home/pi/viewer
echo ""

# Step 4: Check for background image
echo "[4/7] Checking for background image..."
if [ -f "$SCRIPT_DIR/background.jpg" ]; then
    cp "$SCRIPT_DIR/background.jpg" /home/pi/background.jpg
    chown pi:pi /home/pi/background.jpg
    echo "  ✓ background.jpg installed"
elif [ -f "/home/pi/background.jpg" ]; then
    echo "  ✓ background.jpg already exists"
else
    echo "  ⚠ Warning: No background.jpg found"
    echo "  Please place a background image at /home/pi/background.jpg"
fi
echo ""

# Step 5: Install systemd service
echo "[5/7] Installing systemd service..."
if [ -f "$SCRIPT_DIR/adver-player.service" ]; then
    cp "$SCRIPT_DIR/adver-player.service" /etc/systemd/system/
    chmod 644 /etc/systemd/system/adver-player.service
    echo "  ✓ Service file installed"
else
    echo "  ✗ Error: adver-player.service not found"
    exit 1
fi
echo ""

# Step 6: Reload systemd and enable service
echo "[6/7] Enabling auto-start service..."
systemctl daemon-reload
systemctl enable adver-player.service
echo "  ✓ Service enabled for auto-start on boot"
echo ""

# Step 7: Offer to start service now
echo "[7/7] Service installation complete!"
echo ""
echo "=========================================="
echo "Installation Summary"
echo "=========================================="
echo "✓ Configuration: /etc/adver.def"
echo "✓ Viewer files:  /home/pi/viewer/"
echo "✓ Service file:  /etc/systemd/system/adver-player.service"
echo ""
echo "Available commands:"
echo "  sudo systemctl start adver-player    # Start now"
echo "  sudo systemctl stop adver-player     # Stop service"
echo "  sudo systemctl restart adver-player  # Restart service"
echo "  sudo systemctl status adver-player   # Check status"
echo "  sudo journalctl -u adver-player -f   # View logs"
echo ""
echo "The service will automatically start on next boot."
echo ""

read -p "Do you want to start the service now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting service..."
    systemctl start adver-player.service
    sleep 2
    echo ""
    systemctl status adver-player.service --no-pager
    echo ""
    echo "✓ Service started!"
else
    echo "Service not started. It will start automatically on next boot."
fi

echo ""
echo "Installation complete!"
