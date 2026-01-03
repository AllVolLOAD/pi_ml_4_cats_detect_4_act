# Скрипт проверки подключения к Raspberry Pi
# Использование: .\scripts\check_pi.ps1 [IP_ADDRESS]

param(
    [string]$PiIP = "192.168.1.101"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Проверка подключения к Raspberry Pi" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IP адрес: $PiIP" -ForegroundColor White
Write-Host ""

# 1. Ping проверка
Write-Host "[1/2] Ping проверка..." -ForegroundColor Yellow
try {
    $ping_result = Test-Connection -ComputerName $PiIP -Count 2 -Quiet -ErrorAction Stop
    if ($ping_result) {
        Write-Host "✓ Pi доступен по сети" -ForegroundColor Green
    } else {
        Write-Host "✗ Pi не отвечает на ping" -ForegroundColor Red
        Write-Host "  Проверьте:" -ForegroundColor Yellow
        Write-Host "  - Pi включен?" -ForegroundColor White
        Write-Host "  - Кабель/Wi-Fi подключен?" -ForegroundColor White
        Write-Host "  - IP адрес правильный?" -ForegroundColor White
        exit 1
    }
} catch {
    Write-Host "✗ Ошибка ping: $_" -ForegroundColor Red
    exit 1
}

# 2. SSH порт проверка
Write-Host ""
Write-Host "[2/2] Проверка SSH порта (22)..." -ForegroundColor Yellow
try {
    $ssh_result = Test-NetConnection -ComputerName $PiIP -Port 22 -WarningAction SilentlyContinue -ErrorAction Stop
    if ($ssh_result.TcpTestSucceeded) {
        Write-Host "✓ SSH порт открыт" -ForegroundColor Green
    } else {
        Write-Host "✗ SSH порт недоступен" -ForegroundColor Red
        Write-Host "  Проверьте:" -ForegroundColor Yellow
        Write-Host "  - SSH включен на Pi? (sudo systemctl status ssh)" -ForegroundColor White
        Write-Host "  - Firewall не блокирует порт 22?" -ForegroundColor White
    }
} catch {
    Write-Host "✗ Ошибка проверки SSH: $_" -ForegroundColor Red
}

# Итоговая информация
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Команда для подключения:" -ForegroundColor Cyan
Write-Host "  ssh pi@$PiIP" -ForegroundColor White
Write-Host "Или:" -ForegroundColor Cyan
Write-Host "  ssh mlprojectcat@$PiIP" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan

