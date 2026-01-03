# Скрипт для поиска Raspberry Pi в сети
# Сканирует диапазон IP адресов и ищет устройства с открытым SSH портом
# Использование: .\scripts\find_pi.ps1 [NETWORK_BASE]

param(
    [string]$NetworkBase = "192.168.1"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Поиск Raspberry Pi в сети" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Сканирую диапазон: $NetworkBase.1-254" -ForegroundColor Yellow
Write-Host "Это может занять 1-2 минуты..." -ForegroundColor Yellow
Write-Host ""

$found_devices = @()

# Сканирование диапазона
1..254 | ForEach-Object {
    $ip = "$NetworkBase.$_"
    Write-Host -NoNewline "Проверяю $ip...`r" -ForegroundColor Gray
    
    # Быстрый ping
    $ping_result = Test-Connection -ComputerName $ip -Count 1 -Quiet -ErrorAction SilentlyContinue
    
    if ($ping_result) {
        Write-Host "✓ Найден активный хост: $ip" -ForegroundColor Green
        
        # Проверка SSH порта
        try {
            $ssh_result = Test-NetConnection -ComputerName $ip -Port 22 -WarningAction SilentlyContinue -ErrorAction Stop
            if ($ssh_result.TcpTestSucceeded) {
                Write-Host "  → SSH порт открыт!" -ForegroundColor Cyan
                $found_devices += @{
                    IP = $ip
                    SSH = $true
                }
            } else {
                Write-Host "  → Хост активен, но SSH недоступен" -ForegroundColor Yellow
                $found_devices += @{
                    IP = $ip
                    SSH = $false
                }
            }
        } catch {
            # Игнорируем ошибки проверки порта
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Результаты поиска:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($found_devices.Count -eq 0) {
    Write-Host "Raspberry Pi не найдена в сети $NetworkBase.0/24" -ForegroundColor Red
    Write-Host ""
    Write-Host "Возможные причины:" -ForegroundColor Yellow
    Write-Host "  - Pi выключена" -ForegroundColor White
    Write-Host "  - Проблемы с питанием" -ForegroundColor White
    Write-Host "  - Кабель Ethernet не подключен" -ForegroundColor White
    Write-Host "  - Pi в другой подсети" -ForegroundColor White
    Write-Host "  - SSH отключен" -ForegroundColor White
    Write-Host ""
    Write-Host "Попробуйте:" -ForegroundColor Yellow
    Write-Host "  1. Проверить физическое подключение Pi" -ForegroundColor White
    Write-Host "  2. Проверить блок питания" -ForegroundColor White
    Write-Host "  3. Подключить монитор и клавиатуру к Pi" -ForegroundColor White
    Write-Host "  4. Проверить другой диапазон сети (например 192.168.0.x)" -ForegroundColor White
} else {
    $ssh_devices = $found_devices | Where-Object { $_.SSH -eq $true }
    
    if ($ssh_devices.Count -gt 0) {
        Write-Host "Найдены устройства с SSH:" -ForegroundColor Green
        foreach ($device in $ssh_devices) {
            Write-Host "  → $($device.IP)" -ForegroundColor Cyan
            Write-Host "    Команда подключения: ssh pi@$($device.IP)" -ForegroundColor White
        }
    } else {
        Write-Host "Найдены активные устройства, но SSH недоступен:" -ForegroundColor Yellow
        foreach ($device in $found_devices) {
            Write-Host "  → $($device.IP) (SSH закрыт)" -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host "Проверьте:" -ForegroundColor Yellow
        Write-Host "  - SSH включен на Pi? (sudo systemctl status ssh)" -ForegroundColor White
        Write-Host "  - Firewall не блокирует порт 22?" -ForegroundColor White
    }
}

Write-Host "========================================" -ForegroundColor Cyan

