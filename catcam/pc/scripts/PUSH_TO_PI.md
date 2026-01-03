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

## Настройка SSH ключей (для автоматического запуска сервиса)

Для автоматического запуска сервиса на малине нужен SSH доступ без пароля.

### Автоматическая настройка:

```powershell
.\scripts\setup_ssh_keys.ps1
```

Скрипт:
1. Создаст SSH ключ (если еще нет)
2. Скопирует его на малину
3. Проверит подключение без пароля

### Ручная настройка:

1. **Генерация ключа** (если еще нет):
   ```powershell
   ssh-keygen -t rsa -b 4096
   ```
   Нажмите Enter для значений по умолчанию.

2. **Копирование ключа на малину**:
   ```powershell
   # Windows не имеет ssh-copy-id, используем альтернативный способ:
   type $env:USERPROFILE\.ssh\id_rsa.pub | ssh mlprojectcat@192.168.1.103 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
   ```
   Введите пароль когда будет запрошен.

3. **Проверка**:
   ```powershell
   ssh mlprojectcat@192.168.1.103 "echo 'OK'"
   ```
   Должно подключиться без пароля.

## Важно

- **config.yaml** может быть локальным на малине - проверьте, нужно ли его обновлять
- После обновления `main.py` может потребоваться перезапуск сервиса на малине
- Путь на малине: `/home/mlprojectcat/catcam/pc/`
- Для автоматического запуска сервиса нужен SSH доступ без пароля (настроить SSH ключи)
- Если SSH ключи не настроены, скрипт покажет инструкции по настройке

