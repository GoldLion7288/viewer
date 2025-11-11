

import sys
import os
import socket
import json
import argparse
from pathlib import Path
from collections import deque
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QGraphicsOpacityEffect
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPixmap, QImage
import cv2
from PIL import Image
import numpy as np
from ffpyplayer.player import MediaPlayer
import time
import platform


# IPC Configuration
IPC_SOCKET_PATH = '/tmp/video_player_ipc.sock'
# Global readiness flag: becomes True after background image is displayed
GLOBAL_READY = False
IPC_PORT = 45678

# Performance Configuration
FRAME_BUFFER_SIZE = 3  # Pre-buffer 3 frames for smooth playback
FRAME_POOL_SIZE = 5    # Reuse frame buffers to reduce allocations
ENABLE_HARDWARE_ACCEL = True  # Enable hardware H.264 decoding


class FramePool:
    """Memory pool for reusing frame buffers - reduces allocation overhead"""
    def __init__(self, max_size=FRAME_POOL_SIZE):
        self.pool = deque(maxlen=max_size)
        self.max_size = max_size

    def get(self, shape):
        """Get a frame buffer from pool or create new one"""
        # Try to reuse existing buffer with matching shape
        for i, frame in enumerate(self.pool):
            if frame.shape == shape:
                return self.pool[i]

        # Create new buffer if pool is not full
        if len(self.pool) < self.max_size:
            return np.empty(shape, dtype=np.uint8)

        # Reuse oldest buffer and resize if needed
        frame = self.pool.popleft()
        if frame.shape != shape:
            frame = np.empty(shape, dtype=np.uint8)
        return frame

    def release(self, frame):
        """Return frame buffer to pool"""
        if len(self.pool) < self.max_size:
            self.pool.append(frame)


