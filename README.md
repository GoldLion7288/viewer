# Raspberry Pi Advertisement Video Player

Professional-grade video player system for Raspberry Pi with auto-start on boot capability.

## 🎯 Features

- ✅ **Auto-start on boot** - Systemd or cron-based
- ✅ **Smooth transitions** - 150ms fade between media
- ✅ **High-quality playback** - LANCZOS4 interpolation
- ✅ **Full-screen display** - Optimized scaling for all content
- ✅ **IPC control** - Socket-based remote commands
- ✅ **Background image** - Displays when idle
- ✅ **Hardware acceleration** - Enabled for best performance
- ✅ **Headless operation** - Runs without user login

## 📦 What's Included

```
.
├── run.py                      # Main Python video player
├── run.sh                      # Shell launcher script
├── video.sh                    # Boot startup script
├── testrun.sh                  # Test script example
├── adver.def                   # Configuration file
├── adver-player.service        # Systemd service file
├── install-autostart.sh        # Automated installer (systemd)
├── install-cron.sh             # Automated installer (cron)
├── setup.sh                    # Development setup
├── QUICKSTART.md               # Quick installation guide
├── AUTOSTART_SETUP.md          # Detailed setup guide
├── ADVER_CONFIG.md             # Configuration reference
├── DEPLOYMENT_CHECKLIST.md     # Production deployment guide
└── README.md                   # This file
```

## 🚀 Quick Start

### 1. Install on Raspberry Pi

**Method 1: Automated (Recommended)**
```bash
# Copy files to Pi
scp -r * pi@raspberrypi:~/video-install/

# Run installer
ssh pi@raspberrypi
cd ~/video-install
chmod +x install-autostart.sh
sudo bash install-autostart.sh
```

**Method 2: Manual**
See [QUICKSTART.md](QUICKSTART.md) for step-by-step instructions.

### 2. Reboot
```bash
sudo reboot
```

That's it! The video player will start automatically.

## 🎮 Usage

### Command Line Interface

```bash
# Start player with background image
./run.sh start /home/pi/background.jpg

# Play a video for 10 seconds
./run.sh play /home/pi/data/video.mp4 10

# Stop playback (return to background)
./run.sh stop

# Exit player
./run.sh exit
```

### Service Management

```bash
# Control the auto-start service
sudo systemctl start adver-player    # Start now
sudo systemctl stop adver-player     # Stop service
sudo systemctl restart adver-player  # Restart
sudo systemctl status adver-player   # Check status

# View logs
sudo journalctl -u adver-player -f   # Live logs
sudo journalctl -u adver-player -n 50 # Last 50 lines
```

## 📝 Configuration

Configuration is stored in `/etc/adver.def`:

```
Line 1:  adver                         # Service name
Line 2:  001                           # Version/ID
Line 3:  002                           # Region/ID
Line 4:  https://download.url/        # Download URL
Line 5:  /home/pi/                     # Base directory (EXEC_DIR)
Line 6:  /home/pi/data/                # Data directory
Line 7:  /home/pi/download/            # Download directory
Line 8:  /home/pi/download/trigger     # Trigger file
Line 9:  /home/pi/cron                 # Cron file
Line 10: pi                            # Username
```

See [ADVER_CONFIG.md](ADVER_CONFIG.md) for detailed configuration guide.

## 📁 Directory Structure

```
/home/pi/
├── viewer/
│   ├── run.sh           # Main launcher
│   ├── run.py           # Python player
│   └── video.sh         # Startup script
├── data/
│   ├── video1.mp4       # Your video files
│   ├── video2.mp4
│   └── ...
├── download/            # Download directory
└── background.jpg       # Background image

/etc/
├── adver.def            # Configuration
└── systemd/system/
    └── adver-player.service  # Auto-start service
```

## 🔧 Requirements

### Hardware
- Raspberry Pi 3/4/5 (or compatible)
- Display connected via HDMI
- 2GB+ RAM recommended
- 4GB+ storage

