@echo off
setlocal enabledelayedexpansion
echo ===================================================
echo Starting VeriSure AI Platform Development Servers
echo ===================================================

cd /d "%~dp0"
set PYTHONPATH=.

echo [0/3] Ensuring PostgreSQL daemon is active in WSL...
where wsl >nul 2>nul
if %errorlevel% equ 0 (
    start "VeriSure PostgreSQL Daemon" /min wsl -d Ubuntu -u root -e bash -c "service postgresql restart && sleep infinity"
    timeout /t 2 /nobreak >nul
)

echo [1/3] Verifying database connectivity and seeds...
python -m backend.scripts.seed_data
if %errorlevel% neq 0 (
    echo [ERROR] Failed to seed database. Please verify PostgreSQL is reachable.
    pause
    exit /b 1
)
python -m backend.scripts.seed_models
if %errorlevel% neq 0 (
    echo [ERROR] Failed to seed models.
    pause
    exit /b 1
)

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