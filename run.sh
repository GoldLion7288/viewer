# adver.def Configuration Guide

## File Location
- **Development**: `D:\2025_10_31(video_test)\adver.def`
- **Production (Raspberry Pi)**: `/etc/adver.def`

## Configuration Format

The `adver.def` file contains configuration parameters read by `video.sh`. Each line represents a specific configuration value:

```
Line 1  (index 0): SERVICE_NAME     - Service identifier (e.g., "adver")
Line 2  (index 1): VERSION/ID       - Version or region code (e.g., "001")
Line 3  (index 2): REGION/ID        - Additional identifier (e.g., "002")
Line 4  (index 3): DOWNLOAD_URL     - URL for downloading content
Line 5  (index 4): EXEC_DIR         - Base execution directory (e.g., "/home/pi/")
Line 6  (index 5): DATA_DIR         - Data storage directory (e.g., "/home/pi/data/")
Line 7  (index 6): DOWNLOAD_DIR     - Download directory (e.g., "/home/pi/download/")
Line 8  (index 7): TRIGGER          - Trigger file path (e.g., "/home/pi/download/trigger")
Line 9  (index 8): CRON             - Cron permission file (e.g., "/home/pi/cron")
Line 10 (index 9): USERNAME         - System username (e.g., "pi")
```

## Current Configuration

```
adver
001
002
https://uninyavision.sakura.ne.jp/adver/
/home/pi/
/home/pi/data/
/home/pi/download/
/home/pi/download/trigger
/home/pi/cron
pi
```

## How video.sh Uses This File

```bash
readarray data < "/etc/adver.def"

SERVICE_NAME=${data[0]//$'\n'/}      # Line 1: adver
EXEC_DIR=${data[4]//$'\n'/}          # Line 5: /home/pi/
DATA_DIR=${data[5]//$'\n'/}          # Line 6: /home/pi/data/
DOWNLOAD_DIR=${data[6]//$'\n'/}      # Line 7: /home/pi/download/
TRIGGER=${data[7]//$'\n'/}           # Line 8: /home/pi/download/trigger
CRON=${data[8]//$'\n'/}              # Line 9: /home/pi/cron
```

Then executes:
```bash
${EXEC_DIR}viewer/run.sh start ${EXEC_DIR}background.jpg
```

Which translates to:
```bash
/home/pi/viewer/run.sh start /home/pi/background.jpg
```

## Directory Structure Expected on Raspberry Pi

```
/home/pi/
├── viewer/
│   ├── run.sh           # Main launcher script
│   ├── run.py           # Python video player
│   └── venv/            # Python virtual environment (optional)
├── data/
│   ├── test1.mp4        # Video files
│   ├── test2.mp4
│   └── ...
├── download/
│   └── trigger          # Trigger file for updates
├── cron                 # Cron permission file
└── background.jpg       # Background image

/etc/
└── adver.def           # This configuration file
```

## Installation on Raspberry Pi

1. Copy `adver.def` to `/etc/adver.def`:
   ```bash
   sudo cp adver.def /etc/adver.def
   sudo chmod 644 /etc/adver.def
   ```

2. Create required directories:
   ```bash
   mkdir -p /home/pi/viewer
   mkdir -p /home/pi/data
   mkdir -p /home/pi/download
   ```

3. Deploy the viewer system to `/home/pi/viewer/`

4. Place a background image at `/home/pi/background.jpg`

5. Run video.sh (typically from cron or systemd as root):
   ```bash
   sudo bash video.sh
   ```

## Notes

- All paths must end without trailing slashes except where explicitly shown
- The file must use Unix line endings (LF, not CRLF)
- Each line must contain exactly one value
- Empty lines at the end are acceptable but not required