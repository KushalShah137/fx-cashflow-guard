@echo off
echo ===================================================
echo Starting FX CashFlow Guard (Backend + Frontend)
echo ===================================================

start "FX CashFlow Guard - FastAPI Backend (Port 8000)" cmd /k ".\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

start "FX CashFlow Guard - Vite Frontend (Port 5173)" cmd /k "set PATH=%~dp0.tools\node-v20.18.0-win-x64;%PATH% && cd "FX CASHFLOW3.0\fx-forecaster" && npm run dev -- --host 0.0.0.0 --port 5173"

echo Backend started at: http://localhost:8000
echo Frontend started at: http://localhost:5173
echo ===================================================
