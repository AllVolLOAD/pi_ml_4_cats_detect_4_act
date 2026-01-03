#!/usr/bin/env bash
set -euo pipefail

CAMERA_INDEX=${1:-0}
SRT_PORT=${2:-9000}
OUT_DIR=${3:-/home/$USER/catcam_record}
SEGMENT_SEC=${4:-60}

SRT_HOST="0.0.0.0"
WIDTH=1280
HEIGHT=720
FPS=30
BITRATE="2M"
PRESET="ultrafast"
LATENCY=200000

mkdir -p "$OUT_DIR"

ffmpeg -f v4l2 \
    -input_format mjpeg \
    -framerate ${FPS} \
    -video_size ${WIDTH}x${HEIGHT} \
    -i /dev/video${CAMERA_INDEX} \
    -vf "format=yuv420p" \
    -c:v libx264 \
    -preset ${PRESET} \
    -tune zerolatency \
    -b:v ${BITRATE} \
    -maxrate ${BITRATE} \
    -bufsize $((${BITRATE%M} * 2))M \
    -g 60 \
    -keyint_min 60 \
    -sc_threshold 0 \
    -f tee \
    "[f=mpegts]srt://${SRT_HOST}:${SRT_PORT}?mode=listener&latency=${LATENCY}|[f=segment:segment_time=${SEGMENT_SEC}:reset_timestamps=1:strftime=1]${OUT_DIR}/seg_%Y%m%d_%H%M%S.mp4"
