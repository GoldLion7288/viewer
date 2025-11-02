

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
    """Thread for video playback with synchronized audio using OpenCV + ffpyplayer"""
    frame_ready = pyqtSignal(np.ndarray)
    playback_finished = pyqtSignal(np.ndarray)  # Send last frame with signal

    def __init__(self, video_path, duration=0):
        super().__init__()
        self.video_path = video_path
        self.duration = duration
        self.running = True
        self.audio_player = None

    def run(self):
        """Play video with audio - OpenCV for video, ffpyplayer for audio"""
        try:
            # Start audio playback with ffpyplayer (async)
            try:
                self.audio_player = MediaPlayer(self.video_path, ff_opts={'vn': True})
                print("Audio playback started")
            except Exception as e:
                print(f"Audio initialization failed (video may not have audio): {e}")
                self.audio_player = None

            # Use OpenCV for reliable video frame extraction
            cap = cv2.VideoCapture(self.video_path)

            if not cap.isOpened():
                print(f"Error: Cannot open video {self.video_path}")
                if self.audio_player:
                    self.audio_player.close_player()
                self.playback_finished.emit(np.array([]))
                return

            # Enable hardware acceleration for better performance
            cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY)

            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps == 0 or fps > 120:  # Sanity check
                fps = 24  # Default fallback

            # Normal speed playback for accurate timing
            speed_multiplier = 1.0
            frame_delay = (1.0 / fps) / speed_multiplier

            frames_played = 0
            max_frames = int(self.duration * fps) if self.duration > 0 else float('inf')
            last_frame = None
            start_time = time.time()

            while self.running and cap.isOpened():
                frame_start = time.time()

                ret, frame = cap.read()

                if not ret or frames_played >= max_frames:
                    break

                # Convert BGR to RGB for Qt with high quality
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                last_frame = frame_rgb  # Keep track of last frame
                self.frame_ready.emit(frame_rgb)

                frames_played += 1

                # Optimized frame timing - use precise sleep
                elapsed = time.time() - frame_start
                sleep_time = frame_delay - elapsed

                if sleep_time > 0.001:  # Only sleep if meaningful time remains
                    self.msleep(int(sleep_time * 1000))

            cap.release()
            print(f"Video playback finished: {frames_played} frames displayed")

        except Exception as e:
            print(f"Error during video playback: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Clean up audio player
            if self.audio_player:
                self.audio_player.close_player()
                self.audio_player = None

            # Send last frame with finished signal
            if last_frame is not None:
                self.playback_finished.emit(last_frame)
            else:
                self.playback_finished.emit(np.array([]))

    def stop(self):
        """Stop video playback and audio"""
        self.running = False
        if self.audio_player:
            self.audio_player.close_player()
            self.audio_player = None


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

            # Calculate scaling based on whether this is background or regular media
            img_width, img_height = pil_image.size
            if is_background:
                # Background: fill entire screen (may crop)
                scale = max(screen_width / img_width, screen_height / img_height)
            else:
                # Regular media: show entire image (may have black bars)
                scale = min(screen_width / img_width, screen_height / img_height)

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            # Extra safety check for regular media - ensure it never exceeds screen
            if not is_background:
                if new_width > screen_width or new_height > screen_height:
                    scale = min(screen_width / new_width, screen_height / new_height)
                    new_width = int(new_width * scale)
                    new_height = int(new_height * scale)

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
            self.video_thread.start()

        except Exception as e:
            print(f"Error displaying video {video_path}: {e}")

    def update_frame(self, frame):
        """Update display with new video frame - HIGH DEFINITION QUALITY"""
        try:
            # Get frame dimensions
            height, width, channel = frame.shape

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

            # Calculate scaling to show entire frame (maintain aspect ratio)
            scale = min(screen_width / width, screen_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)

            # Extra safety check - ensure frame never exceeds screen bounds
            if new_width > screen_width or new_height > screen_height:
                scale = min(screen_width / new_width, screen_height / new_height)
                new_width = int(new_width * scale)
                new_height = int(new_height * scale)

            # Use LANCZOS4 for highest quality scaling
            frame_resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)

            # Convert to QPixmap with high quality settings
            height, width, channel = frame_resized.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame_resized.data, width, height, bytes_per_line, QImage.Format_RGB888)

            # Enable smooth transformation for QPixmap
            pixmap = QPixmap.fromImage(q_image)

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
                print(f"Play command sent: {filepath}")

                # Wait for exact playback duration + minimal transition buffer
                # Duration (actual playback) + fade transitions (300ms) + safety margin (100ms)
                wait_time = duration + 0.001
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