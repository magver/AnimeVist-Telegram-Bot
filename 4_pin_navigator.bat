@echo off
chcp 65001 > nul
title AnimeVist - [4/4] Закрепленный навигатор и FAQ (Pin)
cd /d "%~dp0"

echo ========================================================
echo   [4/4] ЗАКРЕПЛЕННЫЙ НАВИГАТОР, ССЫЛКИ И FAQ (Pin)
echo ========================================================
echo.

python -c "
from pinned_navigator import publish_pinned_navigator
confirm = input('Отправить и закрепить главный навигационный пост в канале? (y/n): ').strip().lower()
if confirm in ['y', 'yes', 'д', 'да']:
    publish_pinned_navigator(dry_run=False)
else:
    print('Отправка отменена.')
"

echo.
pause
