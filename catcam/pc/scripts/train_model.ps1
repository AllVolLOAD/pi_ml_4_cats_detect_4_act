# Обучение модели
param(
    [string]$Model = "n",
    [int]$Epochs = 100,
    [int]$ImageSize = 640,
    [int]$Batch = 16,
    [string]$Data = "../data/dataset/data.yaml"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PcDir = Split-Path -Parent $ScriptDir
Set-Location $PcDir

Write-Host "Обучение модели YOLOv8" -ForegroundColor Cyan
Write-Host "Модель: yolov8$Model.pt" -ForegroundColor Yellow
Write-Host "Epochs: $Epochs" -ForegroundColor Yellow
Write-Host "Batch: $Batch" -ForegroundColor Yellow

python train.py --model $Model --epochs $Epochs --imgsz $ImageSize --batch $Batch --data $Data

