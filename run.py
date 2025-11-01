import sys
import os
import socket
import json
import argparse
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QGraphicsOpacityEffect
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QSocketNotifier
from PyQt5.QtGui import QPixmap, QImage
import cv2
from PIL import Image
import numpy as np
import threading


# ===================================
# RASPBERRY PI PERFORMANCE OPTIMIZATION
# ===================================
# Set to True for Raspberry Pi (enables all optimizations)
RASPBERRY_PI_MODE = True

# Performance settings for Raspberry Pi
if RASPBERRY_PI_MODE:
    # Use INTER_AREA for better quality with good performance (better than NEAREST)
    # INTER_AREA is excellent for downscaling and maintains quality
    FRAME_INTERPOLATION = cv2.INTER_AREA  # Good quality + fast
    # Sleep between frames - 0 for maximum performance
    PLAYBACK_SLEEP = 0.0001  # Minimal sleep (100 microseconds)
    # Target FPS for smooth playback (used in fallback path)
    TARGET_FPS = 30  # Smooth framerate for Pi
    # Scaling behavior: 'fit' = show entire video (QQ Player style - no crop)
    SCALING_MODE = 'fit'  # Show ALL video area, add black bars if needed
else:
    # Desktop mode: highest quality
    FRAME_INTERPOLATION = cv2.INTER_LANCZOS4  # Highest quality
    PLAYBACK_SLEEP = 0.001  # 1ms sleep
    TARGET_FPS = 30  # Full framerate
    SCALING_MODE = 'fit'  # Fit screen with black bars

# Enable OpenCV optimizations
try:
    cv2.setUseOptimized(True)
    if RASPBERRY_PI_MODE:
        # Fewer threads can reduce scheduling jitter on small CPUs
        cv2.setNumThreads(1)
except Exception:
    pass

# Audio/Video synchronization using ffpyplayer (unified decoder)
try:
    from ffpyplayer.player import MediaPlayer
    SYNC_SUPPORT = True
    print("ffpyplayer loaded - synchronized A/V playback enabled")
    if RASPBERRY_PI_MODE:
        print("Raspberry Pi optimization mode: ENABLED")
except ImportError:
    SYNC_SUPPORT = False

# IPC Configuration
IPC_SOCKET_PATH = '/tmp/video_player_ipc.sock'
IPC_PORT = 45678


