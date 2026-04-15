@echo off
chcp 65001 >nul
title Stock AI - Backend
cd /d %~dp0..\backend
echo.
echo  Backend starting...
echo  http://127.0.0.1:8000
echo  http://127.0.0.1:8000/docs
echo.
C:\Users\Laptop\miniconda3\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info
echo.
echo  Backend stopped. Press any key to close.
pause >nul
