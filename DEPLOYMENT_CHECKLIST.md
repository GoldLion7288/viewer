# Deployment Checklist for Raspberry Pi

Use this checklist before deploying to production.

## Pre-Deployment Checklist

### 1. Files Ready ✓
- [ ] `run.sh` - Main launcher script
- [ ] `run.py` - Python video player
- [ ] `video.sh` - Boot startup script
- [ ] `adver.def` - Configuration file
- [ ] `adver-player.service` - Systemd service file
- [ ] `install-autostart.sh` - Installation script
- [ ] `background.jpg` - Background image
- [ ] Video files for `/home/pi/data/`

### 2. Configuration Check ✓
- [ ] Edit `adver.def` if paths differ from defaults
- [ ] Verify line endings are Unix (LF) not Windows (CRLF)
- [ ] Background image path matches in configuration

### 3. Test Before Deploy ✓
On your Raspberry Pi, test manually first:

```bash
# Test 1: Run the player directly
cd /home/pi/viewer
./run.sh start /home/pi/background.jpg

# Test 2: Play a video
./run.sh play /home/pi/data/test1.mp4 10

# Test 3: Exit cleanly
./run.sh exit
```

If these work, auto-start will work too.

## Deployment Steps

### Step 1: Transfer Files
```bash
# On your computer
scp -r * pi@raspberrypi:~/video-player-install/
```
- [ ] All files transferred successfully

### Step 2: Install
```bash
# On Raspberry Pi
cd ~/video-player-install
chmod +x install-autostart.sh
sudo bash install-autostart.sh
```
- [ ] Installation completed without errors
- [ ] Service enabled successfully

### Step 3: Verify Installation
```bash
# Check service status
sudo systemctl status adver-player

# Check if files exist
ls -l /home/pi/viewer/
ls -l /etc/adver.def
ls -l /etc/systemd/system/adver-player.service
```
- [ ] All files in correct locations
- [ ] Service shows as "enabled"

### Step 4: Test Service
```bash
# Start service manually
sudo systemctl start adver-player

# Wait 5 seconds, then check
sudo systemctl status adver-player
ps aux | grep run.py
```
- [ ] Service started successfully
- [ ] Video player GUI visible on screen
- [ ] No errors in status output

### Step 5: Test Auto-Start
```bash
# Reboot
sudo reboot

# After reboot (via SSH):
sudo systemctl status adver-player
ps aux | grep run.py
```
- [ ] Service started automatically after reboot
- [ ] Video player visible on screen
- [ ] Background image displayed

## Post-Deployment Verification

### System Health ✓
```bash
# Check logs
sudo journalctl -u adver-player -n 50

# Check resource usage
top -n 1 | grep python3
```
- [ ] No error messages in logs
- [ ] CPU usage acceptable (< 80%)
- [ ] Memory usage acceptable

### Functional Tests ✓
From another computer or SSH:

```bash
# Test play command
ssh pi@raspberrypi "cd /home/pi/viewer && ./run.sh play /home/pi/data/test1.mp4 10"
```
- [ ] Video plays correctly
- [ ] Smooth transitions
- [ ] No screen tearing or artifacts

### Long-term Stability ✓
- [ ] Leave running for 1 hour - check stability
- [ ] Test after power loss/reboot
- [ ] Verify service restarts on failure

## Production Readiness

### Security ✓
- [ ] Change default passwords (if applicable)
- [ ] Update system: `sudo apt update && sudo apt upgrade`
- [ ] Disable SSH if not needed: `sudo systemctl disable ssh`

### Backup ✓
- [ ] Backup `/etc/adver.def`
- [ ] Backup `/home/pi/viewer/` directory
- [ ] Document any custom changes

### Documentation ✓
- [ ] Note video file paths in use
- [ ] Record configuration changes
- [ ] Document playlist structure
- [ ] Share credentials with team (if needed)

## Maintenance Schedule

### Weekly
- [ ] Check logs: `sudo journalctl -u adver-player -n 100`
- [ ] Verify service running: `sudo systemctl status adver-player`

### Monthly
- [ ] Update video content
- [ ] Check disk space: `df -h`
- [ ] Review system updates: `sudo apt update`

### Quarterly
- [ ] Full system update: `sudo apt update && sudo apt upgrade`
- [ ] Backup configuration
- [ ] Test recovery procedure

## Emergency Procedures

### If service fails:
```bash
# Check logs
sudo journalctl -u adver-player -n 100

# Restart service
sudo systemctl restart adver-player

# If still failing, start manually
sudo /home/pi/viewer/video.sh
```

### If screen freezes:
```bash
# Via SSH
sudo systemctl restart adver-player

# Or kill and restart
pkill -f run.py
sudo systemctl start adver-player
```

### Recovery from backup:
```bash
# Stop service
sudo systemctl stop adver-player

# Restore files
sudo cp backup/adver.def /etc/
sudo cp -r backup/viewer/* /home/pi/viewer/

# Restart
sudo systemctl start adver-player
```

## Support Contacts

| Issue | Contact | Command |
|-------|---------|---------|
| Service not starting | Check logs | `sudo journalctl -u adver-player -f` |
| Config issues | Review settings | `cat /etc/adver.def` |
| Video playback | Test manually | `./run.sh play /path/to/video.mp4 10` |

## Sign-off

- [ ] All checklist items completed
- [ ] System tested and verified
- [ ] Documentation updated
- [ ] Team notified of deployment

**Deployed by:** _____________
**Date:** _____________
**Raspberry Pi ID:** _____________
**Location:** _____________

---

**Notes:**