class VideoThread(QThread):
    """Thread for synchronized audio/video playback using unified decoder"""
    frame_ready = pyqtSignal(np.ndarray)
    playback_finished = pyqtSignal(np.ndarray)  # Send last frame with signal

    def __init__(self, video_path, duration=0):
        super().__init__()
        self.video_path = video_path
        self.duration = duration
        self.running = True
        self.media_player = None

    def run(self):
        """Play video with PERFECTLY synchronized audio using unified decoder"""
        import time

        if not SYNC_SUPPORT:
            # Fallback to video-only playback without audio
            print("Playing video without audio (ffpyplayer not available)")
            self._run_video_only()
            return

        try:
            # Create MediaPlayer - handles BOTH audio and video with perfect sync
            # ff_opts: Configure for Raspberry Pi optimization
            ff_opts = {
                'sync': 'audio',  # Sync video to audio clock
                'framedrop': True,  # Drop frames if needed to maintain sync
            }

            # Additional Raspberry Pi optimizations
            if RASPBERRY_PI_MODE:
                ff_opts.update({
                    'fast': True,  # Enable fast decoding
                    'lowres': 0,  # No resolution reduction (0=full, 1=half, 2=quarter)
                    'skip_frame': 0,  # Don't skip frames in decoder (0=none, 1=nonref, 2=bidir)
                })

            self.media_player = MediaPlayer(self.video_path, ff_opts=ff_opts)

        except Exception as e:
            print(f"Error creating MediaPlayer: {e}")
            self.playback_finished.emit(np.array([]))
            return

        start_time_monotonic = time.monotonic()
        last_frame = None
        frame_count = 0

        # Main playback loop - MediaPlayer handles synchronization
        while self.running:
            frame_start = time.monotonic()

            # Get next frame from MediaPlayer (includes audio sync)
            frame_data, val = self.media_player.get_frame()

            if val == 'eof':
                break

            if frame_data is None:
                # No frame ready yet, wait a bit
                time.sleep(0.001)
                continue

            # Extract frame data
            img, pts = frame_data
            width, height = img.get_size()
            frame_array = img.to_bytearray()[0]

            # Convert to numpy array (RGB format from ffpyplayer)
            frame_rgb = np.frombuffer(frame_array, dtype=np.uint8)
            frame_rgb = frame_rgb.reshape((height, width, 3))

            last_frame = frame_rgb
            frame_count += 1

            # PTS-based pacing for smooth, timestamp-accurate playback
            # If pts is available, wait until wall clock reaches start + pts
            try:
                if pts is not None:
                    target_time = start_time_monotonic + float(pts)
                    now = time.monotonic()
                    delay = target_time - now
                    if delay > 0:
                        # Sleep in short chunks to keep UI responsive
                        time.sleep(min(delay, 0.02))
                else:
                    # Fallback to tiny sleep to avoid busy loop
                    time.sleep(PLAYBACK_SLEEP)
            except Exception:
                # Any timing issue: minimal sleep to avoid spin
                time.sleep(PLAYBACK_SLEEP)

            # If duration limit is set, stop once PTS exceeds it
            if self.duration > 0 and pts is not None and pts >= self.duration:
                break

            # Emit frame after pacing
            self.frame_ready.emit(frame_rgb)

        # Cleanup
        if self.media_player:
            try:
                self.media_player.close_player()
            except Exception as e:
                print(f"Error closing MediaPlayer: {e}")
            self.media_player = None

        # Send last frame with finished signal
        if last_frame is not None:
            self.playback_finished.emit(last_frame)
        else:
            self.playback_finished.emit(np.array([]))

    def _run_video_only(self):
        """Fallback: Play video without audio using OpenCV"""
        import time

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print(f"Error: Cannot open video {self.video_path}")
            self.playback_finished.emit(np.array([]))
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0 or fps > 120:
            fps = 30

        frame_delay = 1.0 / fps
        start_time = time.time()
        max_frames = int(self.duration * fps) if self.duration > 0 else float('inf')
        frame_count = 0
        last_frame = None

        while self.running and cap.isOpened() and frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            last_frame = frame_rgb
            self.frame_ready.emit(frame_rgb)

            frame_count += 1

            # Simple timing
            elapsed = time.time() - start_time
            target_time = frame_count * frame_delay
            sleep_time = target_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        cap.release()

        if last_frame is not None:
            self.playback_finished.emit(last_frame)
        else:
            self.playback_finished.emit(np.array([]))

    def stop(self):
        """Stop synchronized audio/video playback"""
        self.running = False

        # Stop MediaPlayer immediately
        if self.media_player:
            try:
                self.media_player.close_player()
            except Exception as e:
                print(f"Error stopping MediaPlayer: {e}")
            self.media_player = None


