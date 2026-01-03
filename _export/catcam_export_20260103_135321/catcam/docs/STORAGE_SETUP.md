# Настройка хранилища (USB диск, сетевые пути)

Система поддерживает использование внешних дисков (USB SSD) для хранения моделей, датасетов, логов и чекпоинтов.

## Быстрый старт

### Вариант 1: USB диск на Windows

1. Подключите USB SSD
2. Отформатируйте в NTFS (если нужно)
3. Откройте `catcam/pc/config.yaml`
4. Укажите путь к диску:

```yaml
storage:
  base_path: "E:/catcam_data"  # Замените E: на вашу букву диска
  models_dir: "models"
  datasets_dir: "datasets"
  logs_dir: "logs"
  checkpoints_dir: "checkpoints"
```

### Вариант 2: USB диск на Linux

1. Подключите USB SSD
2. Смонтируйте (обычно автоматически в `/media/username/...`)
3. Создайте папку для данных:
   ```bash
   sudo mkdir -p /mnt/usb/catcam_data
   sudo chown $USER:$USER /mnt/usb/catcam_data
   ```
4. Добавьте в `/etc/fstab` для автоматического монтирования (опционально)
5. В `config.yaml`:

```yaml
storage:
  base_path: "/mnt/usb/catcam_data"
  models_dir: "models"
  datasets_dir: "datasets"
  logs_dir: "logs"
  checkpoints_dir: "checkpoints"
```

## Структура директорий

После настройки будет создана следующая структура:

```
base_path/
├── models/           # Обученные модели
│   ├── best.pt      # Лучшая модель (копируется после обучения)
│   └── yolov8n.pt   # Предобученные модели (если скачаны)
├── datasets/         # Датасеты
│   └── dataset/
│       ├── data.yaml
│       ├── train/
│       └── val/
├── logs/             # Логи телеметрии
│   ├── telemetry_YYYYMMDD.csv
│   └── events_YYYYMMDD.jsonl
└── checkpoints/      # Чекпоинты обучения
    └── cat_activity/
        ├── weights/
        │   ├── last.pt
        │   ├── best.pt
        │   └── epoch*.pt
        └── results.csv
```

## Обучение с сохранением чекпоинтов

### Продолжение обучения

Если обучение прервалось, можно продолжить с последнего чекпоинта:

```bash
python train.py --resume
```

Или указать конкретный чекпоинт:

```bash
python train.py --resume --checkpoint "E:/catcam_data/checkpoints/cat_activity/weights/last.pt"
```

### Автоматическое сохранение

При обучении автоматически сохраняются:
- **last.pt** - последний чекпоинт (для resume)
- **best.pt** - лучшая модель по метрикам
- **epoch*.pt** - периодические чекпоинты (если включено)

После завершения обучения лучшая модель копируется в `models/best.pt` для использования в production.

## Использование обученной модели

После обучения обновите `config.yaml`:

```yaml
ai:
  model_path: "best.pt"  # Будет искаться в storage/models/
```

Или укажите полный путь:

```yaml
ai:
  model_path: "E:/catcam_data/models/best.pt"
```

## Перемещение данных между системами

Если вы обучаете на одной машине, а используете на другой:

1. Скопируйте `models/best.pt` на целевую систему
2. Обновите `config.yaml` с путем к модели
3. Или скопируйте весь `base_path/` и используйте тот же путь в конфиге

## Сетевые пути

Система поддерживает сетевые пути (SMB, NFS):

**Windows:**
```yaml
storage:
  base_path: "\\\\server\\share\\catcam_data"
```

**Linux:**
```yaml
storage:
  base_path: "/mnt/nas/catcam_data"
```

## Проверка настройки

Проверить пути можно скриптом:

```python
from storage import StoragePaths
import yaml

with open('config.yaml') as f:
    config = yaml.safe_load(f)

storage = StoragePaths(config)
print(storage)
print(f"Models: {storage.models_dir}")
print(f"Checkpoints: {storage.checkpoints_dir}")
```

## Рекомендации

1. **USB 3.0+** - для быстрого доступа к данным и моделям
2. **SSD предпочтительнее HDD** - особенно для чекпоинтов (частые записи)
3. **Резервное копирование** - регулярно копируйте `models/` и `checkpoints/`
4. **Свободное место** - модели могут занимать 50-200MB, чекпоинты могут расти
5. **Файловая система** - NTFS (Windows) или ext4 (Linux) для больших файлов

