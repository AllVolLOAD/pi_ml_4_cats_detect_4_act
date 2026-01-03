#!/bin/bash
# Скрипт SRT стриминга с USB камеры на Raspberry Pi
# Использование: ./stream_cam.sh [CAMERA_INDEX] [SRT_PORT]

# Параметры по умолчанию
CAMERA_INDEX=${1:-0}
SRT_PORT=${2:-9000}
SRT_HOST="0.0.0.0"  # Слушаем на всех интерфейсах

# Параметры видео
WIDTH=1280
HEIGHT=720
FPS=30
BITRATE="2M"
PRESET="ultrafast"  # Низкая задержка для Pi

# SRT параметры
LATENCY=200  # миллисекунды
MAXBW=10000000  # Максимальная пропускная способность (байт/сек)

echo "========================================="
echo "CatCam SRT Streamer для Raspberry Pi"
echo "========================================="
echo "Камера: /dev/video${CAMERA_INDEX}"
echo "SRT порт: ${SRT_PORT}"
echo "Разрешение: ${WIDTH}x${HEIGHT} @ ${FPS} fps"
echo "Битрейт: ${BITRATE}"
echo ""
echo "Подключение к потоку:"
echo "  srt://$(hostname -I | awk '{print $1}'):${SRT_PORT}"
echo ""
echo "Нажмите Ctrl+C для остановки"
echo "========================================="

# FFmpeg команда для стриминга (программное кодирование libx264)
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
    -f mpegts \
    "srt://${SRT_HOST}:${SRT_PORT}?mode=listener&latency=200000"

