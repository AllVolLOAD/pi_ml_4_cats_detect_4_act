#!/bin/bash
# HTTP MJPEG стрим (проще чем TCP/UDP)
# FFmpeg создает HTTP сервер с MJPEG потоком
ffmpeg -f v4l2 -input_format mjpeg -video_size 1280x720 -framerate 30 -i /dev/video0 \
    -c:v copy -f mjpeg http://0.0.0.0:9000/

