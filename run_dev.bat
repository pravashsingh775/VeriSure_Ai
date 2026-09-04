@echo off
setlocal
echo ===================================================
echo Starting VeriSure AI Platform Development Servers
echo ===================================================

cd /d "%~dp0"
set PYTHONPATH=.

echo [1/3] Verifying database connectivity & seeds...
python -m backend.scripts.seed_data
python -m backend.scripts.seed_models

echo [2/3] Starting FastAPI Backend on http://localhost:8000 ...
start "VeriSure Backend" cmd /k "set PYTHONPATH=. && python -m uvicorn backend.app.main:app --reload --port 8000"

echo [3/3] Starting Vite Frontend on http://localhost:5173 ...
start "VeriSure Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo VeriSure AI Services Launched Successfully!
echo Frontend: http://localhost:5173
echo Backend API Docs: http://localhost:8000/docs
echo ===================================================
pause