#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-/home/pi/catcam_record}"
SEGMENT_SEC="${2:-60}"
WIDTH="${3:-1280}"
HEIGHT="${4:-720}"
FPS="${5:-30}"
DEVICE="${6:-/dev/video0}"

mkdir -p "$OUT_DIR"

ffmpeg -f v4l2 -video_size "${WIDTH}x${HEIGHT}" -framerate "$FPS" -i "$DEVICE" \
  -c:v libx264 -preset veryfast -tune zerolatency \
  -f segment -segment_time "$SEGMENT_SEC" -reset_timestamps 1 \
  "${OUT_DIR}/seg_%Y%m%d_%H%M%S.mp4"
