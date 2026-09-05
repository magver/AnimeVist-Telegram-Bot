@echo off
chcp 65001 > nul
title AnimeVist - [1/4] Автопостинг новых серий (#release)
cd /d "%~dp0"

echo ========================================================
echo   [1/4] МОДУЛЬ АВТОПОСТИНГА НОВЫХ СЕРИЙ (#release)
echo ========================================================
echo.

python series_announcer.py
echo.
pause
