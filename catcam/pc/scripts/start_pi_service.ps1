param(
    [string]$PiHost = "mlprojectcat@192.168.1.103",
    [string]$ServiceName = "cam-stream-record.service"
)

Write-Host "Запуск сервиса на Raspberry Pi..." -ForegroundColor Cyan
Write-Host "Host: $PiHost" -ForegroundColor Gray
Write-Host "Service: $ServiceName" -ForegroundColor Gray
Write-Host ""

# Проверяем, настроены ли SSH ключи (пробуем подключиться без пароля)
Write-Host "🔐 Проверка SSH подключения..." -ForegroundColor Yellow
$testConnection = & ssh -o BatchMode=yes -o ConnectTimeout=5 $PiHost "echo 'OK'" 2>&1

if ($LASTEXITCODE -ne 0 -or $testConnection -notmatch "OK") {
    Write-Host "⚠️  SSH ключи не настроены или требуется пароль" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Для автоматического запуска сервиса нужно настроить SSH ключи:" -ForegroundColor Cyan
    Write-Host "1. Генерация ключа (если еще нет):" -ForegroundColor White
    Write-Host "   ssh-keygen -t rsa -b 4096" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Копирование ключа на малину:" -ForegroundColor White
    Write-Host "   ssh-copy-id $PiHost" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Или запустите сервис вручную на малине:" -ForegroundColor Cyan
    Write-Host "   ssh $PiHost" -ForegroundColor Gray
    Write-Host "   sudo systemctl start $ServiceName" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

# Проверка статуса перед запуском
Write-Host "📊 Текущий статус сервиса:" -ForegroundColor Yellow
& ssh -o BatchMode=yes $PiHost "sudo systemctl status $ServiceName --no-pager -l | head -n 10" 2>&1
Write-Host ""

# Остановка сервиса (если запущен)
Write-Host "⏹️  Остановка сервиса (если запущен)..." -ForegroundColor Yellow
& ssh -o BatchMode=yes $PiHost "sudo systemctl stop $ServiceName" 2>&1 | Out-Null

# Небольшая задержка
Start-Sleep -Seconds 2

# Запуск сервиса
Write-Host "▶️  Запуск сервиса..." -ForegroundColor Green
$result = & ssh -o BatchMode=yes $PiHost "sudo systemctl start $ServiceName" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Сервис запущен успешно" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Статус сервиса:" -ForegroundColor Cyan
    & ssh -o BatchMode=yes $PiHost "sudo systemctl status $ServiceName --no-pager -l | head -n 15" 2>&1
} else {
    Write-Host "❌ Ошибка запуска сервиса" -ForegroundColor Red
    if ($result) {
        Write-Host "Детали: $result" -ForegroundColor Red
    }
    exit 1
}

