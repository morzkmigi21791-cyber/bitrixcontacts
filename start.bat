@echo off
chcp 65001 >nul
title Bitrix24 Contacts - Project Launcher

echo.
echo ============================================================
echo                Bitrix24 Contacts - Project Launcher
echo ============================================================
echo.
echo [INFO] 🚀 Серверное приложение Битрикс24
echo [INFO] 📥 Скачать проект: https://github.com/your-repo/bitrix24-contacts
echo [INFO] 🌐 Установка: https://amusingly-awaited-starling.cloudpub.ru/bitrix/oauth/install
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)

echo [INFO] Python and Node.js are installed
echo.

REM Check if required files exist
if not exist "backend\main.py" (
    echo [ERROR] Backend file not found: backend\main.py
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo [ERROR] Frontend package.json not found: frontend\package.json
    pause
    exit /b 1
)

echo [INFO] All required files found
echo.

REM Install Python dependencies
echo [INFO] Installing Python dependencies...
pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)
echo [SUCCESS] Python dependencies installed
echo.

REM Install Node.js dependencies
echo [INFO] Installing Node.js dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install Node.js dependencies
    pause
    exit /b 1
)
echo [SUCCESS] Node.js dependencies installed
echo.

REM Build frontend for production
echo [INFO] Building frontend for production...
call npm run build
if errorlevel 1 (
    echo [ERROR] Failed to build frontend
    pause
    exit /b 1
)
echo [SUCCESS] Frontend built successfully
echo.

cd ..

REM Start unified server
echo [INFO] Starting unified server on port 8000...
echo [INFO] Frontend and backend will be served from the same port
echo [INFO] Open your browser and go to: http://localhost:8000
echo.
echo ============================================================
echo                    🎯 Готово к использованию!
echo ============================================================
echo [INFO] 📱 Локальное приложение: http://localhost:8000
echo [INFO] 🌐 Серверное приложение: https://amusingly-awaited-starling.cloudpub.ru
echo [INFO] 🔗 Установка в Битрикс24: https://amusingly-awaited-starling.cloudpub.ru/bitrix/oauth/install
echo [INFO] 📥 Скачать проект: https://github.com/your-repo/bitrix24-contacts
echo ============================================================
echo.

python backend\main.py

echo.
echo ============================================================
echo                    Server Stopped
echo ============================================================
echo.
pause
