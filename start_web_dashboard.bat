@echo off
chcp 65001 > nul
title AnimeVist Web Dashboard
cd /d "%~dp0"

echo ========================================================
echo   ANIME VIST — ЗАПУСК ВЕБ-ИНТЕРФЕЙСА УПРАВЛЕНИЯ
echo ========================================================
echo.
echo Открытие панели управления в браузере: http://localhost:5000
echo.

start "" "http://localhost:5000"
python web_dashboard.py
pause
