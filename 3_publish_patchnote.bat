@echo off
chcp 65001 > nul
title AnimeVist - [3/4] Публикатор обновлений (#patchnote)
cd /d "%~dp0"

echo ========================================================
echo   [3/4] ПУБЛИКАТОР ОБНОВЛЕНИЙ И ЧЕЙНДЖЛОГОВ (#patchnote)
echo ========================================================
echo.

python -c "
from patchnote_publisher import publish_patchnote_from_github
confirm = input('Опубликовать релизный патчноут из GitHub Releases в Telegram? (y/n): ').strip().lower()
if confirm in ['y', 'yes', 'д', 'да']:
    publish_patchnote_from_github(dry_run=False)
else:
    print('Публикация отменена.')
"

echo.
pause
