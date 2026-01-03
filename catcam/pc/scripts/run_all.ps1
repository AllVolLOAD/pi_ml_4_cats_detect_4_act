# Скрипт запуска всех компонентов CatCam системы
# Использование: .\run_all.ps1 [--stage1|--stage2|--stage3]

param(
    [switch]$Stage1,  # Только receiver + streamer (фиксированная рамка)
    [switch]$Stage2,  # AI детектор отдельно (тест)
    [switch]$Stage3   # Полная система (receiver + AI + streamer)
)

# Если не указан этап, используем Stage3 (полная система)
if (-not $Stage1 -and -not $Stage2 -and -not $Stage3) {
    $Stage3 = $true
}

# Путь к директории скрипта
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PcDir = Split-Path -Parent $ScriptDir
Set-Location $PcDir

# Проверка конфигурации
if (-not (Test-Path "config.yaml")) {
    Write-Host "Ошибка: config.yaml не найден!" -ForegroundColor Red
    exit 1
}

# Проверка FFmpeg
$ffmpegCheck = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpegCheck) {
    Write-Host "Ошибка: FFmpeg не найден в PATH!" -ForegroundColor Red
    Write-Host "Установите FFmpeg: https://ffmpeg.org/download.html" -ForegroundColor Yellow
    exit 1
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "CatCam System Launcher" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Этап 1: Receiver + Streamer (фиксированная рамка)
if ($Stage1) {
    Write-Host "Запуск Этапа 1: Receiver + Streamer (фиксированная рамка)" -ForegroundColor Green
    Write-Host ""
    
    # Запуск Receiver
    Write-Host "Запуск Receiver..." -ForegroundColor Yellow
    Start-Process python -ArgumentList "receiver.py" -WindowStyle Normal
    
    Start-Sleep -Seconds 2
    
    # Запуск Streamer
    Write-Host "Запуск Streamer..." -ForegroundColor Yellow
    Start-Process python -ArgumentList "streamer.py" -WindowStyle Normal
    
    Write-Host ""
    Write-Host "Компоненты запущены. Нажмите любую клавишу для остановки..." -ForegroundColor Green
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    
    # Остановка процессов
    Get-Process python | Where-Object { $_.Path -like "*catcam*" } | Stop-Process -Force
}

# Этап 2: AI Detector (тест)
elseif ($Stage2) {
    Write-Host "Запуск Этапа 2: AI Detector (тестовый режим)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Использование:" -ForegroundColor Yellow
    Write-Host "  python ai_detector.py --image path/to/image.jpg" -ForegroundColor White
    Write-Host "  python ai_detector.py --camera 0" -ForegroundColor White
    Write-Host ""
    
    python ai_detector.py --help
}

# Этап 3: Полная система
elseif ($Stage3) {
    Write-Host "Запуск Этапа 3: Полная система (Receiver + AI + Streamer)" -ForegroundColor Green
    Write-Host ""
    
    # Запуск Receiver
    Write-Host "[1/3] Запуск Receiver..." -ForegroundColor Yellow
    $receiver = Start-Process python -ArgumentList "receiver.py" -WindowStyle Normal -PassThru
    
    Start-Sleep -Seconds 2
    
    # Запуск AI Detector
    Write-Host "[2/3] Запуск AI Detector..." -ForegroundColor Yellow
    $aiDetector = Start-Process python -ArgumentList "ai_detector.py", "--udp" -WindowStyle Normal -PassThru
    
    Start-Sleep -Seconds 2
    
    # Запуск Streamer
    Write-Host "[3/3] Запуск Streamer..." -ForegroundColor Yellow
    $streamer = Start-Process python -ArgumentList "streamer.py", "--use-ai" -WindowStyle Normal -PassThru
    
    Write-Host ""
    Write-Host "Все компоненты запущены!" -ForegroundColor Green
    Write-Host "Нажмите Ctrl+C для остановки всех процессов..." -ForegroundColor Yellow
    Write-Host ""
    
    try {
        # Ожидание завершения или прерывания
        Wait-Process -Id $receiver.Id, $aiDetector.Id, $streamer.Id -ErrorAction SilentlyContinue
    }
    catch {
        Write-Host "Остановка процессов..." -ForegroundColor Yellow
        Stop-Process -Id $receiver.Id, $aiDetector.Id, $streamer.Id -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "Завершено." -ForegroundColor Cyan

