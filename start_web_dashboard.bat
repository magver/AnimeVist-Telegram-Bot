@echo off
chcp 65001 > nul
title AnimeVist Web Dashboard
cd /d "%~dp0"

echo ========================================================
echo   ANIME VIST — ЗАПУСК ВЕБ-ИНТЕРФЕЙСА УПРАВЛЕНИЯ
echo ========================================================
echo.
echo [1/2] Проверка окружения Python...

where python >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
    )
)

echo [2/2] Запуск локального веб-сервера...
echo Панель управления откроется в браузере автоматически.
echo.

python web_dashboard.py
if %errorlevel% neq 0 (
    echo.
    echo [ОШИБКА] Не удалось запустить веб-интерфейс.
    pause
)
pause
