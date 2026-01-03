param(
    [string]$SourceDir = "C:\NOSYS-WORK\rasberi_pi4modB\catcam\pc",
    [string]$TargetDir = "C:\NOSYS-USER\catcam\catcam\pc"
)

Write-Host "Копирование файлов на второй PC..." -ForegroundColor Cyan
Write-Host "Источник: $SourceDir" -ForegroundColor Gray
Write-Host "Назначение: $TargetDir" -ForegroundColor Gray
Write-Host ""

# Проверяем существование исходной директории
if (-not (Test-Path $SourceDir)) {
    Write-Host "❌ Исходная директория не найдена: $SourceDir" -ForegroundColor Red
    exit 1
}

# Проверяем/создаем целевую директорию
if (-not (Test-Path $TargetDir)) {
    Write-Host "📁 Создание целевой директории: $TargetDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

# Файлы для копирования
$filesToCopy = @(
    "main.py",
    "config.yaml"
)

foreach ($file in $filesToCopy) {
    $sourcePath = Join-Path $SourceDir $file
    $targetPath = Join-Path $TargetDir $file
    
    if (-not (Test-Path $sourcePath)) {
        Write-Host "⚠️  Файл не найден: $sourcePath" -ForegroundColor Yellow
        continue
    }
    
    Write-Host "📤 Копирование: $file -> $targetPath" -ForegroundColor Green
    Copy-Item $sourcePath $targetPath -Force
    
    if (Test-Path $targetPath) {
        Write-Host "✅ Успешно скопирован: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ Ошибка копирования: $file" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "Готово!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Проверка обновленного config.yaml:" -ForegroundColor Cyan
$configPath = Join-Path $TargetDir "config.yaml"
if (Test-Path $configPath) {
    $timeout = Select-String -Path $configPath -Pattern "receiver_timeout_sec: 10.0" | Select-Object -First 1
    if ($timeout) {
        Write-Host "✅ receiver_timeout_sec: 10.0 найден в config.yaml" -ForegroundColor Green
    } else {
        Write-Host "⚠️  receiver_timeout_sec: 10.0 не найден - возможно старый config" -ForegroundColor Yellow
    }
}

