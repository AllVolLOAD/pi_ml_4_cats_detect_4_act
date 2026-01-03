# Сбор данных для обучения
param(
    [int]$Duration = 3600,
    [int]$Segment = 60,
    [string]$Output = "../data/raw_videos"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PcDir = Split-Path -Parent $ScriptDir
Set-Location $PcDir

Write-Host "Сбор данных для обучения" -ForegroundColor Cyan
Write-Host "Длительность: $Duration сек, Сегменты: $Segment сек" -ForegroundColor Yellow

python data_collector.py --duration $Duration --segment $Segment --output $Output

