# VeriSure AI - Idempotent, Health-Aware Development Launcher
# Ensures WSL PostgreSQL, FastAPI Backend, and Vite Frontend are active without duplicate processes or port collisions.

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "   VeriSure AI - Development Environment Launcher     " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

# -------------------------------------------------------------------
# Phase 1: Verify Core Prerequisites (Python, Node, npm, WSL)
# -------------------------------------------------------------------
Write-Host "`n[1/5] Verifying System Prerequisites..." -ForegroundColor Yellow

# Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Suggested action: Install Python 3.10+ and add it to system PATH." -ForegroundColor DarkYellow
    exit 1
}
$pyVer = & python --version 2>&1
Write-Host "  [OK] Python: $pyVer" -ForegroundColor Green

# Check Node & npm
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $nodeCmd -or -not $npmCmd) {
    Write-Host "[ERROR] Node.js or npm is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Suggested action: Install Node.js 18+ and add to PATH." -ForegroundColor DarkYellow
    exit 1
}
$nodeVer = & node -v 2>&1
Write-Host "  [OK] Node.js: $nodeVer" -ForegroundColor Green

# Check WSL
$wslCmd = Get-Command wsl -ErrorAction SilentlyContinue
if (-not $wslCmd) {
    Write-Host "[ERROR] WSL is not installed or not available in PATH." -ForegroundColor Red
    Write-Host "Suggested action: Enable Windows Subsystem for Linux (WSL)." -ForegroundColor DarkYellow
    exit 1
}
Write-Host "  [OK] WSL Available" -ForegroundColor Green

# -------------------------------------------------------------------
# Phase 2: Ensure PostgreSQL is running & reachable
# -------------------------------------------------------------------
Write-Host "`n[2/5] Ensuring PostgreSQL Database is Ready..." -ForegroundColor Yellow

# Check if PostgreSQL is accepting connections on 5432
$dbReachable = $false
try {
    $tcp5432 = Test-NetConnection -ComputerName 127.0.0.1 -Port 5432 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($tcp5432) { $dbReachable = $true }
} catch {}

if (-not $dbReachable) {
    # Dynamically query WSL Ubuntu IP if available, with static fallback
    $wslIp = "172.30.74.29"
    try {
        $detectedIp = (& wsl -d Ubuntu -e hostname -I 2>$null).Trim().Split(' ')[0]
        if ($detectedIp -and $detectedIp.Length -ge 7) { $wslIp = $detectedIp }
    } catch {}

    try {
        $tcpWsl = Test-NetConnection -ComputerName $wslIp -Port 5432 -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($tcpWsl) { $dbReachable = $true }
    } catch {}
}

if (-not $dbReachable) {
    Write-Host "  PostgreSQL not yet responding, starting via WSL Ubuntu daemon..." -ForegroundColor Gray
    try {
        & wsl -d Ubuntu -u root -e /usr/sbin/service postgresql start 2>&1 | Out-Null
        # Also ensure WSL keep-alive is active
        Start-Process -FilePath "wsl" -ArgumentList "-d Ubuntu -u root -e bash -c 'sleep infinity'" -WindowStyle Hidden
        Start-Sleep -Seconds 3
    } catch {
        Write-Host "  [WARN] Failed to start PostgreSQL service automatically via WSL." -ForegroundColor DarkYellow
    }
}

# Verify actual database connection via Python
$dbTestScript = "import asyncio, asyncpg, sys, os
from backend.app.core.config import settings
async def test():
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://'))
        await conn.close()
        sys.exit(0)
    except Exception as e:
        print(f'DB Connection Error: {e}', file=sys.stderr)
        sys.exit(1)
asyncio.run(test())"

$dbCheckResult = & python -c $dbTestScript 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Database connectivity failed." -ForegroundColor Red
    Write-Host "Reason: $dbCheckResult" -ForegroundColor Red
    Write-Host "Suggested action: Check WSL PostgreSQL status (`wsl -d Ubuntu -u root -e service postgresql status`)." -ForegroundColor DarkYellow
    exit 1
}
Write-Host "  [OK] PostgreSQL reachable & accepting connections" -ForegroundColor Green

# -------------------------------------------------------------------
# Phase 3: Run Idempotent Database & Model Seeds
# -------------------------------------------------------------------
Write-Host "`n[3/5] Verifying Database Seeds..." -ForegroundColor Yellow

$seedDataOut = & python -m backend.scripts.seed_data 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Database seeding failed." -ForegroundColor Red
    Write-Host "$seedDataOut" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Core product catalog seeds verified" -ForegroundColor Green

$seedModelsOut = & python -m backend.scripts.seed_models 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Model registry seeding failed." -ForegroundColor Red
    Write-Host "$seedModelsOut" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Model registry seeds verified" -ForegroundColor Green

# -------------------------------------------------------------------
# Phase 4: Manage FastAPI Backend (Port 8000)
# -------------------------------------------------------------------
Write-Host "`n[4/5] Checking FastAPI Backend (Port 8000)..." -ForegroundColor Yellow

$backendReady = $false
$conn8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue

