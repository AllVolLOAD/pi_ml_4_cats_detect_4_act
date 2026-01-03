param(
    [string]$PiHost = "mlprojectcat@192.168.1.103",
    [string]$ServiceName = "cam-stream-record.service"
)

Write-Host "Starting service on Raspberry Pi..." -ForegroundColor Cyan
Write-Host "Host: $PiHost" -ForegroundColor Gray
Write-Host "Service: $ServiceName" -ForegroundColor Gray
Write-Host ""

# Check if SSH keys are configured (try to connect without password)
Write-Host "Checking SSH connection..." -ForegroundColor Yellow
$testConnection = & ssh -o BatchMode=yes -o ConnectTimeout=5 $PiHost "echo 'OK'" 2>&1

if ($LASTEXITCODE -ne 0 -or $testConnection -notmatch "OK") {
    Write-Host "WARNING: SSH keys not configured or password required" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To enable automatic service start, configure SSH keys:" -ForegroundColor Cyan
    Write-Host "1. Generate key (if not exists):" -ForegroundColor White
    Write-Host "   ssh-keygen -t rsa -b 4096" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Copy key to Pi:" -ForegroundColor White
    Write-Host "   ssh-copy-id $PiHost" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Or start service manually on Pi:" -ForegroundColor Cyan
    Write-Host "   ssh $PiHost" -ForegroundColor Gray
    Write-Host "   sudo systemctl start $ServiceName" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

# Check status before starting
Write-Host "Current service status:" -ForegroundColor Yellow
& ssh -o BatchMode=yes $PiHost "sudo systemctl status $ServiceName --no-pager -l | head -n 10" 2>&1
Write-Host ""

# Stop service (if running)
Write-Host "Stopping service (if running)..." -ForegroundColor Yellow
& ssh -o BatchMode=yes $PiHost "sudo systemctl stop $ServiceName" 2>&1 | Out-Null

# Small delay
Start-Sleep -Seconds 2

# Start service
Write-Host "Starting service..." -ForegroundColor Green
$result = & ssh -o BatchMode=yes $PiHost "sudo systemctl start $ServiceName" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "Service started successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "Service status:" -ForegroundColor Cyan
    & ssh -o BatchMode=yes $PiHost "sudo systemctl status $ServiceName --no-pager -l | head -n 15" 2>&1
} else {
    Write-Host "ERROR: Failed to start service" -ForegroundColor Red
    if ($result) {
        Write-Host "Details: $result" -ForegroundColor Red
    }
    exit 1
}

