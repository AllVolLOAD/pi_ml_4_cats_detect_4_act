#!/bin/bash
# Скрипт для поиска и проверки камер

echo "Поиск USB камер..."
echo ""

# Список USB устройств
echo "USB устройства:"
lsusb | grep -i video
echo ""

# Видео устройства
echo "Видео устройства:"
ls -l /dev/video* 2>/dev/null || echo "Нет /dev/video* устройств"
echo ""

# Для каждого видео устройства проверяем форматы
for dev in /dev/video*; do
    if [ -c "$dev" ]; then
        echo "========================================="
        echo "Устройство: $dev"
        echo "========================================="
        v4l2-ctl --device="$dev" --list-formats-ext 2>/dev/null || echo "Ошибка чтения $dev"
        echo ""
    fi
done

# Тест захвата с первого устройства
if [ -c /dev/video0 ]; then
    echo "========================================="
    echo "Тест захвата с /dev/video0 (5 секунд):"
    echo "========================================="
    timeout 5 ffmpeg -f v4l2 -i /dev/video0 -frames:v 10 -f null - 2>&1 | head -20
fi

