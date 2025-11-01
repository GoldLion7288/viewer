#!/bin/bash
# ===========================================
# 🎬 Raspberry Pi Video Player Setup Script
# ===========================================
# Dependencies: PyQt5, OpenCV, Pillow, NumPy, ffpyplayer
# Audio/Video: ffpyplayer unified decoder for PERFECT synchronization

set -euo pipefail

echo "🔧 Step 1: Update system packages..."
sudo apt update

echo "📦 Step 2: Install Python 3, pip, and venv..."
sudo apt install -y python3 python3-pip python3-venv

echo ""
echo "🐍 Step 3: Creating virtual environment..."
python3 -m venv --system-site-packages venv
echo "✓ Virtual environment created at ./venv"
echo ""

echo "📚 Step 4: Installing system dependencies..."
echo "   → Installing PyQt5 system packages..."
sudo apt install -y python3-pyqt5 pyqt5-dev-tools

echo "   → Installing OpenCV system dependencies..."
sudo apt install -y libgl1-mesa-glx libglib2.0-0 \
                    libavcodec-extra libavformat-dev libswscale-dev

echo "   → Installing FFmpeg and SDL2 for synchronized audio/video playback..."
sudo apt install -y ffmpeg libavformat-dev libavcodec-dev libavdevice-dev \
                    libavutil-dev libswscale-dev libswresample-dev libavfilter-dev \
                    libsdl2-dev libsdl2-2.0-0 \
                    pulseaudio pulseaudio-utils alsa-utils

echo "   → Installing X11 libraries for Qt GUI..."
sudo apt install -y libxcb-xinerama0 libx11-xcb1 libxkbcommon-x11-0 libxcb-icccm4 \
                    libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
                    libxcb-shape0 libxcb-sync1 libxcb-xfixes0 libxrender1

echo "   → Installing Qt5 core libraries..."
sudo apt install -y libqt5gui5 libqt5core5a libqt5widgets5 libqt5opengl5 \
                    libqt5x11extras5 libqt5dbus5 libqt5network5

echo ""
echo "⚡ Step 5: Installing Python packages in virtual environment..."
source venv/bin/activate

echo "   → Upgrading pip..."
pip install --upgrade pip

echo "   → Installing requirements (PyQt5, OpenCV, Pillow, NumPy, ffpyplayer)..."
pip install -r requirements.txt

echo ""
echo "   → Verifying ffpyplayer installation..."
python3 -c "from ffpyplayer.player import MediaPlayer; print('✓ ffpyplayer is working')" || echo "⚠ ffpyplayer installation failed"

echo ""
echo "🔑 Step 6: Making scripts executable..."
chmod +x run.sh
chmod +x testrun.sh 2>/dev/null || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Installed Python packages:"
pip list | grep -E "PyQt5|opencv-python|Pillow|numpy|ffpyplayer"

echo ""
echo "🎬 Audio/Video Sync System:"
python3 -c "from ffpyplayer.player import MediaPlayer; print('  ✓ ffpyplayer: READY (unified A/V decoder)')" 2>/dev/null || echo "  ✗ ffpyplayer: NOT INSTALLED"
command -v ffmpeg >/dev/null 2>&1 && echo "  ✓ ffmpeg: $(ffmpeg -version | head -n1 | cut -d' ' -f3)" || echo "  ✗ ffmpeg not found"
pgrep -x pulseaudio >/dev/null 2>&1 && echo "  ✓ PulseAudio is running" || echo "  ⚠ PulseAudio not running"
echo ""
echo "📝 Next steps:"
echo "   1. Activate venv: source venv/bin/activate"
echo "   2. Run player: ./run.sh start test/background.jpg"
echo ""
echo "💡 Note: run.sh automatically uses the venv"
echo ""