class IPCServerThread(QThread):
    """Thread for handling IPC socket server"""
    command_received = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.running = True
        self.server_socket = None

    def run(self):
        """Run IPC server"""
        try:
            # Create Unix domain socket
            if os.path.exists(IPC_SOCKET_PATH):
                os.remove(IPC_SOCKET_PATH)

            self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_socket.bind(IPC_SOCKET_PATH)
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)  # Timeout for checking self.running

            while self.running:
                try:
                    client_socket, _ = self.server_socket.accept()
                    data = client_socket.recv(4096).decode('utf-8')

                    if data:
                        try:
                            command = json.loads(data)
                            self.command_received.emit(command)

                            # Send acknowledgment
                            client_socket.send(b"OK")
                        except json.JSONDecodeError as e:
                            print(f"Invalid JSON: {e}")
                            client_socket.send(b"ERROR")

                    client_socket.close()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"IPC error: {e}")

        except Exception as e:
            print(f"IPC server error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
            if os.path.exists(IPC_SOCKET_PATH):
                os.remove(IPC_SOCKET_PATH)

    def stop(self):
        """Stop IPC server"""
        self.running = False


class AdPlayerWindow(QMainWindow):
    def __init__(self, background_image=None):
        super().__init__()

        self.background_image = background_image
        self.current_file = None
        self.video_thread = None
        self.is_transitioning = False
        self.pending_command = None

        # Setup window with high-quality rendering
        self.setWindowTitle('High-Quality Ad Player - IPC Control')

        # Enable high-quality rendering attributes
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WA_NoSystemBackground, False)

        self.showFullScreen()

        # Create label for displaying content with quality settings
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: black;")
        self.label.setScaledContents(False)  # Manual scaling for maximum quality control
        self.setCentralWidget(self.label)

        # Setup opacity effect for smooth transitions
        self.opacity_effect = QGraphicsOpacityEffect(self.label)
        self.label.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        # Setup fade animation (150ms transition)
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(150)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_animation.finished.connect(self.on_fade_finished)

        # Timer for media display
        self.media_timer = QTimer()
        self.media_timer.timeout.connect(self.on_media_timeout)

        # Start IPC server
        self.ipc_thread = IPCServerThread()
        self.ipc_thread.command_received.connect(self.handle_ipc_command)
        self.ipc_thread.start()

        # Delay background display until window is fully initialized
        if self.background_image and os.path.exists(self.background_image):
            QTimer.singleShot(100, self.display_initial_background)

    def _clear_video_layout_cache(self):
        """Clear cached sizing to ensure correct aspect per media item."""
        for attr in [
            '_cached_screen_width', '_cached_screen_height', '_cached_scale',
            '_cached_video_width', '_cached_video_height',
            '_cached_x_offset', '_cached_y_offset'
        ]:
            if hasattr(self, attr):
                delattr(self, attr)

    def display_initial_background(self):
        """Display initial background after window is fully initialized"""
        if self.background_image and os.path.exists(self.background_image):
            self.display_image(self.background_image, 0, is_background=True)

    def handle_ipc_command(self, command):
        """Handle commands received via IPC"""
        cmd_type = command.get('command')

        if cmd_type == 'PLAY':
            filepath = command.get('file')
            duration = command.get('duration', 0)
            if filepath:
                self.play_media(filepath, duration)

        elif cmd_type == 'STOP':
            self.stop_playback(return_to_background=True)

        elif cmd_type == 'EXIT':
            self.close()

    def display_image(self, image_path, duration, is_background=False):
        """Display image with MAXIMUM high quality"""
        try:
            # Load image with Pillow for better quality
            pil_image = Image.open(image_path)

            # Convert to RGB if needed
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')

            # Get screen size - use actual screen geometry, not label size
            from PyQt5.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            screen_geometry = screen.geometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()

            # Fallback to label size if needed
            if screen_width <= 0 or screen_height <= 0:
                screen_size = self.label.size()
                screen_width = screen_size.width()
                screen_height = screen_size.height()

            # Calculate scaling with PRECISE aspect ratio preservation
            img_width, img_height = pil_image.size
            img_aspect = img_width / img_height

            if is_background:
                # Background: fill entire screen (may crop)
                scale = max(screen_width / img_width, screen_height / img_height)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
            else:
                # Regular media: show entire image with EXACT aspect ratio preservation
                scale_width = screen_width / img_width
                scale_height = screen_height / img_height
                scale = min(scale_width, scale_height)

                # Calculate dimensions maintaining PRECISE aspect ratio
                if scale_width <= scale_height:
                    new_width = int(img_width * scale)
                    new_height = int(new_width / img_aspect)
                else:
                    new_height = int(img_height * scale)
                    new_width = int(new_height * img_aspect)

                # Verify aspect ratio preservation
                original_aspect = img_width / img_height
                scaled_aspect = new_width / new_height
                aspect_error = abs(original_aspect - scaled_aspect) / original_aspect * 100
                if aspect_error > 0.5:
                    print(f"  Image aspect ratio error: {aspect_error:.3f}%")

            # Resize with HIGHEST quality (LANCZOS/ANTIALIAS)
            pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)

            # Center crop if background and image is larger than screen
            if is_background and (new_width > screen_width or new_height > screen_height):
                left = (new_width - screen_width) // 2
                top = (new_height - screen_height) // 2
                right = left + screen_width
                bottom = top + screen_height
                pil_image = pil_image.crop((left, top, right, bottom))

            # Convert to QPixmap with high quality
            img_array = np.array(pil_image)
            height, width, channel = img_array.shape
            bytes_per_line = 3 * width

            q_image = QImage(img_array.data, width, height, bytes_per_line, QImage.Format_RGB888)

            # Create pixmap with smooth transformation enabled
            pixmap = QPixmap.fromImage(q_image)

            self.label.setPixmap(pixmap)

            # Set timer if duration specified
            if duration > 0:
                self.media_timer.start(int(duration * 1000))

        except Exception as e:
            print(f"Error displaying image {image_path}: {e}")

    def display_video(self, video_path, duration):
        """Display video with high quality"""
        try:
            # Stop any running video thread
            if self.video_thread and self.video_thread.isRunning():
                self.video_thread.stop()
                self.video_thread.wait()

            # Create and start video thread
            self.video_thread = VideoThread(video_path, duration)
            self.video_thread.frame_ready.connect(self.update_frame)
            self.video_thread.playback_finished.connect(self.on_video_finished)
            # Start with higher priority for smoother playback
            try:
                self.video_thread.start(QThread.TimeCriticalPriority)
            except Exception:
                self.video_thread.start()

        except Exception as e:
            print(f"Error displaying video {video_path}: {e}")

    def update_frame(self, frame):
        """
        Update display with new video frame - QQ PLAYER STYLE
        - FIT mode: Shows ENTIRE video (all area visible)
        - Maintains aspect ratio (no stretching)
        - Adds black bars if needed (letterbox/pillarbox)
        - No cropping - you see 100% of the video
        - Optimized for Raspberry Pi performance
        """
        try:
            # Get frame dimensions
            frame_height, frame_width, channel = frame.shape

            # Get FULL screen dimensions dynamically (cached)
            if not hasattr(self, '_cached_screen_width'):
                from PyQt5.QtWidgets import QApplication
                screen = QApplication.primaryScreen()
                screen_geometry = screen.geometry()
                self._cached_screen_width = screen_geometry.width()
                self._cached_screen_height = screen_geometry.height()

            screen_width = self._cached_screen_width
            screen_height = self._cached_screen_height

            # Calculate scaling for FIT mode with PRECISE aspect ratio preservation
            # Use MINIMUM scale to ensure entire video fits on screen
            if not hasattr(self, '_cached_scale'):
                # Calculate aspect ratios
                video_aspect = frame_width / frame_height
                screen_aspect = screen_width / screen_height

                # Calculate scales for both dimensions
                scale_width = screen_width / frame_width
                scale_height = screen_height / frame_height

                # Use MIN scale to fit entire video (preserves aspect ratio)
                scale = min(scale_width, scale_height)

                # Calculate target dimensions with PRECISE aspect ratio preservation
                # Method: Scale width first, then calculate height to maintain exact aspect ratio
                if scale_width <= scale_height:
                    # Width-limited: video width fills screen width, height is proportional
                    self._cached_video_width = int(frame_width * scale)
                    # Calculate height to maintain EXACT aspect ratio
                    self._cached_video_height = int(self._cached_video_width / video_aspect)
                else:
                    # Height-limited: video height fills screen height, width is proportional
                    self._cached_video_height = int(frame_height * scale)
                    # Calculate width to maintain EXACT aspect ratio
                    self._cached_video_width = int(self._cached_video_height * video_aspect)

                self._cached_scale = scale

                # Verify aspect ratio is preserved (within 0.1% tolerance)
                original_aspect = frame_width / frame_height
                scaled_aspect = self._cached_video_width / self._cached_video_height
                aspect_error = abs(original_aspect - scaled_aspect) / original_aspect * 100

                # Calculate offsets to center video (creates black bars)
                self._cached_x_offset = (screen_width - self._cached_video_width) // 2
                self._cached_y_offset = (screen_height - self._cached_video_height) // 2

                # Only print warning if aspect ratio error is significant
                if aspect_error > 0.5:
                    print(f"WARNING: Aspect ratio error {aspect_error:.3f}% (target: <0.1%)")

            # Resize video to fit screen (PRESERVING aspect ratio)
            video_w = self._cached_video_width
            video_h = self._cached_video_height

            if video_w != frame_width or video_h != frame_height:
                # Resize with high-quality interpolation
                # INTER_AREA is best for downscaling (maintains quality)
                frame_resized = cv2.resize(frame, (video_w, video_h), interpolation=FRAME_INTERPOLATION)

                # Verify dimensions after resize (sanity check)
                resized_h, resized_w = frame_resized.shape[:2]
                if resized_w != video_w or resized_h != video_h:
                    print(f"  ERROR: Resize mismatch! Expected {video_w}x{video_h}, got {resized_w}x{resized_h}")
            else:
                frame_resized = frame

            # Create black canvas (full screen size) for QQ Player style
            canvas = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)

            # Place video in center of canvas (creates black bars automatically)
            y_start = self._cached_y_offset
            y_end = y_start + video_h
            x_start = self._cached_x_offset
            x_end = x_start + video_w

            # Safety check: ensure frame fits in canvas
            if y_end <= screen_height and x_end <= screen_width:
                # Copy video to canvas (this shows ALL of the video with NO stretching)
                canvas[y_start:y_end, x_start:x_end] = frame_resized
            else:
                print(f"  ERROR: Frame {video_w}x{video_h} doesn't fit in canvas at offset ({x_start},{y_start})")

            # Convert canvas to QPixmap and display
            bytes_per_line = 3 * screen_width
            q_image = QImage(canvas.data, screen_width, screen_height, bytes_per_line, QImage.Format_RGB888)

            pixmap = QPixmap.fromImage(q_image)
            self.label.setPixmap(pixmap)

        except Exception as e:
            print(f"Error updating frame: {e}")

    def play_media(self, filepath, duration):
        """Play media file with smooth transition"""
        if not os.path.exists(filepath):
            print(f"Warning: File not found: {filepath}")
            return

        # Stop current playback
        self.media_timer.stop()

        # Determine file type
        ext = Path(filepath).suffix.lower()
        is_image = ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']

        # Store current file
        self.current_file = filepath

        # Fade out and switch
        if self.opacity_effect.opacity() > 0:
            # Ensure fresh layout calc for next media
            self._clear_video_layout_cache()
            self.pending_command = {'type': 'play', 'file': filepath, 'duration': duration, 'is_image': is_image}
            self.fade_out()
        else:
            # Direct play if already faded
            self._clear_video_layout_cache()
            if is_image:
                self.display_image(filepath, duration, is_background=False)
            else:
                self.display_video(filepath, duration)
            self.fade_in()

    def stop_playback(self, return_to_background=True):
        """Stop current playback and optionally return to background"""
        # Stop timers
        self.media_timer.stop()

        # Stop video thread
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()
            self.video_thread.wait()

        # Clear all cached dimensions for next media
        self._clear_video_layout_cache()

        # Return to background only if explicitly requested
        if return_to_background and self.background_image and os.path.exists(self.background_image):
            self.pending_command = {'type': 'background'}
            self.fade_out()

    def on_media_timeout(self):
        """Called when media duration expires - stay on last frame"""
        # Don't return to background automatically
        # Just stop the timer and wait for next command
        self.media_timer.stop()

    def on_video_finished(self, last_frame):
        """Called when video playback finishes - hold last frame cleanly"""
        # Don't return to background automatically
        # Display the last frame as a static image to prevent freezing
        if last_frame is not None and last_frame.size > 0:
            self.update_frame(last_frame)

    def fade_in(self):
        """Fade in current content"""
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()

    def fade_out(self):
        """Fade out current content"""
        if self.is_transitioning:
            return

        self.is_transitioning = True

        # Stop video during transition
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()
            self.video_thread.wait()

        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()

    def on_fade_finished(self):
        """Called when fade animation completes"""
        if self.pending_command:
            cmd = self.pending_command
            self.pending_command = None

            if cmd['type'] == 'play':
                # Switch to new content
                # Ensure fresh layout calc for new media
                self._clear_video_layout_cache()
                if cmd['is_image']:
                    self.display_image(cmd['file'], cmd['duration'], is_background=False)
                else:
                    self.display_video(cmd['file'], cmd['duration'])
                self.fade_in()
            elif cmd['type'] == 'background':
                # Return to background
                # Clear any video layout cache so next video recalculates
                self._clear_video_layout_cache()
                self.display_image(self.background_image, 0, is_background=True)
                self.fade_in()

        self.is_transitioning = False

    def keyPressEvent(self, event):
        """Handle key press"""
        if event.key() == Qt.Key_Q or event.key() == Qt.Key_Escape:
            self.close()

    def closeEvent(self, event):
        """Clean up on close"""
        # Stop IPC server
        if self.ipc_thread and self.ipc_thread.isRunning():
            self.ipc_thread.stop()
            self.ipc_thread.wait()

        # Stop video thread
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()
            self.video_thread.wait()

        event.accept()


