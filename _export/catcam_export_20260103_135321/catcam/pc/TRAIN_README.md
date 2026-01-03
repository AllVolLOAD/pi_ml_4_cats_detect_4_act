# Инструкция по обучению модели

## Процесс (пошагово)

### 1. Сбор данных (один раз или несколько раз)
Записывает видео с камеры для разметки:
```powershell
.\scripts\collect_data.ps1 -Duration 3600 -Segment 60
```
- Длительность: сколько секунд записывать (3600 = 1 час)
- Сегменты: по сколько секунд разбивать (60 = 1 минута)
- Результат: видео файлы в `data/raw_videos/`

### 2. Разметка (для каждого видео отдельно)
Ручная разметка каждого видео файла:
```powershell
.\scripts\annotate.ps1 -Video "..\data\raw_videos\20240101_120000_segment_001.mp4"
```
- Открывается окно с видео
- Мышь: рисуешь рамку вокруг кота
- 1-4: выбор класса (eating/drinking/playing/sleeping)
- Space: следующий кадр
- S: сохранить
- Q: выход
- Результат: JSON файл с аннотациями в `data/annotations/`

**Нужно разметить минимум 100-200 кадров с разными классами!**

### 3. Подготовка датасета (один раз, после всех разметок)
Конвертирует все аннотации в формат для обучения:
```powershell
.\scripts\prepare_dataset.ps1
```
- Читает все JSON из `data/annotations/`
- Извлекает кадры с аннотациями
- Конвертирует в YOLO формат
- Разделяет на train/val (80/20)
- Результат: датасет в `data/dataset/`

### 4. Обучение (один раз)
Обучает модель:
```powershell
.\scripts\train_model.ps1 -Model n -Epochs 100 -Batch 16
```
- Model: n/s/m/l/x (n = nano, самый быстрый)
- Epochs: сколько эпох обучать
- Batch: размер батча (зависит от VRAM)
- Результат: обученная модель в `data/models/cat_activity/weights/best.pt`

## Полный пайплайн (автоматический, но требует ручной разметки)

Можно запустить всё сразу, но на этапе разметки нужно будет вручную обработать видео:
```powershell
.\scripts\train_pipeline.ps1
```

## Минимальный рабочий пример

```powershell
# 1. Записать 10 минут видео
.\scripts\collect_data.ps1 -Duration 600 -Segment 60

# 2. Разметить несколько видео (повторить для каждого)
.\scripts\annotate.ps1 -Video "..\data\raw_videos\20240101_120000_segment_001.mp4"
.\scripts\annotate.ps1 -Video "..\data\raw_videos\20240101_120000_segment_002.mp4"

# 3. Подготовить датасет
.\scripts\prepare_dataset.ps1

# 4. Обучить (быстро, для теста)
.\scripts\train_model.ps1 -Model n -Epochs 20 -Batch 8
```

## После обучения

Использовать обученную модель в ai_detector.py:
```python
# В config.yaml указать путь к обученной модели
ai:
  model_path: "../data/models/cat_activity/weights/best.pt"
  class_filter: ["eating", "drinking", "playing", "sleeping"]
```

