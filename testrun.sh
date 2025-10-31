#!/bin/bash
# Test script for video player
# Demonstrates the complete workflow

# Wait for system to be ready
sleep 1

# 1. Start GUI with background image
echo "=== Step 1: Starting GUI with background ==="
/home/pi/video/run.sh start /home/pi/background.jpg
sleep 2

# 2. Play first video
echo "=== Step 2: Playing test1.mp4 for 10 seconds ==="
/home/pi/video/run.sh play /home/pi/data/test1.mp4 10
sleep 11

# 3. Play second video
echo "=== Step 3: Playing test2.mp4 for 80 seconds ==="
/home/pi/video/run.sh play /home/pi/data/test2.mp4 80
sleep 81

# 4. Stop playback (return to background)
echo "=== Step 4: Stopping playback ==="
/home/pi/video/run.sh stop
sleep 2

# 5. Play image
echo "=== Step 5: Playing test1.jpg for 10 seconds ==="
/home/pi/video/run.sh play /home/pi/data/test1.jpg 10
sleep 11

# 6. Play first video again
echo "=== Step 6: Playing test1.mp4 for 80 seconds ==="
/home/pi/video/run.sh play /home/pi/data/test1.mp4 80
sleep 81

# 7. Play second video again
echo "=== Step 7: Playing test2.mp4 for 80 seconds ==="
/home/pi/video/run.sh play /home/pi/data/test2.mp4 80
sleep 81

# 8. Play image again
echo "=== Step 8: Playing test1.jpg for 10 seconds ==="
/home/pi/video/run.sh play /home/pi/data/test1.jpg 10
sleep 11

# 9. Play first video one more time
echo "=== Step 9: Playing test1.mp4 for 80 seconds ==="
/home/pi/video/run.sh play /home/pi/data/test1.mp4 80
sleep 81

# 10. Play second video one more time
echo "=== Step 10: Playing test2.mp4 for 80 seconds ==="
/home/pi/video/run.sh play /home/pi/data/test2.mp4 80
sleep 81

# 11. Stop playback
echo "=== Step 11: Stopping playback ==="
/home/pi/video/run.sh stop
sleep 2

# 12. Exit GUI
echo "=== Step 12: Exiting GUI ==="
/home/pi/video/run.sh exit

echo "=== Test completed ==="
