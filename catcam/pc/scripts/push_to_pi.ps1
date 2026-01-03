param(
    [string]$PiHost = "mlprojectcat@192.168.1.103",
    [string]$RemoteDir = "/home/mlprojectcat/catcam/pc",
    [string]$LocalDir = (Join-Path $PSScriptRoot ".."),
    [switch]$StartService
)

# Файлы для отправки
$filesToPush = @(
    "main.py",
    "config.yaml"
)

Write-Host "Отправка файлов на Raspberry Pi..." -ForegroundColor Cyan
Write-Host "Host: $PiHost" -ForegroundColor Gray
Write-Host "Remote: $RemoteDir" -ForegroundColor Gray
Write-Host ""

$LocalDir = (Resolve-Path -LiteralPath $LocalDir).Path

foreach ($file in $filesToPush) {
    $localPath = Join-Path $LocalDir $file
    
    if (-not (Test-Path -LiteralPath $localPath)) {
        Write-Host "⚠️  Файл не найден: $localPath" -ForegroundColor Yellow
        continue
    }
    
    $remotePath = "$RemoteDir/$file"
    Write-Host "📤 Отправка: $file -> $remotePath" -ForegroundColor Green
    
    & scp "$localPath" "${PiHost}:$remotePath"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Успешно отправлен: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ Ошибка отправки: $file" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "Готово!" -ForegroundColor Cyan

# Опционально: запуск сервиса на малине
if ($StartService) {
    Write-Host ""
    Write-Host "🚀 Запуск сервиса на малине..." -ForegroundColor Cyan
    & ssh $PiHost "sudo systemctl restart cam-stream-record.service"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Сервис запущен" -ForegroundColor Green
        Write-Host "Проверка статуса:" -ForegroundColor Gray
        & ssh $PiHost "sudo systemctl status cam-stream-record.service --no-pager -l"
    } else {
        Write-Host "❌ Ошибка запуска сервиса" -ForegroundColor Red
    }
}

