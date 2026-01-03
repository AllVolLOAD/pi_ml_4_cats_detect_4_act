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
Write-Host ""

# Windows не имеет ssh-copy-id, используем альтернативный метод
$publicKey = Get-Content $sshKeyPath -Raw
$publicKey = $publicKey.Trim()

Write-Host "Используйте один из способов ниже:" -ForegroundColor Cyan
Write-Host ""

# Способ 1: Автоматический (требует ввода пароля)
Write-Host "Способ 1: Автоматический (рекомендуется)" -ForegroundColor Yellow
Write-Host "Выполните следующую команду и введите пароль:" -ForegroundColor White
Write-Host ""
Write-Host "  type `"$sshKeyPath`" | ssh $PiHost `"mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys`"" -ForegroundColor Gray
Write-Host ""

$choice = Read-Host "Выполнить автоматическое копирование сейчас? (y/n)"

if ($choice -eq 'y' -or $choice -eq 'Y') {
    Write-Host ""
    Write-Host "Выполнение команды (введите пароль когда будет запрошен)..." -ForegroundColor Yellow
    Write-Host ""
    
    # Используем Get-Content и передаем через pipe
    Get-Content $sshKeyPath | & ssh $PiHost "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
    
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
        Write-Host "Используйте способ 2 (ручной) ниже" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "Пропущено автоматическое копирование" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Способ 2: Ручной (если автоматический не сработал)" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Скопируйте содержимое публичного ключа:" -ForegroundColor White
Write-Host "   notepad `"$sshKeyPath`"" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Подключитесь к малине:" -ForegroundColor White
Write-Host "   ssh $PiHost" -ForegroundColor Gray
Write-Host ""
Write-Host "3. На малине выполните:" -ForegroundColor White
Write-Host "   mkdir -p ~/.ssh" -ForegroundColor Gray
Write-Host "   chmod 700 ~/.ssh" -ForegroundColor Gray
Write-Host "   nano ~/.ssh/authorized_keys" -ForegroundColor Gray
Write-Host "   # Вставьте содержимое публичного ключа и сохраните (Ctrl+X, Y, Enter)" -ForegroundColor Gray
Write-Host "   chmod 600 ~/.ssh/authorized_keys" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Проверьте подключение:" -ForegroundColor White
Write-Host "   ssh $PiHost" -ForegroundColor Gray
Write-Host "   # Должно подключиться без пароля" -ForegroundColor Gray

