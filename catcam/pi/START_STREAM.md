# Запуск SRT стрима на Raspberry Pi

## Быстрый старт

```bash
# 1. Подключитесь к Pi по SSH
ssh pi@192.168.1.100

# 2. Перейдите в папку проекта
cd catcam/pi

# 3. Сделайте скрипт исполняемым (если еще не сделано)
chmod +x stream_cam.sh

# 4. Запустите стрим
./stream_cam.sh
```

## Проверка что стрим работает

В другом терминале (на Pi):

```bash
# Проверка процесса
ps aux | grep ffmpeg

# Проверка порта
sudo netstat -tulpn | grep 9000

# Должно показать что порт 9000 слушается
```

## Если не работает

### Камера не определяется

```bash
# Проверка USB устройств
lsusb

# Проверка видео устройств
ls -l /dev/video*

# Проверка доступных форматов камеры
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

### FFmpeg не установлен

```bash
sudo apt update
sudo apt install -y ffmpeg
```

### Порты заняты

```bash
# Убить процесс на порту 9000 (если есть)
sudo lsof -ti:9000 | xargs sudo kill
```

## Автозапуск (опционально)

Чтобы стрим запускался автоматически при загрузке Pi:

```bash
# Копируем service файл
sudo cp cam-stream.service /etc/systemd/system/

# Включаем автозапуск
sudo systemctl enable cam-stream.service

# Запускаем
sudo systemctl start cam-stream.service

# Проверка статуса
sudo systemctl status cam-stream.service
```

