# Quick Start: Auto-Start on Raspberry Pi Boot

## 🚀 Fastest Method (Recommended)

### Step 1: Copy files to Raspberry Pi

On your computer:
```bash
scp -r * pi@raspberrypi:~/video-player-install/
```

### Step 2: Run installation script

On Raspberry Pi (via SSH or terminal):
```bash
cd ~/video-player-install
chmod +x install-autostart.sh
sudo bash install-autostart.sh
```

### Step 3: Reboot

```bash
sudo reboot
```

**Done!** The video player will start automatically after boot.

---

## ✅ Verify It's Working

After reboot, check:
```bash
# Check if service is running
sudo systemctl status adver-player

# Check if player process is running
ps aux | grep run.py

# View logs
sudo journalctl -u adver-player -n 50
```

---

## 🛠️ Common Commands

```bash
# Start service
sudo systemctl start adver-player

# Stop service
sudo systemctl stop adver-player

# Restart service
sudo systemctl restart adver-player

# View live logs
sudo journalctl -u adver-player -f

# Disable auto-start (won't start on boot)
sudo systemctl disable adver-player

# Re-enable auto-start
sudo systemctl enable adver-player
```

---

## 📁 What Gets Installed

```
/home/pi/
├── viewer/
│   ├── run.sh       ← Main launcher
│   ├── run.py       ← Video player
│   └── video.sh     ← Boot startup script
├── data/            ← Put your video files here
├── download/        ← Download directory
└── background.jpg   ← Background image

/etc/
├── adver.def        ← Configuration file
└── systemd/system/
    └── adver-player.service  ← Auto-start service
```

---

## 🔧 Manual Installation (If Script Fails)

<details>
<summary>Click to expand manual steps</summary>

### 1. Create directories:
```bash
sudo mkdir -p /home/pi/viewer /home/pi/data /home/pi/download
```

### 2. Copy files:
```bash
sudo cp run.sh run.py video.sh /home/pi/viewer/
sudo chmod +x /home/pi/viewer/*.sh
sudo cp adver.def /etc/adver.def
cp background.jpg /home/pi/background.jpg
```

### 3. Install service:
```bash
sudo cp adver-player.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable adver-player
```

### 4. Start service:
```bash
sudo systemctl start adver-player
```

</details>

---

## 🐛 Troubleshooting

### Video player doesn't start?

1. **Check logs:**
   ```bash
   sudo journalctl -u adver-player -n 100
   ```

2. **Test manually:**
   ```bash
   sudo /home/pi/viewer/video.sh
   ```

3. **Check if files exist:**
   ```bash
   ls -l /home/pi/viewer/
   ls -l /etc/adver.def
   ```

### Screen stays black?

1. **Check if DISPLAY is set:**
   ```bash
   echo $DISPLAY
   ```

2. **Try running as pi user:**
   ```bash
   export DISPLAY=:0
   cd /home/pi/viewer
   ./run.sh start /home/pi/background.jpg
   ```

### Need Python packages?

```bash
sudo apt update
sudo apt install python3-pyqt5 python3-opencv python3-numpy python3-pil
```

---

## 📚 More Information

- **Full documentation:** See `AUTOSTART_SETUP.md`
- **Configuration guide:** See `ADVER_CONFIG.md`
- **Alternative cron method:** Run `install-cron.sh`

---

## 🗑️ Uninstall

To remove auto-start:

```bash
sudo systemctl stop adver-player
sudo systemctl disable adver-player
sudo rm /etc/systemd/system/adver-player.service
sudo systemctl daemon-reload
```

---

## 📞 Quick Help

| Problem | Solution |
|---------|----------|
| Service won't start | `sudo journalctl -u adver-player -n 100` |
| Need to restart | `sudo systemctl restart adver-player` |
| Want to disable | `sudo systemctl disable adver-player` |
| Check if running | `sudo systemctl status adver-player` |
| View live logs | `sudo journalctl -u adver-player -f` |

---

**That's it!** Your video player will now start automatically every time the Raspberry Pi boots. 🎉
