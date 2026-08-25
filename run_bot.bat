@echo off
title AI 4 AI - 5 Discord Bots System
color 0b

echo ===================================================
echo     HE THONG 5 DISCORD BOT - AI 4 AI (RUNNING)
echo ===================================================
echo.

cd /d "%~dp0"

:: Kiem tra neu co virtual environment thi kich hoat
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Dang kich hoat virtual environment venv...
    call venv\Scripts\activate.bat
)

:LOOP
echo [INFO] Dang khoi dong 5 Discord Bots va Web Dashboard...
echo [INFO] Giao dien quan ly truc quan tai: http://localhost:5000
echo.

python -u main.py

echo.
echo [CANH BAO] Bot bi tat hoac crash luc %TIME%!
echo [INFO] Tu dong khoi dong lai sau 5 giay...
timeout /t 5 /nobreak >nul
goto LOOP
