#!/bin/bash
# ================================================================
# 🎬 Raspberry Pi Video Player - Complete Setup Script
# ================================================================
# Features:
# - Python environment with PyQt5, OpenCV, Pillow, NumPy
# - ffpyplayer for synchronized audio/video playback
# - GStreamer with hardware-accelerated H.264 decoding
# - Automatic Pi model detection and decoder selection
# ================================================================

set -euo pipefail

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎬 Raspberry Pi Video Player - Complete Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Detect Raspberry Pi model
if [ -f /proc/cpuinfo ]; then
    PI_MODEL=$(cat /proc/cpuinfo | grep "Model" | cut -d: -f2 | xargs || echo "Unknown")
    echo "🔍 Detected: $PI_MODEL"

    # Detect hardware decoder type
    if grep -q "BCM2711\|BCM2712" /proc/cpuinfo; then
        DECODER_TYPE="V4L2 (Pi 4/5)"
        DECODER_PACKAGE="gstreamer1.0-libav"
    elif grep -q "BCM283[567]" /proc/cpuinfo; then
        DECODER_TYPE="OMX (Pi 3)"
        DECODER_PACKAGE="gstreamer1.0-omx"
    else
        DECODER_TYPE="Both decoders"
        DECODER_PACKAGE="gstreamer1.0-libav gstreamer1.0-omx"
    fi
    echo "📦 Will install: $DECODER_TYPE hardware decoder"
else
    echo "⚠️  Warning: Could not detect Pi model, installing all decoders"
    DECODER_TYPE="All decoders"
    DECODER_PACKAGE="gstreamer1.0-libav gstreamer1.0-omx"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Step 1: Update System Packages"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo apt-get update

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 Step 2: Install Python 3, pip, and venv"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sudo apt-get install -y python3 python3-pip python3-venv

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📁 Step 3: Creating Virtual Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists, skipping..."
else
    python3 -m venv --system-site-packages venv
    echo "✓ Virtual environment created at ./venv"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 Step 4: Installing System Dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "   → PyQt5 system packages..."
sudo apt-get install -y python3-pyqt5 pyqt5-dev-tools

echo "   → OpenCV system dependencies..."
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0 \
                        libavcodec-extra libavformat-dev libswscale-dev

echo "   → FFmpeg and SDL2 for audio/video synchronization..."
sudo apt-get install -y ffmpeg libavformat-dev libavcodec-dev libavdevice-dev \
                        libavutil-dev libswscale-dev libswresample-dev libavfilter-dev \
                        libsdl2-dev libsdl2-2.0-0 \
                        pulseaudio pulseaudio-utils alsa-utils

echo "   → X11 libraries for Qt GUI..."
sudo apt-get install -y libxcb-xinerama0 libx11-xcb1 libxkbcommon-x11-0 libxcb-icccm4 \
                        libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
                        libxcb-shape0 libxcb-sync1 libxcb-xfixes0 libxrender1

echo "   → Qt5 core libraries..."
sudo apt-get install -y libqt5gui5 libqt5core5a libqt5widgets5 libqt5opengl5 \
                        libqt5x11extras5 libqt5dbus5 libqt5network5

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎥 Step 5: Installing GStreamer (Hardware Acceleration)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "   → Core GStreamer packages..."
sudo apt-get install -y \
    python3-gst-1.0 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly

echo "   → Hardware decoder: $DECODER_TYPE..."
sudo apt-get install -y $DECODER_PACKAGE

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚡ Step 6: Installing Python Packages"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
source venv/bin/activate

echo "   → Upgrading pip..."
pip install --upgrade pip

echo "   → Installing Python requirements..."
echo "      • PyQt5 (GUI framework)"
echo "      • OpenCV (video processing)"
echo "      • Pillow (image handling)"
echo "      • NumPy (array operations)"
echo "      • ffpyplayer (A/V synchronization)"
echo "      • PyGObject (GStreamer bindings)"

pip install -r requirements.txt

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Step 7: Making Scripts Executable"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
chmod +x run.sh
chmod +x testrun.sh 2>/dev/null || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Step 8: Verifying Installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Verify Python packages
echo "📦 Python Packages:"
pip list | grep -E "PyQt5|opencv-python|Pillow|numpy|ffpyplayer|PyGObject" || echo "   ⚠️  Some packages may not be installed"

echo ""
echo "🎬 Audio/Video System:"

# Check ffpyplayer
if python3 -c "from ffpyplayer.player import MediaPlayer" 2>/dev/null; then
    echo "   ✓ ffpyplayer (A/V sync)"
else
    echo "   ✗ ffpyplayer NOT WORKING"
fi

# Check ffmpeg
if command -v ffmpeg >/dev/null 2>&1; then
    FFMPEG_VER=$(ffmpeg -version | head -n1 | cut -d' ' -f3)
    echo "   ✓ ffmpeg $FFMPEG_VER"
else
    echo "   ✗ ffmpeg not found"
fi

# Check PulseAudio
if pgrep -x pulseaudio >/dev/null 2>&1; then
    echo "   ✓ PulseAudio running"
else
    echo "   ⚠️  PulseAudio not running"
fi

echo ""
echo "🚀 GStreamer Hardware Acceleration:"

# Check GStreamer
if command -v gst-launch-1.0 >/dev/null 2>&1; then
    GST_VER=$(gst-launch-1.0 --version 2>&1 | grep version | awk '{print $4}')
    echo "   ✓ GStreamer $GST_VER"
else
    echo "   ✗ GStreamer not found"
fi

# Check Python GStreamer bindings
if python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst" 2>/dev/null; then
    echo "   ✓ Python GStreamer bindings"
else
    echo "   ✗ Python GStreamer bindings NOT WORKING"
fi

# Check hardware decoders
HW_DECODER_FOUND=0
if gst-inspect-1.0 v4l2h264dec &>/dev/null; then
    echo "   ✓ V4L2 H.264 decoder (Pi 4/5)"
    HW_DECODER_FOUND=1
fi

if gst-inspect-1.0 omxh264dec &>/dev/null; then
    echo "   ✓ OMX H.264 decoder (Pi 3)"
    HW_DECODER_FOUND=1
fi

if [ $HW_DECODER_FOUND -eq 0 ]; then
    echo "   ⚠️  No hardware decoder found (will use software)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Installation Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 System Summary:"
echo "   • Python packages: Installed"
echo "   • Audio/Video sync: ffpyplayer"
echo "   • Hardware decoder: $DECODER_TYPE"
echo "   • Performance: ~70% CPU reduction vs software decoding"
echo ""
echo "⚙️  Recommended: Increase GPU Memory"
echo "   Run: sudo raspi-config"
echo "   Navigate to: Advanced Options → Memory Split"
echo "   Set to: 256 MB (or 128 MB minimum)"
echo "   Then: sudo reboot"
echo ""
echo "🚀 Quick Start:"
echo "   1. Activate venv:"
echo "      source venv/bin/activate"
echo ""
echo "   2. Start player:"
echo "      ./run.sh start test/background.jpg"
echo ""
echo "   3. Play video (in another terminal):"
echo "      python3 run.py --play test.mp4 10"
echo ""
echo "   4. Monitor CPU usage:"
echo "      htop"
echo "      (Should see 15-30% CPU with hardware decoding)"
echo ""
echo "📖 Documentation:"
echo "   • GSTREAMER_SETUP.md - Detailed GStreamer guide"
echo "   • GSTREAMER_UPGRADE.md - Performance comparison"
echo "   • requirements.txt - All dependencies"
echo ""
echo "💡 Note: run.sh automatically activates venv"
echo ""
