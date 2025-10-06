@echo off
chcp 65001
setlocal

REM --- Настройка нужной версии Python ---
set "MIN_PYTHON_VERSION=3.12"

REM --- Проверяем наличие Python ---
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Python не найден!
    echo Скачиваем и устанавливаем Python %MIN_PYTHON_VERSION%...
    powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe -OutFile python-installer.exe"
    start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1
    IF ERRORLEVEL 1 (
        echo Ошибка установки Python. Выход.
        pause
        exit /b
    )
    del python-installer.exe
)

REM --- Проверяем версию Python ---
for /f "tokens=2 delims= " %%i in ('python --version') do set version=%%i
echo Найдена версия Python: %version%
for /f "tokens=1,2 delims=." %%a in ("%version%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
if %PY_MAJOR% LSS 3 (
    echo Нужна версия Python 3.12+, у вас %version%. Выход.
    pause
    exit /b
)
if %PY_MAJOR%==3 if %PY_MINOR% LSS 12 (
    echo Нужна версия Python 3.12+, у вас %version%. Выход.
    pause
    exit /b
)

REM --- Установка зависимостей ---
echo Устанавливаем зависимости...
python -m pip install --upgrade pip
python -m pip install requests faker

REM --- Запуск main.py ---
echo Запуск main.py...
python main.py

pause
