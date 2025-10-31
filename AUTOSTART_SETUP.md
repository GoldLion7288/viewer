# Auto-Start Setup for Raspberry Pi Video Player

This guide explains how to automatically start the video display system when the Raspberry Pi boots.

## Table of Contents
1. [Method 1: Systemd Service (Recommended)](#method-1-systemd-service-recommended)
2. [Method 2: Cron @reboot (Alternative)](#method-2-cron-reboot-alternative)
3. [Verification and Testing](#verification-and-testing)
4. [Troubleshooting](#troubleshooting)

---

## Method 1: Systemd Service (Recommended)

### Quick Installation

**Option A: Automated Installation Script**

1. Copy all files to Raspberry Pi:
   ```bash
   scp -r * pi@raspberrypi:~/temp-install/
   ```

2. Run the installation script:
   ```bash
   ssh pi@raspberrypi
   cd ~/temp-install
   chmod +x install-autostart.sh
   sudo bash install-autostart.sh
   ```

The script will:
- ✓ Create required directories
- ✓ Install configuration files
- ✓ Copy viewer files
- ✓ Install and enable systemd service
- ✓ Start the service (if you choose)

**Option B: Manual Installation**

1. **Copy files to Raspberry Pi:**
   ```bash
   # Create directories
   sudo mkdir -p /home/pi/viewer
   sudo mkdir -p /home/pi/data
   sudo mkdir -p /home/pi/download

   # Copy viewer files
   sudo cp run.sh run.py video.sh /home/pi/viewer/
   sudo chmod +x /home/pi/viewer/*.sh
   sudo chown -R pi:pi /home/pi/viewer

   # Copy configuration
   sudo cp adver.def /etc/adver.def
   sudo chmod 644 /etc/adver.def

   # Copy background image
   cp background.jpg /home/pi/background.jpg
   ```

2. **Install systemd service:**
   ```bash
   sudo cp adver-player.service /etc/systemd/system/
   sudo chmod 644 /etc/systemd/system/adver-player.service
   sudo systemctl daemon-reload
   ```

3. **Enable auto-start:**
   ```bash
   sudo systemctl enable adver-player.service
   ```

4. **Start service now (optional):**
   ```bash
   sudo systemctl start adver-player.service
   ```

### Service Management Commands

```bash
# Start the service
sudo systemctl start adver-player

# Stop the service
sudo systemctl stop adver-player

# Restart the service
sudo systemctl restart adver-player

# Check service status
sudo systemctl status adver-player

# View live logs
sudo journalctl -u adver-player -f

# View recent logs
sudo journalctl -u adver-player -n 50

# Disable auto-start
sudo systemctl disable adver-player

# Re-enable auto-start
sudo systemctl enable adver-player
```

---

## Method 2: Cron @reboot (Alternative)

If you prefer using cron instead of systemd:

1. **Edit root crontab:**
   ```bash
   sudo crontab -e
   ```

2. **Add this line:**
   ```cron
   @reboot sleep 10 && /home/pi/viewer/video.sh > /tmp/video_player_cron.log 2>&1
   ```

3. **Save and exit** (Ctrl+X, then Y, then Enter)

4. **Verify cron entry:**
   ```bash
   sudo crontab -l
   ```

5. **Test by rebooting:**
   ```bash
   sudo reboot
   ```

**Cron Management:**
```bash
# View root cron jobs
sudo crontab -l

# Edit root cron jobs
sudo crontab -e

# Remove all root cron jobs
sudo crontab -r

# View cron logs
grep CRON /var/log/syslog | tail -20
```

---

## Verification and Testing

### 1. Test Before Auto-Start

Before enabling auto-start, test manually:

```bash
# Test video.sh directly
sudo /home/pi/viewer/video.sh

# Or test run.sh
cd /home/pi/viewer
./run.sh start /home/pi/background.jpg
```

If this works, auto-start should work too.

### 2. Verify Service Installation

```bash
# Check if service file exists
ls -l /etc/systemd/system/adver-player.service

# Check if service is enabled
sudo systemctl is-enabled adver-player

# Check service status
sudo systemctl status adver-player
```

Expected output for enabled service:
```
enabled
```

### 3. Test Auto-Start

```bash
# Reboot the Raspberry Pi
sudo reboot

# After reboot, check if running (via SSH)
ps aux | grep run.py

# Check service status
sudo systemctl status adver-player

# View logs
sudo journalctl -u adver-player -n 50
```

---

## Troubleshooting

### Service won't start

**1. Check service logs:**
```bash
sudo journalctl -u adver-player -n 100 --no-pager
```

**2. Check if video.sh exists:**
```bash
ls -l /home/pi/viewer/video.sh
```

**3. Test video.sh manually:**
```bash
sudo /home/pi/viewer/video.sh
```

**4. Check permissions:**
```bash
ls -l /home/pi/viewer/
# All .sh files should be executable (x)
```

### GUI doesn't appear

**1. Check DISPLAY variable:**
```bash
echo $DISPLAY
# Should show :0 or :1
```

**2. Check X authority:**
```bash
ls -l /home/pi/.Xauthority
# File should exist
```

**3. Check if desktop is running:**
```bash
ps aux | grep -i x11
ps aux | grep -i lightdm
```

**4. Try running manually as pi user:**
```bash
su - pi
export DISPLAY=:0
cd ~/viewer
./run.sh start ~/background.jpg
```

### Python errors

**1. Check if Python packages installed:**
```bash
cd /home/pi/viewer
python3 -c "import PyQt5; import cv2; print('OK')"
```

**2. Install missing packages:**
```bash
sudo apt update
sudo apt install python3-pyqt5 python3-opencv python3-numpy python3-pil
```

**3. Or use virtual environment:**
```bash
cd /home/pi/viewer
python3 -m venv venv
source venv/bin/activate
pip install PyQt5 opencv-python numpy pillow
```

### Check video player log

```bash
# Check direct output log
tail -f /tmp/video_player.log

# Check system journal
sudo journalctl -u adver-player -f
```

### Disable auto-start temporarily

```bash
# Stop and disable service
sudo systemctl stop adver-player
sudo systemctl disable adver-player

# Service won't start on next boot
# Re-enable with: sudo systemctl enable adver-player
```

---

## Configuration Files Reference

### Directory Structure
```
/home/pi/
├── viewer/
│   ├── run.sh          # Main launcher
│   ├── run.py          # Python player
│   ├── video.sh        # Startup script
│   └── venv/           # (optional) Virtual environment
├── data/               # Video files
├── download/           # Download directory
├── background.jpg      # Background image
└── cron               # Cron permission file

/etc/
├── adver.def                        # Configuration
└── systemd/system/
    └── adver-player.service        # Service file
```

### Important Paths
- Service file: `/etc/systemd/system/adver-player.service`
- Configuration: `/etc/adver.def`
- Main script: `/home/pi/viewer/video.sh`
- Logs: `/tmp/video_player.log` and `journalctl`

---

## Uninstall

To completely remove auto-start:

```bash
# Stop and disable service
sudo systemctl stop adver-player
sudo systemctl disable adver-player

# Remove service file
sudo rm /etc/systemd/system/adver-player.service
sudo systemctl daemon-reload

# (Optional) Remove viewer files
sudo rm -rf /home/pi/viewer

# (Optional) Remove configuration
sudo rm /etc/adver.def
```

For cron method:
```bash
sudo crontab -e
# Delete the @reboot line
```

---

## Quick Reference Card

### Common Tasks

| Task | Command |
|------|---------|
| Start service | `sudo systemctl start adver-player` |
| Stop service | `sudo systemctl stop adver-player` |
| Restart service | `sudo systemctl restart adver-player` |
| Check status | `sudo systemctl status adver-player` |
| View logs | `sudo journalctl -u adver-player -f` |
| Enable auto-start | `sudo systemctl enable adver-player` |
| Disable auto-start | `sudo systemctl disable adver-player` |
| Test manually | `sudo /home/pi/viewer/video.sh` |

---

## Support

If you encounter issues:

1. Check logs: `sudo journalctl -u adver-player -n 100`
2. Test manually: `sudo /home/pi/viewer/video.sh`
3. Verify configuration: `cat /etc/adver.def`
4. Check permissions: `ls -l /home/pi/viewer/`
5. Review this guide's troubleshooting section
