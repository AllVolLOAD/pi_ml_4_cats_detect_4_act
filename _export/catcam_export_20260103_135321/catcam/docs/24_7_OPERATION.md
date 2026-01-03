# Работа системы 24/7

## Текущий статус

Система работает в **preview режиме** - это режим с GUI окном для тестирования и отладки.

## Preview режим vs Production режим

### Preview режим (текущий)

- ✅ Показывает окно OpenCV с видео и overlay
- ✅ Удобно для тестирования и отладки
- ❌ Требует открытое окно (нельзя свернуть)
- ❌ Завершится если закрыть окно или нажать 'q'
- ⚠️ Не подходит для длительной работы без присмотра

### Production режим (для 24/7)

- ✅ Работает в фоне без GUI окна
- ✅ Можно запускать как службу/автозапуск
- ✅ Стабильная работа без вмешательства
- ❌ Нет визуального preview (нужен мониторинг через логи)

## Переключение в production режим

### Вариант 1: Headless режим (без окна) - РЕКОМЕНДУЕТСЯ

**Проблема:** Текущая версия streamer.py требует GUI окно в preview режиме.

**Временное решение:** Оставить в preview режиме, но:
1. Не закрывать окно
2. Можно свернуть окно (но не закрывать)
3. Оставить PC включенным
4. Мониторить через логи

**Будущее улучшение:** Добавить headless режим без GUI окна.

### Вариант 2: Twitch режим (если есть stream key)

Если есть Twitch stream key, можно переключить в режим стриминга:

```yaml
stream:
  mode: "twitch"  # вместо "preview"
```

В этом режиме нет GUI окна, стрим идет напрямую в Twitch.

## Оставить систему на целый день (preview режим)

### Что нужно сделать:

1. **Не закрывайте окно preview**
   - Можно свернуть, но не закрывать
   - Не нажимайте 'q' в окне

2. **Оставьте PC включенным**
   - Не переводите в спящий режим
   - Настройте: Панель управления → Электропитание → "Никогда" для спящего режима

3. **Проверьте логи телеметрии**
   - Логи пишутся в `logs/telemetry_YYYYMMDD.csv`
   - События в `logs/events_YYYYMMDD.jsonl`
   - Проверяйте периодически

4. **Мониторинг через Watchdog**
   - Watchdog автоматически перезапустит компоненты при проблемах
   - Следите за консолью на ошибки

### Проверка работы:

```powershell
# Проверка размера логов (должны расти)
Get-ChildItem catcam\pc\logs\*.csv | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Format-List Name, Length, LastWriteTime

# Последние события
Get-Content catcam\pc\logs\events_*.jsonl | Select-Object -Last 10
```

## Автозапуск при включении PC

### Windows Task Scheduler

1. **Создайте batch файл** `catcam\pc\scripts\start_catcam.bat`:

```batch
@echo off
cd /d "%~dp0.."
python main.py
pause
```

2. **Создайте задачу в Task Scheduler:**

```powershell
# Запуск от имени администратора
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "C:\NOSYS-WORK\rasberi pi4modB\catcam\pc\main.py" -WorkingDirectory "C:\NOSYS-WORK\rasberi pi4modB\catcam\pc"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
Register-ScheduledTask -TaskName "CatCam System" -Action $action -Trigger $trigger -Principal $principal -Description "Автозапуск CatCam системы"
```

3. **Или через GUI:**
   - Win+R → `taskschd.msc`
   - Создать задачу → Имя: "CatCam System"
   - Триггер: "При входе в систему"
   - Действие: "Запуск программы"
     - Программа: `python.exe`
     - Аргументы: `C:\NOSYS-WORK\rasberi pi4modB\catcam\pc\main.py`
     - Рабочая папка: `C:\NOSYS-WORK\rasberi pi4modB\catcam\pc`

## Мониторинг работы системы

### Через консоль (текущий запуск)

Смотрите на метрики:
- `[System] FPS стрима` - должно быть ~25 FPS
- `Receiver FPS` - должно быть стабильно
- `Infer FPS` - должно быть 5-10 FPS (AI обработка)
- Ошибки в консоли

### Через логи телеметрии

```powershell
# Размер логов (проверка что пишутся)
Get-ChildItem catcam\pc\logs\telemetry_*.csv | Measure-Object -Property Length -Sum

# Количество событий ROI
(Get-Content catcam\pc\logs\events_*.jsonl | Measure-Object -Line).Lines

# Последние события
Get-Content catcam\pc\logs\events_*.jsonl | Select-Object -Last 20
```

### Через Watchdog

Watchdog автоматически:
- Перезапускает receiver если нет кадров > 5 сек
- Перезапускает streamer если FFmpeg процесс умер
- Логирует все действия в консоль

## Что делать если система упала

1. **Проверьте логи** в `logs/`
2. **Проверьте консоль** на ошибки
3. **Перезапустите вручную:**
   ```powershell
   cd catcam\pc
   python main.py
   ```

4. **Если проблема повторяется:**
   - Проверьте подключение к Pi (ping 192.168.1.103)
   - Проверьте что стрим активен на Pi
   - Проверьте место на диске (логи могут расти)

## Рекомендации для длительной работы

1. ✅ **Оставить PC включенным** (без спящего режима)
2. ✅ **Не закрывать окно preview** (можно свернуть)
3. ✅ **Периодически проверять логи** (раз в несколько часов)
4. ✅ **Настроить автозапуск** через Task Scheduler
5. ✅ **Мониторить место на диске** (логи растут)
6. ⚠️ **Для production лучше переключить в headless режим** (когда будет реализован)

## Текущие метрики (из вашего запуска)

```
[System] FPS стрима: 25.9-35.8  ✓ Нормально
Receiver FPS: 27-62              ✓ Нормально
Infer FPS: 2.1-7.6               ✓ Нормально (AI работает с интервалом)
```

Все метрики в норме! Система готова к работе.

