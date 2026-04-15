@echo off
chcp 65001 >nul
title Stock AI - Frontend

set PYTHON=C:\Users\Laptop\miniconda3\python.exe
set FRONTEND=%~dp0..\frontend

cd /d "%FRONTEND%"
echo.
echo  Frontend starting...
echo  http://localhost:5173
echo.
npm run dev
pause
