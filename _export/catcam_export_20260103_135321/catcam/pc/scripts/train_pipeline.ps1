# Полный пайплайн обучения (с паузами для ручной работы)
param(
    [switch]$SkipCollect,
    [switch]$SkipAnnotate,
    [switch]$SkipPrep,
    [switch]$SkipTrain
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PcDir = Split-Path -Parent $ScriptDir
Set-Location $ScriptDir

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Пайплайн обучения модели" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Сбор данных
if (-not $SkipCollect) {
    Write-Host "[1/4] Сбор данных..." -ForegroundColor Green
    Write-Host "Записываю 1 час видео, сегменты по 60 секунд" -ForegroundColor Yellow
    .\collect_data.ps1 -Duration 3600 -Segment 60
    Write-Host ""
    Write-Host "Сбор данных завершен. Видео в: ..\data\raw_videos\" -ForegroundColor Green
    Write-Host ""
}

# 2. Разметка (ручная) - пропускаем автоматически, инструкция
if (-not $SkipAnnotate) {
    Write-Host "[2/4] Разметка видео (РУЧНАЯ РАБОТА)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Нужно разметить видео файлы вручную." -ForegroundColor Yellow
    Write-Host "Для каждого видео запустите:" -ForegroundColor Yellow
    Write-Host "  .\annotate.ps1 -Video `"..\data\raw_videos\<имя_видео>.mp4`"" -ForegroundColor White
    Write-Host ""
    Write-Host "В окне разметки:" -ForegroundColor Yellow
    Write-Host "  - Мышь: рисуй рамку вокруг кота" -ForegroundColor White
    Write-Host "  - 1/2/3/4: выбор класса (eating/drinking/playing/sleeping)" -ForegroundColor White
    Write-Host "  - Space: следующий кадр" -ForegroundColor White
    Write-Host "  - S: сохранить, Q: выход" -ForegroundColor White
    Write-Host ""
    Write-Host "Разметьте минимум 3-5 видео для начала." -ForegroundColor Yellow
    Write-Host "Нажмите Enter когда закончите разметку..." -ForegroundColor Cyan
    Read-Host
    Write-Host ""
}

# 3. Подготовка датасета
if (-not $SkipPrep) {
    Write-Host "[3/4] Подготовка датасета..." -ForegroundColor Green
    Write-Host "Конвертирую аннотации в YOLO формат..." -ForegroundColor Yellow
    .\prepare_dataset.ps1
    Write-Host ""
}

# 4. Обучение
if (-not $SkipTrain) {
    Write-Host "[4/4] Обучение модели..." -ForegroundColor Green
    Write-Host "Это займет время (зависит от данных и GPU)..." -ForegroundColor Yellow
    .\train_model.ps1 -Model n -Epochs 100 -Batch 16
    Write-Host ""
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Готово!" -ForegroundColor Green
Write-Host "Модель: ..\data\models\cat_activity\weights\best.pt" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

