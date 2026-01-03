param(
    [string]$PiHost = "mlprojectcat@192.168.1.103"
)

Write-Host "Настройка SSH ключей для автоматического подключения к малине" -ForegroundColor Cyan
Write-Host ""

# Проверяем, есть ли уже ключ
$sshKeyPath = "$env:USERPROFILE\.ssh\id_rsa.pub"
$sshKeyExists = Test-Path $sshKeyPath

if (-not $sshKeyExists) {
    Write-Host "🔑 Генерация SSH ключа..." -ForegroundColor Yellow
    Write-Host "Нажмите Enter для использования значений по умолчанию" -ForegroundColor Gray
    ssh-keygen -t rsa -b 4096 -f "$env:USERPROFILE\.ssh\id_rsa" -N '""'
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Ошибка генерации ключа" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ SSH ключ создан" -ForegroundColor Green
} else {
    Write-Host "✅ SSH ключ уже существует: $sshKeyPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "📤 Копирование ключа на малину..." -ForegroundColor Yellow
Write-Host "Введите пароль для $PiHost когда будет запрошен" -ForegroundColor Gray
Write-Host ""

# Windows не имеет ssh-copy-id, используем альтернативный метод
$publicKey = Get-Content $sshKeyPath
$tempScript = "$env:TEMP\ssh_copy_key.sh"

# Создаем временный скрипт для копирования ключа
@"
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo '$publicKey' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
echo 'SSH ключ успешно добавлен'
"@ | Out-File -FilePath $tempScript -Encoding ASCII

# Копируем скрипт на малину и выполняем
Write-Host "Выполнение на малине (требуется пароль)..." -ForegroundColor Yellow
scp $tempScript "${PiHost}:/tmp/ssh_copy_key.sh" 2>&1 | Out-Host
ssh $PiHost "bash /tmp/ssh_copy_key.sh && rm /tmp/ssh_copy_key.sh" 2>&1 | Out-Host

Remove-Item $tempScript -ErrorAction SilentlyContinue

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ SSH ключ успешно скопирован на малину!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Проверка подключения без пароля..." -ForegroundColor Cyan
    $test = & ssh -o BatchMode=yes -o ConnectTimeout=5 $PiHost "echo 'OK'" 2>&1
    if ($test -match "OK") {
        Write-Host "✅ Подключение без пароля работает!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Подключение без пароля не работает, проверьте настройки" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "❌ Ошибка копирования ключа" -ForegroundColor Red
    Write-Host ""
    Write-Host "Альтернативный способ (выполните вручную):" -ForegroundColor Cyan
    Write-Host "1. Скопируйте содержимое файла: $sshKeyPath" -ForegroundColor White
    Write-Host "2. Подключитесь к малине: ssh $PiHost" -ForegroundColor White
    Write-Host "3. Выполните:" -ForegroundColor White
    Write-Host "   mkdir -p ~/.ssh" -ForegroundColor Gray
    Write-Host "   chmod 700 ~/.ssh" -ForegroundColor Gray
    Write-Host "   echo 'ВАШ_ПУБЛИЧНЫЙ_КЛЮЧ' >> ~/.ssh/authorized_keys" -ForegroundColor Gray
    Write-Host "   chmod 600 ~/.ssh/authorized_keys" -ForegroundColor Gray
}

