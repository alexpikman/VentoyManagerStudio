@echo off
setlocal
title Ventoy Manager Studio

cd /d "%~dp0"
echo.
echo  ================================================
echo       VENTOY MANAGER STUDIO - STARTUP
echo  ================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3 was not found.
    echo Install Python 3.10 or newer and enable "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

python --version
echo.
echo [INFO] Starting local application server...
echo [INFO] Address: http://127.0.0.1:5454
echo [INFO] Current foundation is read-only.
echo.
python app.py

echo.
echo [INFO] Application server has stopped.
pause
