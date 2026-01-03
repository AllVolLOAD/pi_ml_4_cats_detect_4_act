# Raspberry Pi - Инструкции по настройке стриминга

## Требования

- Raspberry Pi 4 (рекомендуется)
- USB камера
- FFmpeg установлен
- Сетевое подключение

## Установка FFmpeg

```bash
sudo apt update
sudo apt install -y ffmpeg v4l-utils
```

## Проверка камеры

```bash
# Список доступных камер
v4l2-ctl --list-devices

# Проверка разрешений камеры
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

## Запуск стриминга

### Ручной запуск

1. Сделайте скрипт исполняемым:
   ```bash
   chmod +x stream_cam.sh
   ```

2. Запустите стриминг:
   ```bash
   ./stream_cam.sh [CAMERA_INDEX] [SRT_PORT]
   ```
   
   Параметры по умолчанию:
   - CAMERA_INDEX: 0 (первая камера)
   - SRT_PORT: 9000

   Пример:
   ```bash
   ./stream_cam.sh 0 9000
   ```

3. Узнайте IP адрес Pi:
   ```bash
   hostname -I
   ```

4. На PC подключитесь к потоку:
   ```
   srt://<PI_IP>:9000
   ```

### Автозапуск через systemd

1. Скопируйте service файл:
   ```bash
   sudo cp cam-stream.service /etc/systemd/system/
   ```

2. Отредактируйте пути в файле если нужно:
   ```bash
   sudo nano /etc/systemd/system/cam-stream.service
   ```

3. Включите автозапуск:
   ```bash
   sudo systemctl enable cam-stream.service
   sudo systemctl start cam-stream.service
   ```

4. Проверка статуса:
   ```bash
   sudo systemctl status cam-stream.service
   ```

5. Просмотр логов:
   ```bash
   journalctl -u cam-stream.service -f
   ```

## Если стрим падает с ошибкой I/O

Если видите ошибку `Error submitting a packet to the muxer: Input/output error`:

1. **Попробуйте альтернативный скрипт:**
   ```bash
   chmod +x stream_cam_alt.sh
   ./stream_cam_alt.sh
   ```

2. **Проверьте камеру:**
   ```bash
   chmod +x find_camera.sh
   ./find_camera.sh
   ```

3. **Попробуйте уменьшить разрешение:**
   Отредактируйте `stream_cam.sh`:
   ```bash
   WIDTH=640
   HEIGHT=480
   ```

## Устранение проблем

### Камера не определяется

```bash
# Проверка USB устройств
lsusb

# Проверка видео устройств
ls -l /dev/video*

# Тест захвата
ffplay -f v4l2 -video_size 1280x720 -framerate 30 /dev/video0
```

### Низкая производительность

- Уменьшите разрешение: измените WIDTH/HEIGHT в stream_cam.sh
- Уменьшите FPS: измените FPS в stream_cam.sh
- Используйте более быструю SD карту
- Убедитесь, что Pi не перегревается

### Проблемы с сетью

```bash
# Проверка сетевого подключения
ping <PC_IP>

# Проверка открытых портов
sudo netstat -tulpn | grep 9000

# Проверка firewall
sudo ufw status
```