if ($conn8000) {
    $owningPid = $conn8000[0].OwningProcess
    # Probe /health endpoint to see if it is our VeriSure backend
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 3 -ErrorAction Stop
        if ($health.status -eq "healthy") {
            Write-Host "  [OK] VeriSure Backend is already running & healthy (PID: $owningPid)" -ForegroundColor Green
            $backendReady = $true
        }
    } catch {
        # Port is listening but health probe failed or returned unexpected response
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $owningPid" -ErrorAction SilentlyContinue
        $procName = if ($proc) { $proc.Name } else { "Unknown" }
        Write-Host "[ERROR] Port 8000 is occupied by an unresponsive or non-VeriSure process." -ForegroundColor Red
        Write-Host "  Process: $procName (PID: $owningPid)" -ForegroundColor Red
        Write-Host "Suggested action: Terminate PID $owningPid (`Stop-Process -Id $owningPid -Force`) or free port 8000." -ForegroundColor DarkYellow
        exit 1
    }
}

if (-not $backendReady) {
    Write-Host "  Port 8000 is free. Starting FastAPI Backend..." -ForegroundColor Gray
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/k", "title VeriSure Backend && cd /d `"$RepoRoot`" && set PYTHONPATH=. && python -m uvicorn backend.app.main:app --reload --reload-dir backend/app --port 8000") -WindowStyle Normal

    # Poll /health endpoint with retry policy (up to 20 seconds)
    Write-Host "  Waiting for FastAPI Backend to become ready..." -ForegroundColor Gray
    for ($i = 1; $i -le 20; $i++) {
        Start-Sleep -Seconds 1
        try {
            $h = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -ErrorAction Stop
            if ($h.status -eq "healthy") {
                $backendReady = $true
                break
            }
        } catch {}
    }

    if ($backendReady) {
        $newConn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
        $newPid = if ($newConn) { $newConn[0].OwningProcess } else { "Unknown" }
        Write-Host "  [OK] FastAPI Backend successfully started & healthy (PID: $newPid)" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] FastAPI Backend failed to become healthy within 20 seconds." -ForegroundColor Red
        Write-Host "Suggested action: Check the 'VeriSure Backend' console window for traceback details." -ForegroundColor DarkYellow
        exit 1
    }
}

# -------------------------------------------------------------------
# Phase 5: Manage Vite Frontend (Port 5173)
# -------------------------------------------------------------------
Write-Host "`n[5/5] Checking Vite Frontend (Port 5173)..." -ForegroundColor Yellow

$frontendReady = $false
$conn5173 = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue

if ($conn5173) {
    $owningPidFe = $conn5173[0].OwningProcess
    try {
        $feResp = $null
        try { $feResp = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop }
        catch { $feResp = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop }
        if ($feResp -and $feResp.StatusCode -eq 200) {
            Write-Host "  [OK] Vite Frontend is already running & reachable (PID: $owningPidFe)" -ForegroundColor Green
            $frontendReady = $true
        }
    } catch {
        $procFe = Get-CimInstance Win32_Process -Filter "ProcessId = $owningPidFe" -ErrorAction SilentlyContinue
        $procFeName = if ($procFe) { $procFe.Name } else { "Unknown" }
        Write-Host "[ERROR] Port 5173 is occupied by an unresponsive or non-Vite process." -ForegroundColor Red
        Write-Host "  Process: $procFeName (PID: $owningPidFe)" -ForegroundColor Red
        Write-Host "Suggested action: Terminate PID $owningPidFe or free port 5173." -ForegroundColor DarkYellow
        exit 1
    }
}

if (-not $frontendReady) {
    Write-Host "  Port 5173 is free. Starting Vite Frontend..." -ForegroundColor Gray
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/k", "title VeriSure Frontend && cd /d `"$RepoRoot\frontend`" && npm run dev") -WindowStyle Normal

    # Poll frontend with retry policy (up to 15 seconds)
    Write-Host "  Waiting for Vite Frontend to become ready..." -ForegroundColor Gray
    for ($i = 1; $i -le 15; $i++) {
        Start-Sleep -Seconds 1
        try {
            $feProbe = $null
            try { $feProbe = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop }
            catch { $feProbe = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop }
            if ($feProbe -and $feProbe.StatusCode -eq 200) {
                $frontendReady = $true
                break
            }
        } catch {}
    }

    if ($frontendReady) {
        $newConnFe = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
        $newPidFe = if ($newConnFe) { $newConnFe[0].OwningProcess } else { "Unknown" }
        Write-Host "  [OK] Vite Frontend successfully started & reachable (PID: $newPidFe)" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Vite Frontend failed to become ready within 15 seconds." -ForegroundColor Red
        Write-Host "Suggested action: Check the 'VeriSure Frontend' console window for npm/vite errors." -ForegroundColor DarkYellow
        exit 1
    }
}

# -------------------------------------------------------------------
# Final Verification & Startup Summary
# -------------------------------------------------------------------
Write-Host "`n=======================================================" -ForegroundColor Cyan
Write-Host "        VeriSure AI Development Environment            " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  Frontend : http://localhost:5173" -ForegroundColor White
Write-Host "  Backend  : http://localhost:8000" -ForegroundColor White
Write-Host "  Docs     : http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Health   : http://localhost:8000/health" -ForegroundColor White
Write-Host "  Database : Connected (PostgreSQL 18 on WSL Ubuntu)" -ForegroundColor White
Write-Host "  Status   : HEALTHY" -ForegroundColor Green
Write-Host "=======================================================`n" -ForegroundColor Cyan

