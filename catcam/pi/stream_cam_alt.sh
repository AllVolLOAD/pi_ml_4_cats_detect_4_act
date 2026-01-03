#!/bin/bash
# Альтернативный скрипт стриминга (если основной не работает)
# Использование: ./stream_cam_alt.sh [CAMERA_INDEX] [SRT_PORT]

CAMERA_INDEX=${1:-0}
SRT_PORT=${2:-9000}
SRT_HOST="0.0.0.0"

WIDTH=1280
HEIGHT=720
FPS=30
BITRATE="2M"
PRESET="ultrafast"

LATENCY=200
MAXBW=10000000

echo "========================================="
echo "CatCam SRT Streamer (Alt версия)"
echo "========================================="
echo "Камера: /dev/video${CAMERA_INDEX}"
echo "SRT порт: ${SRT_PORT}"
echo ""

# Вариант 1: Если камера поддерживает YUYV
echo "Пробуем формат YUYV..."
ffmpeg -f v4l2 \
    -input_format yuyv422 \
    -video_size ${WIDTH}x${HEIGHT} \
    -framerate ${FPS} \
    -i /dev/video${CAMERA_INDEX} \
    -c:v libx264 \
    -preset ${PRESET} \
    -tune zerolatency \
    -b:v ${BITRATE} \
    -maxrate ${BITRATE} \
    -bufsize $((${BITRATE%M} * 2))M \
    -g ${FPS} \
    -pix_fmt yuv420p \
    -f mpegts \
    "srt://${SRT_HOST}:${SRT_PORT}?mode=listener&latency=${LATENCY}&maxbw=${MAXBW}" 2>&1 || {
    
    echo ""
    echo "YUYV не работает, пробуем MJPEG с конвертацией..."
    
    # Вариант 2: MJPEG с явной конвертацией
    ffmpeg -f v4l2 \
        -input_format mjpeg \
        -video_size ${WIDTH}x${HEIGHT} \
        -framerate ${FPS} \
        -i /dev/video${CAMERA_INDEX} \
        -vf "scale=${WIDTH}:${HEIGHT},format=yuv420p" \
        -c:v libx264 \
        -preset ${PRESET} \
        -tune zerolatency \
        -b:v ${BITRATE} \
        -maxrate ${BITRATE} \
        -bufsize $((${BITRATE%M} * 2))M \
        -g ${FPS} \
        -pix_fmt yuv420p \
        -f mpegts \
        "srt://${SRT_HOST}:${SRT_PORT}?mode=listener&latency=${LATENCY}&maxbw=${MAXBW}"
}

