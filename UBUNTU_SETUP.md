# Ubuntu Environment Setup Guide

## Complete Installation Instructions for Advertisement Player

### 1. System Requirements

**Minimum Requirements:**
- Ubuntu 20.04 LTS or newer (also works on Raspberry Pi OS)
- Python 3.8 or higher
- X11 display server (for GUI)
- 2GB RAM minimum (4GB recommended)

---

### 2. Install System Dependencies

First, update your system and install required packages:

```bash
# Update package list
sudo apt update

# Install Python 3 and pip
sudo apt install -y python3 python3-pip python3-venv

# Install Qt5 system libraries (required for PyQt5)
sudo apt install -y python3-pyqt5 python3-pyqt5.qtmultimedia

# Install OpenCV dependencies
sudo apt install -y libgl1-mesa-glx libglib2.0-0

# Install video codec libraries for better video support
sudo apt install -y libavcodec-extra libavformat-dev libswscale-dev

# Optional: Install additional codecs for various video formats
sudo apt install -y ubuntu-restricted-extras
```

---

### 3. Create Python Virtual Environment (venv)

**What is venv?**
A virtual environment is an isolated Python environment that:
- Keeps project dependencies separate from system Python
- Prevents version conflicts between projects
- Allows different projects to use different library versions
- Makes deployment easier and more reliable

**Create and activate venv:**

```bash
# Navigate to your project directory
cd ~/Downloads/Viewer

# Create virtual environment named 'venv'
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Your prompt should now show (venv) at the beginning
# Example: (venv) user@hostname:~/Downloads/Viewer$
```

---

### 4. Install Python Dependencies

With the virtual environment activated:

```bash
# Upgrade pip to latest version
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt

# Verify installation
pip list
```

**Expected output should include:**
```
PyQt5           5.15.9
opencv-python   4.8.0
Pillow          10.0.0
numpy           1.24.0
```

---

### 5. Verify Installation

Test if everything is installed correctly:

```bash
# Test Python imports
python3 -c "import PyQt5; import cv2; import PIL; import numpy; print('All imports successful!')"

# Check OpenCV build info (should show GUI support)
python3 -c "import cv2; print(cv2.getBuildInformation())" | grep -i gui
```

---

### 6. Setup Test Files

```bash
# Create test directory if it doesn't exist
mkdir -p test

# Add your test media files
# - test/background.jpg  (background image)
# - test/1.mp4          (video file)
# - test/2.jpg          (image file)
# - test/3.jpg          (image file)
```

---

### 7. Make Scripts Executable

```bash
# Make run.sh executable
chmod +x run.sh

# Make run.py executable (optional)
chmod +x run.py
```

---

### 8. Run the Application

**Start the player:**
```bash
# Make sure venv is activated
source venv/bin/activate

# Start with background
./run.sh start ~/Downloads/Viewer/test/background.jpg 1

# Play video
./run.sh play ~/Downloads/Viewer/test/1.mp4 10

# Play images
./run.sh play ~/Downloads/Viewer/test/3.jpg 2
./run.sh play ~/Downloads/Viewer/test/2.jpg 2

# Exit
./run.sh exit
```

---

### 9. Autostart on Boot (Optional)

**For Raspberry Pi or Kiosk Mode:**

Create systemd service:

```bash
sudo nano /etc/systemd/system/ad-player.service
```

Add this content:

```ini
[Unit]
Description=Advertisement Player
After=graphical.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
WorkingDirectory=/home/pi/Downloads/Viewer
ExecStart=/home/pi/Downloads/Viewer/venv/bin/python3 /home/pi/Downloads/Viewer/run.py --start /home/pi/Downloads/Viewer/test/background.jpg --single-instance
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=graphical.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ad-player.service
sudo systemctl start ad-player.service

# Check status
sudo systemctl status ad-player.service
```

---

### 10. Virtual Environment Management

**Deactivate venv:**
```bash
deactivate
```

**Reactivate venv:**
```bash
source venv/bin/activate
```

**Delete venv (if needed):**
```bash
deactivate
rm -rf venv
```

**Recreate venv:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 11. Troubleshooting

**Issue: Qt platform plugin error**
```bash
# Solution: Unset conflicting environment variables
export QT_QPA_PLATFORM_PLUGIN_PATH=""
unset QT_PLUGIN_PATH
```

**Issue: Display not found**
```bash
# Solution: Set DISPLAY variable
export DISPLAY=:0
```

**Issue: Permission denied on /tmp/video_player_ipc.sock**
```bash
# Solution: Remove old socket file
rm -f /tmp/video_player_ipc.sock
```

**Issue: Video codec not supported**
```bash
# Solution: Install additional codecs
sudo apt install -y ubuntu-restricted-extras ffmpeg
```

**Issue: ImportError for cv2**
```bash
# Solution: Reinstall opencv-python (not headless)
pip uninstall opencv-python-headless opencv-python
pip install opencv-python>=4.8.0
```

---

### 12. Performance Optimization

**For Raspberry Pi 4:**

```bash
# Enable OpenGL acceleration
sudo raspi-config
# Navigate to: Advanced Options > GL Driver > GL (Full KMS)

# Increase GPU memory
sudo nano /boot/config.txt
# Add: gpu_mem=256

# Reboot
sudo reboot
```

**For Ubuntu Desktop:**

```bash
# Install hardware acceleration drivers
sudo ubuntu-drivers autoinstall

# Check if GPU is being used
glxinfo | grep "direct rendering"
```

---

### 13. Production Deployment Checklist

- [ ] Virtual environment created and activated
- [ ] All dependencies installed from requirements.txt
- [ ] Test files present in test/ directory
- [ ] run.sh is executable (chmod +x)
- [ ] DISPLAY variable is set correctly
- [ ] Qt platform plugins working
- [ ] Video playback tested successfully
- [ ] Sequential playback working without freezing
- [ ] Systemd service configured (if autostart needed)
- [ ] Log files location defined (/tmp/video_player.log)

---

### 14. Quick Reference Commands

```bash
# One-line setup (run once)
sudo apt update && sudo apt install -y python3 python3-pip python3-venv python3-pyqt5 libgl1-mesa-glx && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Daily use (activate venv and run)
cd ~/Downloads/Viewer && source venv/bin/activate && ./run.sh start test/background.jpg 1

# Check if player is running
ps aux | grep "python.*run.py"

# View logs
tail -f /tmp/video_player.log

# Kill all instances
pkill -f "python.*run.py"
```

---

## Summary

The virtual environment ensures your advertisement player runs in an isolated, controlled environment with exactly the right versions of all dependencies. This prevents conflicts with other Python projects and makes your deployment reliable and reproducible.

**Key Benefits:**
- ✅ Isolated dependencies
- ✅ Easy to replicate on other machines
- ✅ No conflicts with system Python
- ✅ Simple to update or rollback
- ✅ Professional deployment standard
