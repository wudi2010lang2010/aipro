@echo off
chcp 65001 >nul
title Stock AI Analyzer

set PYTHON=C:\Users\Laptop\miniconda3\python.exe
set ROOT=%~dp0
set BACKEND=%ROOT%backend
set FRONTEND=%ROOT%frontend
set SCRIPTS=%ROOT%scripts
set PORT=8000

echo.
echo  +--------------------------------------------------+
echo  ^|      Stock AI Analyzer  v1.0.0                  ^|
echo  ^|      AI A-Share Short-Term Trading Analyzer      ^|
echo  +--------------------------------------------------+
echo.

:: Check Python
if not exist "%PYTHON%" (
    echo  [ERROR] Python not found:
    echo    %PYTHON%
    echo.
    echo  Please edit PYTHON path in start.bat
    pause & exit /b 1
)

:: Check backend
if not exist "%BACKEND%\main.py" (
    echo  [ERROR] backend\main.py not found.
    pause & exit /b 1
)

:: Check frontend
if not exist "%FRONTEND%\package.json" (
    echo  [ERROR] frontend\package.json not found.
    echo  Please run: cd frontend ^& npm install
    pause & exit /b 1
)

:: Check helper scripts
if not exist "%SCRIPTS%\start_backend.bat" (
    echo  [ERROR] scripts\start_backend.bat not found.
    pause & exit /b 1
)

if not exist "%SCRIPTS%\start_frontend.bat" (
    echo  [ERROR] scripts\start_frontend.bat not found.
    pause & exit /b 1
)

:: Step 1: Start backend in new window
echo  [1/4] Starting backend...
start "Stock AI - Backend" "%SCRIPTS%\start_backend.bat"

:: Step 2: Wait for backend to be ready
echo  [2/4] Waiting for backend (max 30s)...
"%PYTHON%" "%SCRIPTS%\wait_server.py" "http://127.0.0.1:%PORT%/health" 30
if errorlevel 1 (
    echo.
    echo  [ERROR] Backend failed to start.
    echo  Please check the backend window for errors.
    echo.
    echo  Common causes:
    echo    1. Port %PORT% already in use
    echo    2. Missing packages: cd backend ^& pip install -r requirements.txt
    echo    3. Config error in backend\.env
    echo.
    pause & exit /b 1
)

:: Step 3: Start frontend in new window
echo  [3/4] Starting frontend...
start "Stock AI - Frontend" "%SCRIPTS%\start_frontend.bat"

:: Step 4: Wait for frontend then open browser
echo  [4/4] Waiting for frontend (max 20s)...
"%PYTHON%" "%SCRIPTS%\wait_server.py" "http://localhost:5173" 20

echo  Opening browser...
start http://localhost:5173

echo.
echo  +--------------------------------------------------+
echo  ^|  Started successfully!                           ^|
echo  ^|                                                  ^|
echo  ^|  Frontend : http://localhost:5173                ^|
echo  ^|  Backend  : http://127.0.0.1:%PORT%                     ^|
echo  ^|  API Docs : http://127.0.0.1:%PORT%/docs                ^|
echo  ^|                                                  ^|
echo  ^|  Close Backend / Frontend windows to stop.      ^|
echo  +--------------------------------------------------+
echo.
echo  Press any key to close this launcher window...
pause >nul
