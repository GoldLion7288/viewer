

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
from ffpyplayer.player import MediaPlayer
import time


# IPC Configuration
IPC_SOCKET_PATH = '/tmp/video_player_ipc.sock'
IPC_PORT = 45678


class VideoThread(QThread):
    """Thread for smooth video playback with audio sync like QQ Player"""
    frame_ready = pyqtSignal(np.ndarray)
    playback_finished = pyqtSignal(np.ndarray)

    def __init__(self, video_path, duration=0):
        super().__init__()
        self.video_path = video_path
        self.duration = duration
        self.running = True
        self.player = None

    def run(self):
        """Play video with synchronized audio - QQ Player style smooth playback"""
        try:
            # Create MediaPlayer with optimized settings for smooth playback
            ff_opts = {
                'paused': False,
                'autoexit': False,
            }

            self.player = MediaPlayer(self.video_path, ff_opts=ff_opts)

            start_time = time.time()
            last_frame = None
            frame_count = 0

            # Performance tracking for smooth playback
            last_pts = 0
            audio_pts = 0

            print(f"Starting smooth playback: {self.video_path}")

            # Main playback loop - synchronized to audio
            while self.running:
                # Check duration limit
                if self.duration > 0:
                    elapsed = time.time() - start_time
                    if elapsed >= self.duration:
                        print(f"Duration limit reached: {elapsed:.2f}s")
                        break

                # Get frame with timing info
                frame_data, val = self.player.get_frame()

                if val == 'eof':
                    print("End of file reached")
                    break
                elif val == 'paused':
                    time.sleep(0.01)
                    continue

                if frame_data is None:
                    # No frame ready yet, small wait
                    time.sleep(0.002)
                    continue

                # Extract image and presentation timestamp
                img, pts = frame_data

                if img is None:
                    continue

                # Get audio/video sync info
                audio_pts = self.player.get_pts()

                # Convert image to numpy array (RGB format)
                try:
                    width, height = img.get_size()
                    buf = img.to_bytearray()[0]
                    frame_rgb = np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 3)

                    # Emit frame for display
                    last_frame = frame_rgb.copy()
                    self.frame_ready.emit(frame_rgb)
                    frame_count += 1

                except Exception as e:
                    print(f"Frame conversion error: {e}")
                    continue

                # A/V sync: Calculate delay based on audio position
                if audio_pts > 0 and pts > 0:
                    delay = pts - audio_pts

                    # Smooth sync adjustment
                    if delay > 0.001:  # Video ahead of audio
                        # Sleep to sync with audio
                        sleep_time = min(delay, 0.1)  # Cap at 100ms
                        time.sleep(sleep_time)
                    elif delay < -0.05:  # Video behind audio (>50ms)
                        # Skip this frame to catch up (frame dropping)
                        continue
                else:
                    # No audio sync available, minimal sleep
                    time.sleep(0.001)

                last_pts = pts

            print(f"Playback finished: {frame_count} frames, {time.time() - start_time:.2f}s")

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

        # Setup window with optimized rendering for smooth playback
        self.setWindowTitle('Smooth Video Player - QQ Player Style')

        # Enable optimized rendering attributes for smooth video
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        self.setAttribute(Qt.WA_DontCreateNativeAncestors, True)
        self.setAttribute(Qt.WA_NativeWindow, True)

        self.showFullScreen()

        # Create label for displaying content with performance optimization
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background-color: black;")
        self.label.setScaledContents(False)  # Manual scaling for control
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
        """Display image with smart full-screen sizing"""
        try:
            # Load image with Pillow for better quality
            pil_image = Image.open(image_path)

            # Convert to RGB if needed
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')

            # Get screen size - use actual screen geometry
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

            # Calculate optimal scaling to fit full screen
            img_width, img_height = pil_image.size

            if is_background:
                # Background: fill entire screen (may crop to maintain aspect ratio)
                scale = max(screen_width / img_width, screen_height / img_height)
            else:
                # Regular media: fit entire image (may have black bars)
                scale = min(screen_width / img_width, screen_height / img_height)

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            print(f"Image size adjusted: {img_width}x{img_height} → {new_width}x{new_height} (screen: {screen_width}x{screen_height}, bg={is_background})")

            # Resize with high quality (LANCZOS)
            pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)

            # Center crop if background and image is larger than screen
            if is_background and (new_width > screen_width or new_height > screen_height):
                left = (new_width - screen_width) // 2
                top = (new_height - screen_height) // 2
                right = left + screen_width
                bottom = top + screen_height
                pil_image = pil_image.crop((left, top, right, bottom))
                print(f"Background cropped to: {screen_width}x{screen_height}")

            # Convert to QPixmap with high quality
            img_array = np.array(pil_image)
            height, width, channel = img_array.shape
            bytes_per_line = 3 * width

            q_image = QImage(img_array.data, width, height, bytes_per_line, QImage.Format_RGB888)

            # Create pixmap
            pixmap = QPixmap.fromImage(q_image)

            self.label.setPixmap(pixmap)

            # Set timer if duration specified
            if duration > 0:
                self.media_timer.start(int(duration * 1000))

        except Exception as e:
            print(f"Error displaying image {image_path}: {e}")

    def display_video(self, video_path, duration):
        """Display video with smart full-screen sizing"""
        try:
            # Stop any running video thread
            if self.video_thread and self.video_thread.isRunning():
                self.video_thread.stop()
                self.video_thread.wait()

            # Clear cached video size to recalculate for new video
            if hasattr(self, '_cached_video_size'):
                delattr(self, '_cached_video_size')
            if hasattr(self, '_cached_display_size'):
                delattr(self, '_cached_display_size')

            # Create and start video thread
            self.video_thread = VideoThread(video_path, duration)
            self.video_thread.frame_ready.connect(self.update_frame)
            self.video_thread.playback_finished.connect(self.on_video_finished)
            self.video_thread.start()

        except Exception as e:
            print(f"Error displaying video {video_path}: {e}")

    def update_frame(self, frame):
        """Update display with new video frame - OPTIMIZED for smooth playback"""
        try:
            # Get frame dimensions
            height, width, channel = frame.shape

            # Check if video resolution changed or cache doesn't exist
            cache_key = f"{width}x{height}"
            if not hasattr(self, '_cached_video_size') or self._cached_video_size != cache_key:
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

                # Calculate optimal scaling to fit full screen while maintaining aspect ratio
                scale = min(screen_width / width, screen_height / height)
                new_width = int(width * scale)
                new_height = int(height * scale)

                # Cache dimensions for this video resolution
                self._cached_video_size = cache_key
                self._cached_display_size = (new_width, new_height)

                print(f"Video size adjusted: {width}x{height} → {new_width}x{new_height} (screen: {screen_width}x{screen_height})")
            else:
                new_width, new_height = self._cached_display_size

            # Fast bilinear interpolation for smoother real-time playback
            # INTER_LINEAR is faster than LANCZOS4 and still provides good quality
            frame_resized = cv2.resize(frame, (new_width, new_height),
                                      interpolation=cv2.INTER_LINEAR)

            # Direct conversion to QImage without intermediate steps
            bytes_per_line = 3 * new_width
            q_image = QImage(frame_resized.data, new_width, new_height,
                           bytes_per_line, QImage.Format_RGB888)

            # Fast pixmap conversion
            pixmap = QPixmap.fromImage(q_image)

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
        # Don't return to background automatically
        # Just stop the timer and wait for next command
        self.media_timer.stop()

    def on_video_finished(self, last_frame):
        """Called when video playback finishes - hold last frame cleanly"""
        # Don't return to background automatically
        # Display the last frame as a static image to prevent freezing
        if last_frame is not None and last_frame.size > 0:
            self.update_frame(last_frame)
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
                time.sleep(0.01)  # Wait for graceful shutdown
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

        time.sleep(0.01)  # Wait for cleanup

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
                print(f"Play command sent: {filepath}")

                # Wait for exact playback duration + minimal transition buffer
                # Duration (actual playback) + fade transitions (300ms) + safety margin (100ms)
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