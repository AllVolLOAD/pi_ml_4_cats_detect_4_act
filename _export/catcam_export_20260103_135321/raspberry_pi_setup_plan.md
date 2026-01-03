# План подготовки Raspberry Pi для тестирования камер

## Цель
Подготовить рабочую среду на Raspberry Pi 4 для тестирования записи с USB камер

## Задачи

1. Архивировать текущие boot файлы
2. Создать структуру проекта для тестирования на Pi
3. Создать тестовый скрипт для USB камер
4. Документировать утилиты для оптимизации Raspberry Pi OS

## Структура проекта

```
.
├── boot_backup/                  # Архивированные boot файлы (zip архив)
├── raspberry_pi/                 # Код для Raspberry Pi
│   ├── camera_test.py            # Тестовый скрипт для USB камер
│   ├── list_cameras.py           # Утилита для обнаружения камер
│   ├── optimize_pi.sh            # Скрипт автоматической оптимизации Pi
│   ├── requirements.txt          # Python зависимости
│   └── README.md                 # Инструкции для Pi
└── README.md                     # Основная документация проекта
```

## Утилиты для оптимизации Raspberry Pi OS

### Встроенные утилиты

**raspi-config** (основная утилита конфигурации):
```bash
sudo raspi-config
```
- **Performance Options → Overclock**: повышение частоты CPU/GPU
- **Advanced Options → Memory Split**: увеличить GPU память (128-256 для камер)
- **System Options → Boot / Auto Login**: отключить GUI, включить Console Autologin
- **Interface Options**: отключить ненужные интерфейсы (Bluetooth, SPI, I2C если не используются)

**rpi-update** (обновление прошивки):
```bash
sudo rpi-update
```

### Отключение ненужных сервисов (улучшение отзывчивости)

```bash
# Отключить Bluetooth
sudo systemctl disable bluetooth
sudo systemctl stop bluetooth

# Отключить WiFi power management
sudo systemctl disable wifi-powersave
sudo iwconfig wlan0 power off

# Отключить avahi-daemon (mDNS)
sudo systemctl disable avahi-daemon
sudo systemctl stop avahi-daemon

# Отключить ненужные пакеты (если установлены)
sudo systemctl disable wolfram-engine
sudo systemctl disable libreoffice

# Отключить swap (если достаточно RAM)
sudo dphys-swapfile swapoff
sudo systemctl disable dphys-swapfile
```

### Оптимизация USB и камер

```bash
# Установка утилит для работы с USB камерами
sudo apt update
sudo apt install -y v4l-utils usbutils

# Проверка доступных камер
v4l2-ctl --list-devices
lsusb

# Отключение USB autosuspend (создать файл /etc/udev/rules.d/90-usb-power.rules)
echo 'ACTION=="add", SUBSYSTEM=="usb", TEST=="power/control", ATTR{power/control}="on"' | sudo tee /etc/udev/rules.d/90-usb-power.rules
sudo udevadm control --reload-rules
```

### Уменьшение безопасности (только для разработки!)

**Отключение firewall:**
```bash
sudo ufw disable
# или
sudo systemctl stop ufw
sudo systemctl disable ufw
```

**Упрощение SSH (для удобства разработки):**
```bash
sudo nano /etc/ssh/sshd_config
# Раскомментировать или добавить:
# PasswordAuthentication yes
# PermitRootLogin yes (опционально)
sudo systemctl restart ssh
```

**Отключение SELinux/AppArmor (если установлены):**
```bash
# AppArmor обычно не установлен на Raspberry Pi OS, но если есть:
sudo systemctl stop apparmor
sudo systemctl disable apparmor
```

### Оптимизация config.txt (в /boot/config.txt на Pi)

Добавить/изменить следующие параметры:

```
# Увеличить GPU память для камер
gpu_mem=128

# Overclock CPU (Pi 4)
arm_freq=2000
over_voltage=6

# Overclock GPU
gpu_freq=750

# Улучшить производительность USB
dtoverlay=vc4-kms-v3d
max_usb_current=1

# Отключить компрессию логов
boot_delay=0
```

### Дополнительные утилиты для мониторинга и оптимизации

**Установка полезных утилит:**
```bash
# Мониторинг системы
sudo apt install -y htop iotop nethogs

# Мониторинг температуры
sudo apt install -y vcgencmd

# Оптимизация файловой системы
sudo apt install -y preload  # предзагрузка часто используемых программ
```

**Настройка tmpfs для временных файлов (уменьшение записи на SD карту):**
Добавить в `/etc/fstab`:
```
tmpfs /tmp tmpfs defaults,noatime,nosuid,size=100m 0 0
tmpfs /var/tmp tmpfs defaults,noatime,nosuid,size=30m 0 0
tmpfs /var/log tmpfs defaults,noatime,nosuid,size=100m 0 0
```

**Увеличение файловых дескрипторов (для работы с несколькими камерами):**
Добавить в `/etc/security/limits.conf`:
```
* soft nofile 65536
* hard nofile 65536
```

### Специфичные оптимизации для работы с камерами

```bash
# Увеличить размер буфера USB
echo 'vm.usbcore.usbfs_memory_mb=1000' | sudo tee -a /etc/sysctl.conf

# Оптимизация сетевых настроек (если передача по сети)
echo 'net.core.rmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 16777216' | sudo tee -a /etc/sysctl.conf

# Применить изменения
sudo sysctl -p
```

### Скрипт автоматической оптимизации

Создать скрипт `optimize_pi.sh` который выполнит основные оптимизации автоматически (см. raspberry_pi/optimize_pi.sh)
