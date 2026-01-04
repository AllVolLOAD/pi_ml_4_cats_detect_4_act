# Создание SSH ключа без passphrase для автоматизации
param(
    [string]$KeyPath = "$env:USERPROFILE\.ssh\id_rsa"
)

Write-Host "Создание SSH ключа без passphrase..." -ForegroundColor Cyan
Write-Host ""

# Проверяем, существует ли ключ
if (Test-Path $KeyPath) {
    $backupPath = "${KeyPath}.backup.$(Get-Date -Format 'yyyyMMddHHmmss')"
    Write-Host "Существующий ключ будет сохранен в: $backupPath" -ForegroundColor Yellow
    Copy-Item $KeyPath $backupPath -Force
    Copy-Item "${KeyPath}.pub" "${backupPath}.pub" -Force
}

Write-Host "Создание нового ключа (нажмите Enter для всех вопросов)..." -ForegroundColor Yellow
Write-Host ""

# Создаем ключ без passphrase (используем -N "" для пустого passphrase)
$sshKeygenArgs = @(
    "-t", "rsa",
    "-b", "4096",
    "-f", $KeyPath,
    "-N", '""'  # Пустой passphrase
)

Start-Process -FilePath "ssh-keygen" -ArgumentList $sshKeygenArgs -Wait -NoNewWindow

if (Test-Path "${KeyPath}.pub") {
    Write-Host "`n✓ SSH ключ создан успешно!" -ForegroundColor Green
    Write-Host "Публичный ключ:" -ForegroundColor Gray
    Get-Content "${KeyPath}.pub" | Write-Host -ForegroundColor Gray
    Write-Host ""
    Write-Host "Теперь скопируйте ключ на малину:" -ForegroundColor Yellow
    Write-Host "  `$key = Get-Content `"${KeyPath}.pub`"" -ForegroundColor Gray
    Write-Host "  ssh mlprojectcat@192.168.1.103 `"mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '`$key' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys`"" -ForegroundColor Gray
} else {
    Write-Host "`n✗ Ошибка создания ключа" -ForegroundColor Red
    exit 1
}

