#!/bin/bash
# TCP стрим вместо UDP
ffmpeg -f v4l2 -input_format mjpeg -video_size 1280x720 -framerate 30 -i /dev/video0 -c:v libx264 -preset ultrafast -b:v 2M -f mpegts tcp://0.0.0.0:9000?listen

