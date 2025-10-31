#!/bin/bash
# ===========================================
# 🎬 Raspberry Pi Video Player Setup Script
# ===========================================
# Dependencies: PyQt5, OpenCV, Pillow, NumPy
# No GStreamer needed - using OpenCV for video

set -euo pipefail

echo "🔧 Step 1: Update system packages..."
sudo apt update

echo "📦 Step 2: Install Python 3 and pip..."
sudo apt install -y python3 python3-pip python3-venv

echo "🖥 Step 3: Install PyQt5 system packages..."
sudo apt install -y python3-pyqt5 pyqt5-dev-tools

echo "🎥 Step 4: Install OpenCV system dependencies..."
# Core OpenCV dependencies for video playback
sudo apt install -y libgl1-mesa-glx libglib2.0-0

# Video codec libraries for OpenCV
sudo apt install -y libavcodec-extra libavformat-dev libswscale-dev

echo "🪟 Step 5: Install X11 libraries for Qt GUI..."
sudo apt install -y libxcb-xinerama0 libx11-xcb1 libxkbcommon-x11-0 libxcb-icccm4 \
                    libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
                    libxcb-shape0 libxcb-sync1 libxcb-xfixes0 libxrender1

echo "📚 Step 6: Install Qt5 core libraries..."
sudo apt install -y libqt5gui5 libqt5core5a libqt5widgets5 libqt5opengl5 \
                    libqt5x11extras5 libqt5dbus5 libqt5network5

echo "🐍 Step 7: Create Python virtual environment..."
python3 -m venv --system-site-packages venv

echo "⚡ Step 8: Activate venv and install Python packages..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "🔑 Step 9: Make scripts executable..."
chmod +x run.sh
chmod +x testrun.sh 2>/dev/null || true

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Activate venv: source venv/bin/activate"
echo "   2. Run player: ./run.sh start test/background.jpg"
echo ""
