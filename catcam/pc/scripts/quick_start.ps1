# Быстрый старт - показывает что делать по шагам

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Обучение модели - Быстрый старт" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Процесс обучения состоит из 4 этапов:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. СБОР ДАННЫХ" -ForegroundColor Green
Write-Host "   Записать видео с камеры" -ForegroundColor White
Write-Host "   Команда: .\scripts\collect_data.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "2. РАЗМЕТКА (ручная работа!)" -ForegroundColor Green
Write-Host "   Разметить каждое видео: рамки + классы" -ForegroundColor White
Write-Host "   Команда: .\scripts\annotate.ps1 -Video <путь>" -ForegroundColor Gray
Write-Host "   Нужно разметить 3-5+ видео минимум" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. ПОДГОТОВКА ДАТАСЕТА" -ForegroundColor Green
Write-Host "   Конвертация в формат для обучения" -ForegroundColor White
Write-Host "   Команда: .\scripts\prepare_dataset.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "4. ОБУЧЕНИЕ" -ForegroundColor Green
Write-Host "   Обучить модель YOLOv8" -ForegroundColor White
Write-Host "   Команда: .\scripts\train_model.ps1" -ForegroundColor Gray
Write-Host ""

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Начать с этапа 1? (Y/N)" -ForegroundColor Yellow
$answer = Read-Host

if ($answer -eq "Y" -or $answer -eq "y") {
    Write-Host ""
    Write-Host "Запускаю сбор данных (10 минут тестовой записи)..." -ForegroundColor Green
    .\scripts\collect_data.ps1 -Duration 600 -Segment 60
    Write-Host ""
    Write-Host "Готово! Теперь размечайте видео:" -ForegroundColor Green
    Write-Host ".\scripts\annotate.ps1 -Video `"..\data\raw_videos\<имя>.mp4`"" -ForegroundColor Yellow
} else {
    Write-Host "Используйте команды выше для запуска нужного этапа" -ForegroundColor Gray
}

