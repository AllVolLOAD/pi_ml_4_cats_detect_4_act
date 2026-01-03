<!-- d209c04c-1714-4fbc-91d7-334f20251092 4256c0bb-862d-45c1-839a-547c47126056 -->
# План: Телеметрия и стабилизация системы

## Архитектура изменений

```
main.py (CatCamSystem)
├── TelemetryLogger (новый класс)
│   ├── log_telemetry(ts, bbox, conf, roi_result, fps_metrics)
│   └── log_event(event: ActivityEvent, avg_conf)
├── FPSController (новый класс)
│   ├── limit_streamer_fps(frame_queue, target_fps=25)
│   └── track_fps_metrics()
└── Watchdog (новый класс)
    ├── check_receiver_health()
    ├── check_ffmpeg_health()
    └── auto_restart_on_failure()
```

## День 1: Телеметрия и лимиты FPS

### 1.1 Создать telemetry.py модуль

**Файл:** `catcam/pc/telemetry.py`

**Классы:**

- `TelemetryLogger`: запись telemetry.csv и events.jsonl
- `FPSMetrics`: трекинг FPS для Receiver/AI/Streamer
- `BBoxJitterTracker`: расчет jitter (смещение центра bbox)

**Формат telemetry.csv:**

```
ts,has_bbox,conf,cx,cy,w,h,active_zone,zone_timer_sec,fps_receiver,fps_infer,fps_stream,jitter_px
```

**Формат events.jsonl:**

```json
{"start_ts": 1234.5, "end_ts": 1237.2, "type": "eating", "duration": 2.7, "avg_conf": 0.45}
```

### 1.2 Интегрировать телеметрию в main.py

**Изменения:**

- Создать `TelemetryLogger` в `CatCamSystem.__init__`
- В основном цикле `run()` вызывать `telemetry.log_telemetry()` после каждого AI inference
- Логировать события из `roi_result.events`
- Добавить `logs/` директорию с автоподстановкой даты в имя файла

**Структура логов:**

```
logs/
├── telemetry_20250102.csv
├── events_20250102.jsonl
└── system.log (stdout/stderr перенаправление)
```

### 1.3 Ограничить FPS компонентов

**Receiver:** оставить как есть (может быть 60+ fps)

**Streamer:**

- В `main.py` добавить frame skipping для стримера
- Если `config.stream.fps = 25`, не отправлять каждый кадр в streamer
- Использовать timestamp-based throttling: `time.sleep(1.0 / target_fps - elapsed)`

**AI:**

- Уже ограничен через `ai_interval = 1.0 / 8.0` (~8 fps) - проверить что это работает корректно
- Добавить явный параметр `ai.fps_limit` в config.yaml (по умолчанию 8)

### 1.4 Добавить FPS метрики в телеметрию

**В TelemetryLogger:**

- Трекинг `fps_receiver` (от receiver.py через callback или счетчик кадров)
- Трекинг `fps_infer` (количество AI вызовов в секунду)
- Трекинг `fps_stream` (количество кадров отправленных в streamer)

### 1.5 Добавить BBox jitter tracking

**В telemetry.py:**

- `BBoxJitterTracker`: хранит последний центр bbox, вычисляет расстояние между центрами
- Jitter = расстояние (px) между центрами соседних детекций

**Добавить в telemetry.csv:**

- `jitter_px`: смещение центра относительно предыдущего кадра

## День 2: Стабилизация ROI и Watchdog

### 2.1 Добавить hysteresis в ROI Engine

**Файл:** `catcam/pc/roi/roi_engine.py`

**Изменения:**

- Добавить параметр `hysteresis_ticks` в `ROIConfig` (по умолчанию 3)
- Зона не меняется мгновенно, а только если новая зона активна N тиков подряд
- В `ZoneState` добавить `candidate_zone: Optional[str]` и `candidate_ticks: int`
- Логика: если активна новая зона, накапливаем счетчик, если старая - сбрасываем

**Config.yaml:**