### Software
- Raspberry Pi OS (Debian-based)
- Python 3.7+
- Desktop environment (X11/Wayland)

### Python Packages
- PyQt5
- OpenCV (cv2)
- Pillow (PIL)
- NumPy

**Install dependencies:**
```bash
sudo apt update
sudo apt install python3-pyqt5 python3-opencv python3-numpy python3-pil
```

## 🎬 Features in Detail

### Video Playback
- Supports: MP4, AVI, MKV, MOV, and more
- Hardware acceleration enabled
- LANCZOS4 interpolation for scaling
- Maintains aspect ratio
- Configurable playback duration

### Image Display
- Supports: JPG, PNG, BMP, GIF, WebP
- High-quality LANCZOS resampling
- Background fills entire screen
- Regular images show complete content

### Transitions
- Smooth 150ms fade effects
- Prevents jarring content switches
- Configurable easing curves

### IPC Control
- Unix domain socket communication
- JSON-based commands
- Non-blocking operation
- Single-instance management

## 🐛 Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u adver-player -n 100

# Test manually
sudo /home/pi/viewer/video.sh
```

### Screen stays black
```bash
# Check DISPLAY variable
echo $DISPLAY

# Test as pi user
export DISPLAY=:0
cd /home/pi/viewer
./run.sh start /home/pi/background.jpg
```

### Python errors
```bash
# Install missing packages
sudo apt install python3-pyqt5 python3-opencv python3-numpy python3-pil
```

See [AUTOSTART_SETUP.md](AUTOSTART_SETUP.md#troubleshooting) for more help.

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](QUICKSTART.md) | Fast installation guide |
| [AUTOSTART_SETUP.md](AUTOSTART_SETUP.md) | Complete setup guide |
| [ADVER_CONFIG.md](ADVER_CONFIG.md) | Configuration reference |
| [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) | Production deployment |

## 🔒 Security Notes

- Service runs as root for GUI access
- IPC socket limited to local connections
- No network services exposed
- Configure firewall if network control needed

## 📊 Performance

**Typical Resource Usage:**
- CPU: 15-30% (during video playback)
- RAM: 200-400 MB
- Disk I/O: Minimal
- Network: None (local files only)

## 🛠️ Development

### Local Testing
```bash
# Clone repository
git clone <your-repo-url>
cd video-player

# Run setup
bash setup.sh

# Test locally
./run.sh start background.jpg
./run.sh play test.mp4 10
```

### Code Structure
- `run.py` - Main player (PyQt5 + OpenCV)
- `run.sh` - Shell wrapper (handles environment)
- `video.sh` - Boot script (reads config)
- `adver.def` - Config file (10 lines)

## 🔄 Updates

### Update Player
```bash
# Stop service
sudo systemctl stop adver-player

# Update files
cd ~/video-install
git pull  # or copy new files

# Restart
sudo systemctl start adver-player
```

### Update Configuration
```bash
# Edit config
sudo nano /etc/adver.def

# Restart to apply
sudo systemctl restart adver-player
```

## 🗑️ Uninstall

```bash
# Stop and disable
sudo systemctl stop adver-player
sudo systemctl disable adver-player

# Remove service
sudo rm /etc/systemd/system/adver-player.service
sudo systemctl daemon-reload

# Remove files (optional)
sudo rm -rf /home/pi/viewer
sudo rm /etc/adver.def
```

## 📞 Support

**Common Issues:**
- Service fails: Check `sudo journalctl -u adver-player`
- Black screen: Verify DISPLAY and X11 running
- Video won't play: Check file format and permissions

**Logs Location:**
- System: `sudo journalctl -u adver-player`
- Player: `/tmp/video_player.log`
- Cron: `/tmp/video_player_cron.log`

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional video formats
- Network streaming support
- Web-based control interface
- Playlist management
- Multi-screen support

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

Built for Raspberry Pi-based digital signage and advertisement displays.

---

**Version:** 1.0
**Last Updated:** 2025
**Platform:** Raspberry Pi OS (Debian-based)
**Python:** 3.7+