def send_ipc_command(command):
    """Send command to running instance via IPC"""
    try:
        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client_socket.settimeout(2.0)
        client_socket.connect(IPC_SOCKET_PATH)

        # Send command
        client_socket.send(json.dumps(command).encode('utf-8'))

        # Wait for response
        response = client_socket.recv(1024).decode('utf-8')
        client_socket.close()

        return response == "OK"
    except Exception as e:
        print(f"IPC send error: {e}")
        return False


def is_instance_running():
    """Check if instance is already running"""
    return os.path.exists(IPC_SOCKET_PATH)


def kill_existing_instance():
    """Kill existing instance"""
    import subprocess
    import time

    try:
        # First try to send exit command via IPC
        if is_instance_running():
            print("Sending exit command to existing instance...")
            try:
                command = {'command': 'EXIT'}
                send_ipc_command(command)
                time.sleep(0.5)  # Wait for graceful shutdown
            except:
                pass

        # If still running, force kill (excluding current process)
        current_pid = os.getpid()
        result = subprocess.run(
            ["pgrep", "-f", "python.*run.py"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid and pid.strip() and int(pid) != current_pid:
                    print(f"Killing process {pid}...")
                    subprocess.run(["kill", "-9", pid], check=False)

        # Clean up socket
        if os.path.exists(IPC_SOCKET_PATH):
            os.remove(IPC_SOCKET_PATH)

        time.sleep(0.3)  # Wait for cleanup

    except Exception as e:
        print(f"Error killing instance: {e}")


def main():
    parser = argparse.ArgumentParser(description='Video Player with IPC Control')
    parser.add_argument('--start', metavar='BACKGROUND', help='Start GUI with background image')
    parser.add_argument('--play', nargs=2, metavar=('FILE', 'DURATION'), help='Play file with duration')
    parser.add_argument('--stop', action='store_true', help='Stop playback')
    parser.add_argument('--exit', action='store_true', help='Exit GUI')
    parser.add_argument('--single-instance', action='store_true', help='Enable single instance mode')

    args = parser.parse_args()

    # Handle --start command
    if args.start:
        # Kill existing instance if single-instance mode
        if args.single_instance and is_instance_running():
            print("Existing instance found. Restarting...")
            kill_existing_instance()

        # Start new GUI instance
        app = QApplication(sys.argv)
        window = AdPlayerWindow(background_image=args.start)
        sys.exit(app.exec_())

    # Handle --play command
    elif args.play:
        import time
        filepath, duration = args.play
        duration = int(duration)

        if is_instance_running():
            command = {'command': 'PLAY', 'file': filepath, 'duration': duration}
            if send_ipc_command(command):
                # Wait for exact playback duration + minimal transition buffer
                wait_time = duration + 0.001
                time.sleep(wait_time)
            else:
                print("Failed to send play command")
        else:
            print("No running instance found. Use --start first.")
            sys.exit(1)

    # Handle --stop command
    elif args.stop:
        if is_instance_running():
            command = {'command': 'STOP'}
            if send_ipc_command(command):
                print("Stop command sent")
            else:
                print("Failed to send stop command")
        else:
            print("No running instance found")

    # Handle --exit command
    elif args.exit:
        if is_instance_running():
            command = {'command': 'EXIT'}
            if send_ipc_command(command):
                print("Exit command sent")
            else:
                print("Failed to send exit command")
        else:
            print("No running instance found")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
