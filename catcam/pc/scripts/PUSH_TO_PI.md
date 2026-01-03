# Инструкция: Отправка файлов на Raspberry Pi

## Что нужно отправить

После изменений в коде на PC нужно отправить на малину:

1. **`main.py`** - обновленный код с исправлениями watchdog и обработки видео
2. **`config.yaml`** - обновленный конфиг (если изменялся)

**Важно:** Путь на малине: `/home/mlprojectcat/catcam/pc/`

## Способ 1: Использовать скрипт (рекомендуется)

Из папки `catcam/pc/`:

```powershell
.\scripts\push_to_pi.ps1
```

С автоматическим запуском сервиса на малине:

```powershell
.\scripts\push_to_pi.ps1 -StartService
```

Или с параметрами:

```powershell
.\scripts\push_to_pi.ps1 -PiHost "mlprojectcat@192.168.1.103" -RemoteDir "/home/mlprojectcat/catcam/pc" -StartService
```

## Способ 2: Вручную через SCP

### Отправка main.py:

```powershell
scp catcam\pc\main.py mlprojectcat@192.168.1.103:/home/mlprojectcat/catcam/pc/main.py
```

### Отправка config.yaml:

```powershell
scp catcam\pc\config.yaml mlprojectcat@192.168.1.103:/home/mlprojectcat/catcam/pc/config.yaml
```

### Запуск сервиса на малине (отдельно):

```powershell
.\scripts\start_pi_service.ps1
```

## Способ 3: Через SSH и git pull (если на малине есть git)

Если на малине настроен git и репозиторий:

```bash
ssh mlprojectcat@192.168.1.103
cd ~/catcam/pc
git pull
```

## Проверка после отправки

После отправки файлов на малине можно проверить:

```bash
ssh mlprojectcat@192.168.1.103
cd ~/catcam/pc
ls -la main.py config.yaml
```

## Автоматический запуск сервиса на малине

Теперь при запуске `main.py` на PC автоматически запускается сервис на малине (если включено в `config.yaml`):

```yaml
pi_service:
  enabled: true  # автоматически запускать сервис на малине при старте
  pi_host: "mlprojectcat@192.168.1.103"
  service_name: "cam-stream-record.service"
```

Это означает, что после запуска `python main.py` на PC:
1. Автоматически запустится сервис `cam-stream-record.service` на малине
2. PC подключится к SRT потоку от малины
3. Начнется обработка видео

## Важно

- **config.yaml** может быть локальным на малине - проверьте, нужно ли его обновлять
- После обновления `main.py` может потребоваться перезапуск сервиса на малине
- Путь на малине: `/home/mlprojectcat/catcam/pc/`
- Для автоматического запуска сервиса нужен SSH доступ без пароля (настроить SSH ключи) или вводить пароль вручную

