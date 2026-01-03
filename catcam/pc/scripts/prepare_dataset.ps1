# Подготовка датасета
param(
    [string]$Annotations = "../data/annotations",
    [string]$Videos = "../data/raw_videos",
    [string]$Output = "../data/dataset"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PcDir = Split-Path -Parent $ScriptDir
Set-Location $PcDir

Write-Host "Подготовка датасета" -ForegroundColor Cyan
Write-Host "Аннотации: $Annotations" -ForegroundColor Yellow
Write-Host "Видео: $Videos" -ForegroundColor Yellow
Write-Host "Выход: $Output" -ForegroundColor Yellow

python dataset_prep.py --annotations $Annotations --videos $Videos --output $Output

