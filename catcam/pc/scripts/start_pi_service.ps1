param(
    [string]$PiHost = "mlprojectcat@192.168.1.103",
    [string]$ServiceName = "cam-stream-record.service"
)

Write-Host "Запуск сервиса на Raspberry Pi..." -ForegroundColor Cyan
Write-Host "Host: $PiHost" -ForegroundColor Gray
Write-Host "Service: $ServiceName" -ForegroundColor Gray
Write-Host ""

# Проверка статуса перед запуском
Write-Host "📊 Текущий статус сервиса:" -ForegroundColor Yellow
& ssh $PiHost "sudo systemctl status $ServiceName --no-pager -l | head -n 10"
Write-Host ""

# Остановка сервиса (если запущен)
Write-Host "⏹️  Остановка сервиса (если запущен)..." -ForegroundColor Yellow
& ssh $PiHost "sudo systemctl stop $ServiceName" 2>&1 | Out-Null

# Небольшая задержка
Start-Sleep -Seconds 2

# Запуск сервиса
Write-Host "▶️  Запуск сервиса..." -ForegroundColor Green
& ssh $PiHost "sudo systemctl start $ServiceName"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Сервис запущен успешно" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Статус сервиса:" -ForegroundColor Cyan
    & ssh $PiHost "sudo systemctl status $ServiceName --no-pager -l | head -n 15"
} else {
    Write-Host "❌ Ошибка запуска сервиса" -ForegroundColor Red
    exit 1
}

