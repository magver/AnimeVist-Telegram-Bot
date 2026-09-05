@echo off
chcp 65001 > nul
title AnimeVist - [2/4] Автопостинг аниме-новостей (#news)
cd /d "%~dp0"

echo ========================================================
echo   [2/4] МОДУЛЬ АНИМЕ-НОВОСТЕЙ И АНОНСОВ (#news)
echo ========================================================
echo.

python news_announcer.py
echo.
pause
