# Разметка видео
param(
    [Parameter(Mandatory=$true)]
    [string]$Video,
    
    [string]$Output
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PcDir = Split-Path -Parent $ScriptDir
Set-Location $PcDir

if (-not $Output) {
    $VideoName = [System.IO.Path]::GetFileNameWithoutExtension($Video)
    $Output = "../data/annotations/${VideoName}.json"
}

Write-Host "Разметка видео: $Video" -ForegroundColor Cyan
Write-Host "Выходной файл: $Output" -ForegroundColor Yellow

python annotator.py $Video $Output

