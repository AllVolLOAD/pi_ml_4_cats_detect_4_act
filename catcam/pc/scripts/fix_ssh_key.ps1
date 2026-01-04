# Скрипт для правильной настройки SSH ключа на малине
param(
    [string]$PiHost = "mlprojectcat@192.168.1.103"
)

Write-Host "Настройка SSH ключа для $PiHost" -ForegroundColor Cyan
Write-Host ""

# Проверяем наличие ключа
$keyPath = "$env:USERPROFILE\.ssh\id_rsa.pub"
if (-not (Test-Path $keyPath)) {
    Write-Host "Ошибка: SSH ключ не найден: $keyPath" -ForegroundColor Red
    Write-Host "Сначала выполните: ssh-keygen -t rsa -b 4096" -ForegroundColor Yellow
    exit 1
}

Write-Host "Читаем публичный ключ..." -ForegroundColor Gray
$publicKey = Get-Content $keyPath -Raw
$publicKey = $publicKey.Trim()

Write-Host "Копируем ключ на малину..." -ForegroundColor Yellow
Write-Host "Введите пароль для ${PiHost}:" -ForegroundColor Yellow

# Создаем временный скрипт на малине
$tempScript = @"
#!/bin/bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
# Проверяем, нет ли уже этого ключа
if ! grep -Fxq '$publicKey' ~/.ssh/authorized_keys 2>/dev/null; then
    echo '$publicKey' >> ~/.ssh/authorized_keys
    echo "Ключ добавлен"
else
    echo "Ключ уже существует"
fi
chmod 600 ~/.ssh/authorized_keys
echo "Готово"
"@

$tempFile = "$env:TEMP\ssh_setup_$(Get-Date -Format 'yyyyMMddHHmmss').sh"
$tempScript | Out-File -FilePath $tempFile -Encoding ASCII -NoNewline

try {
    # Копируем скрипт на малину
    Write-Host "`nКопирование скрипта на малину..." -ForegroundColor Gray
    $scpResult = scp $tempFile "${PiHost}:/tmp/ssh_setup.sh" 2>&1
    $scpResult | Out-Host
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Ошибка копирования скрипта" -ForegroundColor Red
        exit 1
    }
    
    # Выполняем скрипт на малине
    Write-Host "Выполнение скрипта на малине..." -ForegroundColor Gray
    $sshResult = ssh $PiHost "bash /tmp/ssh_setup.sh && rm /tmp/ssh_setup.sh" 2>&1
    $sshResult | Out-Host
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Ошибка выполнения скрипта" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "`nПроверка подключения без пароля..." -ForegroundColor Cyan
    $result = & ssh -o BatchMode=yes -o ConnectTimeout=5 $PiHost "echo 'OK'" 2>&1
    
    if ($LASTEXITCODE -eq 0 -and $result -eq "OK") {
        Write-Host "✓ SSH ключ настроен успешно! Подключение работает без пароля." -ForegroundColor Green
    } else {
        Write-Host "⚠ Подключение все еще требует пароль." -ForegroundColor Yellow
        Write-Host "Проверьте на малине:" -ForegroundColor Yellow
        Write-Host "  ssh $PiHost 'ls -la ~/.ssh/'" -ForegroundColor Gray
        Write-Host "  ssh $PiHost 'cat ~/.ssh/authorized_keys | wc -l'" -ForegroundColor Gray
    }
} finally {
    if (Test-Path $tempFile) {
        Remove-Item $tempFile -Force
    }
}