```yaml
roi:
  hysteresis_ticks: 3  # Зона меняется только после 3 тиков подряд
```

### 2.2 Добавить watchdog в main.py

**Файл:** `catcam/pc/main.py`

**Класс Watchdog:**

- `check_receiver_health()`: если нет кадров > 5 сек → перезапуск receiver
- `check_streamer_health()`: если FFmpeg процесс умер → перезапуск streamer
- Вызывать каждые 2 секунды в отдельном потоке

**Интеграция:**

- В `CatCamSystem` добавить `watchdog_thread`
- При обнаружении проблемы - логировать и перезапускать компонент

### 2.3 Добавить конфигурацию для телеметрии

**config.yaml:**

```yaml
telemetry:
  enabled: true
  log_dir: "logs"
  telemetry_file: "telemetry_{date}.csv"
  events_file: "events_{date}.jsonl"
  flush_interval: 5.0  # секунды между flush в файл

watchdog:
  enabled: true
  receiver_timeout_sec: 5.0
  streamer_check_interval_sec: 2.0
  auto_restart: true
```

### 2.4 Создать скрипт автозапуска (Windows)

**Файл:** `catcam/pc/scripts/install_service.ps1`

**Функциональность:**

- Создать Task Scheduler task для автозапуска `python main.py`
- Настроить перенаправление stdout/stderr в `logs/system.log`
- Настроить авто-рестарт при падении (через Task Scheduler)

**Альтернатива (проще):**

- Создать batch файл `start_catcam.bat` который запускает Python и рестартит при падении
- Пользователь может добавить его в автозагрузку Windows

## Дополнительные улучшения (опционально)

### Сохранение проблемных клипов

**Файл:** `catcam/pc/hard_cases_recorder.py`

- Горячая клавиша (например, 's' в preview режиме)
- Сохраняет последние 30 секунд в `data/hard_cases/`
- Привязывается к событиям ROI для контекста

### Метрики и анализ

**Скрипт:** `catcam/pc/scripts/analyze_telemetry.py`

- Парсит telemetry.csv
- Вычисляет: detection rate, confidence stats, jitter stats, dropouts
- Генерирует отчет в `logs/report_YYYYMMDD.txt`

## Порядок реализации

**Фаза 1 (День 1):**

1. Создать `telemetry.py` с TelemetryLogger, FPSMetrics, BBoxJitterTracker
2. Добавить секцию `telemetry` в config.yaml
3. Интегрировать телеметрию в main.py (логирование каждого AI тика)
4. Ограничить FPS streamer до 25
5. Тест 30 минут, проверить логи

**Фаза 2 (День 2):**

1. Добавить hysteresis в ROI Engine
2. Создать Watchdog класс
3. Интегрировать watchdog в main.py
4. Добавить конфигурацию watchdog в config.yaml
5. Тест 30 минут, проверить стабильность

**Фаза 3 (опционально):**

1. Скрипт автозапуска
2. Сохранение hard cases
3. Скрипт анализа метрик

### To-dos

- [ ] Создать структуру проекта для тестирования Raspberry Pi
- [ ] Создать telemetry.py с классами TelemetryLogger, FPSMetrics, BBoxJitterTracker
- [ ] Добавить секцию telemetry в config.yaml (enabled, log_dir, flush_interval)
- [ ] Интегрировать TelemetryLogger в main.py - логирование каждого AI inference тика
- [ ] Ограничить FPS streamer до target_fps (25) через frame skipping в main.py
- [ ] Добавить трекинг fps_receiver, fps_infer, fps_stream в телеметрию
- [ ] Реализовать BBoxJitterTracker для расчета jitter_px (смещение центра bbox)
- [ ] Добавить hysteresis в ROI Engine (зона меняется только после N тиков подряд)
- [ ] Создать Watchdog класс в main.py для проверки health receiver/streamer
- [ ] Интегрировать Watchdog в CatCamSystem - запуск в отдельном потоке, авто-рестарт
- [ ] Добавить секцию watchdog в config.yaml (enabled, timeouts, auto_restart)