class OptimizedVideoThread(QThread):
    """Optimized thread for H.264 hardware-accelerated video playback"""
    frame_ready = pyqtSignal(np.ndarray)
    playback_finished = pyqtSignal(np.ndarray)

    def __init__(self, video_path, duration=0):
        super().__init__()
        self.video_path = video_path
        self.duration = duration
        self.running = True
        self.player = None
        self.frame_pool = FramePool()
        self.frame_buffer = deque(maxlen=FRAME_BUFFER_SIZE)

    def get_hardware_codec_options(self):
        """Get hardware acceleration options based on platform"""
        ff_opts = {
            'paused': False,
            'autoexit': False,
            'sync': 'audio',  # Sync to audio for better A/V sync
        }

        if not ENABLE_HARDWARE_ACCEL:
            return ff_opts

        system = platform.system()
        machine = platform.machine()

        # Raspberry Pi hardware acceleration (H.264 MMAL or V4L2 M2M)
        if 'arm' in machine.lower() or 'aarch64' in machine.lower():
            ff_opts['codec'] = 'h264_mmal'  # Try MMAL first
            ff_opts['lowres'] = '0'
            ff_opts['fast'] = '1'
            print("Using Raspberry Pi H.264 hardware acceleration (MMAL)")

        # NVIDIA GPU acceleration
        elif os.path.exists('/proc/driver/nvidia/version'):
            ff_opts['codec'] = 'h264_cuvid'
            ff_opts['hwaccel'] = 'cuda'
            print("Using NVIDIA H.264 hardware acceleration (CUVID)")

        # Intel hardware acceleration (VAAPI on Linux)
        elif system == 'Linux' and os.path.exists('/dev/dri'):
            ff_opts['hwaccel'] = 'vaapi'
            ff_opts['hwaccel_device'] = '/dev/dri/renderD128'
            print("Using Intel H.264 hardware acceleration (VAAPI)")

        # Windows hardware acceleration (DXVA2)
        elif system == 'Windows':
            ff_opts['hwaccel'] = 'dxva2'
            print("Using Windows H.264 hardware acceleration (DXVA2)")

        else:
            print("Using software H.264 decoding (no hardware acceleration detected)")

        return ff_opts

    def run(self):
        """Optimized playback with H.264 hardware acceleration and frame buffering"""
        try:
            # Create MediaPlayer with hardware acceleration
            ff_opts = self.get_hardware_codec_options()

            try:
                self.player = MediaPlayer(self.video_path, ff_opts=ff_opts)
            except Exception as e:
                # Fallback to software decoding if hardware acceleration fails
                print(f"Hardware acceleration failed, using software decoding: {e}")
                ff_opts = {'paused': False, 'autoexit': False, 'sync': 'audio'}
                self.player = MediaPlayer(self.video_path, ff_opts=ff_opts)

            start_time = time.time()
            last_frame = None
            frame_count = 0
            dropped_frames = 0

            # Performance tracking
            last_pts = 0
            target_frame_time = 1.0 / 30.0  # Assume 30fps, will adjust dynamically
            fps_samples = []

            print(f"Starting optimized H.264 playback: {self.video_path}")

            # Pre-buffer frames before starting display
            prebuffer_count = 0
            while prebuffer_count < FRAME_BUFFER_SIZE and self.running:
                frame_data, val = self.player.get_frame()
                if frame_data is not None:
                    img, pts = frame_data
                    if img is not None:
                        width, height = img.get_size()
                        buf = img.to_bytearray()[0]

                        # Use frame pool for memory efficiency
                        frame_shape = (height, width, 3)
                        frame_rgb = self.frame_pool.get(frame_shape)
                        np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 3, out=frame_rgb)

                        self.frame_buffer.append((frame_rgb.copy(), pts))
                        prebuffer_count += 1
                else:
                    time.sleep(0.001)

            print(f"Pre-buffered {prebuffer_count} frames")

            # Main playback loop - optimized with frame buffering
            last_display_time = time.time()

            while self.running:
                # Check duration limit
                if self.duration > 0:
                    elapsed = time.time() - start_time
                    if elapsed >= self.duration:
                        print(f"Duration limit reached: {elapsed:.2f}s")
                        break

                # Display buffered frame if available
                if self.frame_buffer:
                    frame_rgb, pts = self.frame_buffer.popleft()

                    # Get audio sync
                    audio_pts = self.player.get_pts()

                    # Calculate frame timing
                    current_time = time.time()
                    frame_display_time = current_time - last_display_time
                    last_display_time = current_time

                    # Dynamic FPS estimation
                    if len(fps_samples) < 30:
                        fps_samples.append(frame_display_time)
                        if len(fps_samples) >= 10:
                            avg_frame_time = sum(fps_samples) / len(fps_samples)
                            target_frame_time = avg_frame_time

                    # Emit frame for display
                    self.frame_ready.emit(frame_rgb)
                    last_frame = frame_rgb
                    frame_count += 1

                    # Return frame to pool
                    self.frame_pool.release(frame_rgb)

                    # Precise A/V sync
                    if audio_pts > 0 and pts > 0:
                        delay = pts - audio_pts

                        if delay > 0.002:  # Video ahead of audio (>2ms)
                            # Sleep to sync with audio
                            sleep_time = min(delay, 0.05)  # Cap at 50ms
                            time.sleep(sleep_time)
                        elif delay < -0.08:  # Video behind audio (>80ms)
                            # Drop frames to catch up
                            dropped_frames += 1
                            continue
                    else:
                        # No audio sync, use target frame time
                        time.sleep(max(0.001, target_frame_time - frame_display_time))

                # Fetch next frame to maintain buffer
                while len(self.frame_buffer) < FRAME_BUFFER_SIZE and self.running:
                    frame_data, val = self.player.get_frame()

                    if val == 'eof':
                        print("End of file reached")
                        self.running = False
                        break
                    elif val == 'paused':
                        time.sleep(0.01)
                        break

                    if frame_data is None:
                        time.sleep(0.001)
                        break

                    img, pts = frame_data
                    if img is None:
                        break

                    try:
                        width, height = img.get_size()
                        buf = img.to_bytearray()[0]

                        # Use frame pool for memory efficiency
                        frame_shape = (height, width, 3)
                        frame_rgb = self.frame_pool.get(frame_shape)
                        np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 3, out=frame_rgb)

                        self.frame_buffer.append((frame_rgb.copy(), pts))

                    except Exception as e:
                        print(f"Frame conversion error: {e}")
                        break

            playback_time = time.time() - start_time
            fps = frame_count / playback_time if playback_time > 0 else 0
            print(f"Playback finished: {frame_count} frames, {playback_time:.2f}s, {fps:.2f} fps")
            print(f"Dropped frames: {dropped_frames} ({(dropped_frames/frame_count*100) if frame_count > 0 else 0:.1f}%)")

        except Exception as e:
            print(f"Playback error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Clean shutdown
            if self.player:
                try:
                    self.player.close_player()
                except:
                    pass
                self.player = None

            # Clear buffers
            self.frame_buffer.clear()

            # Send last frame
            if last_frame is not None:
                self.playback_finished.emit(last_frame)
            else:
                self.playback_finished.emit(np.array([]))

    def stop(self):
        """Stop playback"""
        self.running = False
        if self.player:
            try:
                self.player.close_player()
            except:
                pass
            self.player = None


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

            print(f"IPC Server listening on {IPC_SOCKET_PATH}")

            while self.running:
                try:
                    client_socket, _ = self.server_socket.accept()
                    data = client_socket.recv(4096).decode('utf-8')

                    if data:
                        try:
                            command = json.loads(data)
                            print(f"Received command: {command}")

                            # Special STATUS command: report if background is displayed
                            cmd_type = command.get('command')
                            if cmd_type == 'STATUS':
                                try:
                                    from run import GLOBAL_READY  # same module
                                except Exception:
                                    # Fallback if import path differs
                                    ready = False
                                else:
                                    ready = GLOBAL_READY
                                client_socket.send(b"READY" if ready else b"NOT_READY")
                            else:
                                # Forward normal commands to main window
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


class OptimizedAdPlayerWindow(QMainWindow):
    """Optimized window with hardware acceleration and reduced CPU usage"""
    def __init__(self, background_image=None):
        super().__init__()

        self.background_image = background_image
        self.current_file = None
        self.video_thread = None
        self.is_transitioning = False
        self.pending_command = None

        # Cache for scaled frames to reduce CPU usage
        self._frame_cache = None
        self._cache_key = None

        # Setup window with optimized rendering
        self.setWindowTitle('Optimized H.264 Video Player - Hardware Accelerated')

        # Enable optimized rendering attributes
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        self.setAttribute(Qt.WA_DontCreateNativeAncestors, True)
        self.setAttribute(Qt.WA_NativeWindow, True)

        self.showFullScreen()

        # Create label for displaying content
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: black;")
        self.label.setScaledContents(False)
        self.setCentralWidget(self.label)

        # Setup opacity effect for smooth transitions
        self.opacity_effect = QGraphicsOpacityEffect(self.label)
        self.label.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        # Setup fade animation (100ms for snappier transitions)
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(100)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_animation.finished.connect(self.on_fade_finished)

        # Timer for media display
        self.media_timer = QTimer()
        self.media_timer.timeout.connect(self.on_media_timeout)

        # Start IPC server
        self.ipc_thread = IPCServerThread()
        self.ipc_thread.command_received.connect(self.handle_ipc_command)
        self.ipc_thread.start()

        # Get screen size once and cache
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self.screen_width = screen_geometry.width()
        self.screen_height = screen_geometry.height()

        print(f"Screen resolution: {self.screen_width}x{self.screen_height}")

        # Delay background display until window is fully initialized
        if self.background_image and os.path.exists(self.background_image):
            QTimer.singleShot(100, self.display_initial_background)

    def display_initial_background(self):
        """Display initial background after window is fully initialized"""
        if self.background_image and os.path.exists(self.background_image):
            self.display_image(self.background_image, 0, is_background=True)
            # Mark global readiness once background is rendered
            global GLOBAL_READY
            GLOBAL_READY = True

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
        """Display image with optimized scaling using cv2 for consistency"""
        try:
            # Read image with cv2 (faster than PIL for our use case)
            img = cv2.imread(image_path)
            if img is None:
                print(f"Failed to load image: {image_path}")
                return

            # Convert BGR to RGB
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            img_height, img_width = img.shape[:2]

            # Calculate optimal scaling
            if is_background:
                # Background: fill entire screen (may crop)
                scale = max(self.screen_width / img_width, self.screen_height / img_height)
            else:
                # Regular media: fit entire image (may have letterbox)
                scale = min(self.screen_width / img_width, self.screen_height / img_height)

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            print(f"Image size adjusted: {img_width}x{img_height} → {new_width}x{new_height} (bg={is_background})")

            # Resize with optimized interpolation (INTER_AREA for downscaling, INTER_LINEAR for upscaling)
            if scale < 1.0:
                img_resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            else:
                img_resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

            # Center crop if background and oversized
            if is_background and (new_width > self.screen_width or new_height > self.screen_height):
                start_x = (new_width - self.screen_width) // 2
                start_y = (new_height - self.screen_height) // 2
                img_resized = img_resized[start_y:start_y+self.screen_height, start_x:start_x+self.screen_width]
                print(f"Background cropped to: {self.screen_width}x{self.screen_height}")

            # Convert to QImage (optimized path)
            height, width, channel = img_resized.shape
            bytes_per_line = 3 * width
            q_image = QImage(img_resized.data, width, height, bytes_per_line, QImage.Format_RGB888)

            # Create pixmap
            pixmap = QPixmap.fromImage(q_image.copy())  # Copy to prevent data corruption
            self.label.setPixmap(pixmap)

            # Set timer if duration specified
            if duration > 0:
                self.media_timer.start(int(duration * 1000))

        except Exception as e:
            print(f"Error displaying image {image_path}: {e}")
            import traceback
            traceback.print_exc()

    def display_video(self, video_path, duration):
        """Display video with hardware-accelerated H.264 decoding"""
        try:
            # Stop any running video thread
            if self.video_thread and self.video_thread.isRunning():
                self.video_thread.stop()
                self.video_thread.wait()

            # Clear cache
            self._frame_cache = None
            self._cache_key = None
            if hasattr(self, '_cached_video_size'):
                delattr(self, '_cached_video_size')
            if hasattr(self, '_cached_display_size'):
                delattr(self, '_cached_display_size')

            # Create and start optimized video thread
            self.video_thread = OptimizedVideoThread(video_path, duration)
            self.video_thread.frame_ready.connect(self.update_frame_optimized)
            self.video_thread.playback_finished.connect(self.on_video_finished)
            self.video_thread.start()

        except Exception as e:
            print(f"Error displaying video {video_path}: {e}")
            import traceback
            traceback.print_exc()

    def update_frame_optimized(self, frame):
        """Optimized frame update with caching and minimal memory copies"""
        try:
            # Get frame dimensions
            height, width, channel = frame.shape

            # Calculate scaling once and cache
            cache_key = f"{width}x{height}"
            if not hasattr(self, '_cached_video_size') or self._cached_video_size != cache_key:
                # Calculate optimal scaling
                scale = min(self.screen_width / width, self.screen_height / height)
                new_width = int(width * scale)
                new_height = int(height * scale)

                # Cache dimensions
                self._cached_video_size = cache_key
                self._cached_display_size = (new_width, new_height)

                print(f"Video size adjusted: {width}x{height} → {new_width}x{new_height} (screen: {self.screen_width}x{self.screen_height})")
            else:
                new_width, new_height = self._cached_display_size

            # Ultra-fast scaling with INTER_NEAREST for real-time performance on low-power devices
            # Use INTER_LINEAR for better quality if CPU allows
            if platform.machine().lower() in ['armv7l', 'aarch64']:
                # Raspberry Pi: Use INTER_NEAREST for maximum performance
                interpolation = cv2.INTER_NEAREST
            else:
                # Desktop: Use INTER_LINEAR for better quality
                interpolation = cv2.INTER_LINEAR

            frame_resized = cv2.resize(frame, (new_width, new_height), interpolation=interpolation)

            # Direct conversion to QImage without intermediate copies
            bytes_per_line = 3 * new_width

            # Create QImage directly from numpy array
            # IMPORTANT: Keep frame_resized in scope until QPixmap is created
            q_image = QImage(frame_resized.data, new_width, new_height,
                           bytes_per_line, QImage.Format_RGB888)

            # Fast pixmap conversion (copy needed to avoid data corruption)
            pixmap = QPixmap.fromImage(q_image.copy())

            # Update display
            self.label.setPixmap(pixmap)

        except Exception as e:
            print(f"Error updating frame: {e}")

    def play_media(self, filepath, duration):
        """Play media file with smooth transition"""
        if not os.path.exists(filepath):
            print(f"Warning: File not found: {filepath}")
            return

        print(f"Playing: {filepath} (duration: {duration}s)")

        # Stop current playback
        self.media_timer.stop()

        # Determine file type
        ext = Path(filepath).suffix.lower()
        is_image = ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']

        # Store current file
        self.current_file = filepath

        # Fade out and switch
        if self.opacity_effect.opacity() > 0:
            self.pending_command = {'type': 'play', 'file': filepath, 'duration': duration, 'is_image': is_image}
            self.fade_out()
        else:
            # Direct play if already faded
            if is_image:
                self.display_image(filepath, duration, is_background=False)
            else:
                self.display_video(filepath, duration)
            self.fade_in()

    def stop_playback(self, return_to_background=True):
        """Stop current playback and optionally return to background"""
        print("Stopping playback...")

        # Stop timers
        self.media_timer.stop()

        # Stop video thread
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()
            self.video_thread.wait()

        # Return to background only if explicitly requested
        if return_to_background and self.background_image and os.path.exists(self.background_image):
            self.pending_command = {'type': 'background'}
            self.fade_out()

    def on_media_timeout(self):
        """Called when media duration expires - stay on last frame"""
        self.media_timer.stop()

    def on_video_finished(self, last_frame):
        """Called when video playback finishes - hold last frame cleanly"""
        if last_frame is not None and last_frame.size > 0:
            self.update_frame_optimized(last_frame)
            print("Video finished - holding last frame")

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
                if cmd['is_image']:
                    self.display_image(cmd['file'], cmd['duration'], is_background=False)
                else:
                    self.display_video(cmd['file'], cmd['duration'])
                self.fade_in()
            elif cmd['type'] == 'background':
                # Return to background
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
                time.sleep(0.01)
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

        time.sleep(0.01)

    except Exception as e:
        print(f"Error killing instance: {e}")


def main():
    parser = argparse.ArgumentParser(description='Optimized H.264 Video Player with Hardware Acceleration')
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
        window = OptimizedAdPlayerWindow(background_image=args.start)
        sys.exit(app.exec_())

    # Handle --play command
    elif args.play:
        import time
        filepath, duration = args.play
        duration = int(duration)

        if is_instance_running():
            command = {'command': 'PLAY', 'file': filepath, 'duration': duration}
            if send_ipc_command(command):
                print(f"Play command sent: {filepath}")

                # Wait for exact playback duration + minimal transition buffer
                wait_time = duration + 0.00001
                print(f"Waiting {wait_time}s for playback to complete...")
                time.sleep(wait_time)
                print(f"Playback completed")
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
