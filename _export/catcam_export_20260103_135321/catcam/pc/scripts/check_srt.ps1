# Проверка подключения к SRT потоку
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PcDir = Split-Path -Parent $ScriptDir
Set-Location $PcDir

Write-Host "Проверка SRT подключения..." -ForegroundColor Cyan
Write-Host ""

python test_srt_manual.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Если стрим не запущен на Raspberry Pi:" -ForegroundColor Yellow
    Write-Host "  ssh pi@192.168.1.100" -ForegroundColor White
    Write-Host "  cd catcam/pi" -ForegroundColor White
    Write-Host "  ./stream_cam.sh" -ForegroundColor White
}

