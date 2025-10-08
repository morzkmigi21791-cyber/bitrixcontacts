@echo off
chcp 65001 >nul
title Bitrix24 Contacts - Project Launcher

echo.
echo ============================================================
echo                Bitrix24 Contacts - Project Launcher
echo ============================================================
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
if not exist "backend\backend.py" (
    echo [ERROR] Backend file not found: backend\backend.py
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
cd ..
echo [SUCCESS] Node.js dependencies installed
echo.

REM Start backend in new window
echo [INFO] Starting FastAPI backend on port 8000...
start "Bitrix24 Backend" cmd /k "cd /d %~dp0backend && python backend.py"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in new window
echo [INFO] Starting React frontend on port 3000...
start "Bitrix24 Frontend" cmd /k "cd /d %~dp0frontend && npm start"

REM Wait a moment for frontend to start
timeout /t 5 /nobreak >nul

REM Browser will open automatically by React

echo.
echo ============================================================
echo                    Project Started Successfully!
echo ============================================================
echo.
echo Backend API:    http://localhost:8000
echo Frontend:       http://localhost:3000
echo API Docs:       http://localhost:8000/docs
echo.
echo Press any key to close this launcher...
pause >nul
