# Скрипт архивации boot файлов Raspberry Pi в zip архив
# Создает архив со всеми boot файлами, исключая файлы проекта

$archiveName = "boot_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"
$tempDir = "boot_backup_temp"

Write-Host "Архивация boot файлов Raspberry Pi..." -ForegroundColor Green

# Создаем временную директорию
if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

# Копируем все файлы кроме .md, .git, .ps1 и директорий проекта
Get-ChildItem -File | Where-Object { 
    $_.Extension -ne ".md" -and 
    $_.Name -notlike ".git*" -and
    $_.Name -ne "archive_boot.ps1" -and
    $_.Name -ne "archive_boot.zip" -and
    $_.Extension -ne ".zip"
} | ForEach-Object {
    Copy-Item $_.FullName -Destination "$tempDir\" -Force
    Write-Host "  Скопирован: $($_.Name)" -ForegroundColor Gray
}

# Копируем папку overlays если существует
if (Test-Path "overlays") {
    Copy-Item -Path "overlays" -Destination "$tempDir\overlays" -Recurse -Force
    Write-Host "  Скопировано: overlays/" -ForegroundColor Gray
}

# Создаем zip архив
Write-Host "`nСоздание zip архива: $archiveName" -ForegroundColor Yellow
Compress-Archive -Path "$tempDir\*" -DestinationPath $archiveName -Force

# Удаляем временную директорию
Remove-Item $tempDir -Recurse -Force

Write-Host "`nАрхивация завершена!" -ForegroundColor Green
Write-Host "Архив создан: $archiveName" -ForegroundColor Cyan
Write-Host "`nТеперь можно удалить оригинальные boot файлы (кроме этого скрипта)" -ForegroundColor Yellow
