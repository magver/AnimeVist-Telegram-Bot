@echo off
chcp 65001 > nul
title AnimeVist Standalone Automation Service
cd /d "%~dp0"

echo ========================================================
echo   ANIME VIST — АВТОНОМНЫЙ TELEGRAM БОТ И АВТОМАТИЗАЦИЯ
echo ========================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python 3 не обнаружен в системе!
    echo Установите Python с python.org и отметьте галочку "Add to PATH".
    pause
    exit /b 1
)

python main.py
pause
