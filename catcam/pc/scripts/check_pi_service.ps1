# Проверка статуса сервиса на малине
param(
    [string]$PiHost = "mlprojectcat@192.168.1.103",
    [string]$ServiceName = "cam-stream-record.service"
)

Write-Host "Проверка сервиса на Raspberry Pi..." -ForegroundColor Cyan
Write-Host "Host: $PiHost" -ForegroundColor Gray
Write-Host "Service: $ServiceName" -ForegroundColor Gray
Write-Host ""

# Проверка статуса сервиса
Write-Host "Статус сервиса:" -ForegroundColor Yellow
ssh $PiHost "sudo systemctl status $ServiceName --no-pager" 2>&1

Write-Host "`nПроверка порта 9000 (SRT):" -ForegroundColor Yellow
ssh $PiHost "sudo netstat -tulpn | grep 9000" 2>&1

Write-Host "`nПоследние логи сервиса:" -ForegroundColor Yellow
ssh $PiHost "sudo journalctl -u $ServiceName -n 20 --no-pager" 2>&1

