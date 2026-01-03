# CatCam - Система стриминга с детекцией кота в Twitch

Система для стриминга видео с Raspberry Pi с автоматической детекцией кота и наложением bounding box в реальном времени.

## Архитектура

```
Raspberry Pi (SRT 720p30) → PC Receiver → AI Detector → Streamer (overlay + RTMP Twitch)
```

## Быстрый старт

### Требования

- **Raspberry Pi 4**: USB камера, подключение к сети
- **Windows PC**: Python 3.13+, NVIDIA GPU (RTX 3060), FFmpeg
- **Twitch**: Stream key для RTMP стриминга

### Установка

1. **На PC:**
   ```powershell
   cd catcam/pc
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Настройка конфигурации:**
   Отредактируйте `pc/config.yaml`:
   - SRT URL и порт
   - Twitch RTMP URL и stream key
   - Путь к YOLOv8 модели

3. **Запуск:**
   ```powershell
   cd catcam/pc
   .\scripts\run_all.ps1
   ```

### Компоненты

- **pi/stream_cam.sh**: SRT стрим с камеры на Raspberry Pi
- **pc/receiver.py**: Прием и декодирование SRT потока
- **pc/ai_detector.py**: Детекция кота через YOLOv8
- **pc/streamer.py**: Наложение bbox и стрим в Twitch

## Обучение модели

Для обучения модели детекции активности кошек:

1. **Сбор данных**: `.\pc\scripts\collect_data.ps1`
2. **Разметка**: `.\pc\scripts\annotate.ps1 -Video <путь>` (ручная работа)
3. **Подготовка**: `.\pc\scripts\prepare_dataset.ps1`
4. **Обучение**: `.\pc\scripts\train_model.ps1`

Подробная инструкция: [pc/TRAIN_README.md](pc/TRAIN_README.md)

---

Подробная документация: [docs/architecture.md](docs/architecture.md)

