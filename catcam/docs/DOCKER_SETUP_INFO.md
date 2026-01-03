# Информация для Docker-настройки CatCam

Этот файл собирает входные данные и зависимости, которые нужны, чтобы собрать Docker-образ и развернуть его на VPS.

## 1) Что нужно от VPS

Укажите:

- OS и версию (например, Ubuntu 22.04)
- Есть ли NVIDIA GPU
  - Если да: версия CUDA (например, 11.8 или 12.1)
- Доступность SRT источника
  - IP Raspberry Pi
  - Порт SRT (обычно 9000)
- Куда стримить
  - Twitch RTMP URL + stream key
  - или другой RTMP сервер

Пример SRT URL:

```
srt://192.168.1.103:9000?mode=caller&latency=200
```

## 2) Системные зависимости

- FFmpeg (обязательно)
- Python 3.10+ (рекомендуется)

## 3) Python зависимости

Из `catcam/pc/requirements.txt`:

```
opencv-python>=4.8.0
ultralytics>=8.0.0
numpy>=1.24.0
pyyaml>=6.0
torch>=2.0.0
torchvision>=0.15.0
```

PyTorch варианты:

- CUDA: `torch torchvision` с CUDA wheel
- CPU only: `torch torchvision --index-url https://download.pytorch.org/whl/cpu`

## 4) Структура проекта (ключевые файлы)

```
catcam/pc/
  main.py              # запуск
  config.yaml          # конфигурация
  receiver.py          # прием SRT
  ai_detector.py       # детекция YOLOv8
  streamer.py          # overlay + RTMP
  roi/                 # ROI Engine
  telemetry.py         # телеметрия
  storage.py           # пути данных
  requirements.txt
```

## 5) Ключевые параметры config.yaml

Пример:

```yaml
srt:
  url: "srt://192.168.1.103:9000?mode=caller&latency=200"

twitch:
  rtmp_url: "rtmp://live.twitch.tv/app/"
  stream_key: "YOUR_STREAM_KEY_HERE"

stream:
  mode: "twitch"
  width: 1280
  height: 720
  fps: 25
  bitrate: "2500k"

ai:
  model_path: "yolov8n.pt"
  confidence_threshold: 0.2

storage:
  base_path: "/data"
  models_dir: "models"
  logs_dir: "logs"
  datasets_dir: "datasets"
  checkpoints_dir: "checkpoints"
```

## 6) Порты и сеть

Исходящие:
- SRT: UDP 9000
- RTMP: TCP 1935

Внутри контейнера:
- UDP 5555 (bbox AI -> streamer, localhost)

## 7) Volumes

Рекомендуется монтировать:

- `/data` для моделей, логов, датасетов и чекпоинтов

Пример структуры:

```
/data/
  models/
  logs/
  datasets/
  checkpoints/
```

## 8) Команда запуска

```
python main.py
```

Или:

```
python main.py --config /app/config.yaml
```

## 9) Базовый Dockerfile (пример)

```dockerfile
FROM python:3.10-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY catcam/pc/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY catcam/pc/ /app/

VOLUME ["/data"]

CMD ["python", "main.py"]
```

## 10) Базовый docker-compose.yml (пример)

```yaml
version: "3.8"
services:
  catcam:
    build: .
    container_name: catcam
    restart: unless-stopped
    volumes:
      - ./data:/data
      - ./config.yaml:/app/config.yaml
    environment:
      - SRT_URL=srt://192.168.1.103:9000?mode=caller&latency=200
      - TWITCH_STREAM_KEY=your_key_here
    network_mode: host
```

## 11) Проверки перед запуском

На VPS:

```
ffmpeg -version
python3 --version
```

Сеть до Pi:

```
ping 192.168.1.103
nc -zv 192.168.1.103 9000
```

GPU (если есть):

```
nvidia-smi
```
