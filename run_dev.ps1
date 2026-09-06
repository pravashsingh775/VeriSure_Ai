#requires -Version 5.1

<#
.SYNOPSIS
    VeriSure AI - Idempotent, health-aware development environment launcher.

.DESCRIPTION
    Ensures the following development services are available:

      1. WSL Ubuntu PostgreSQL
      2. FastAPI backend on port 8000
      3. Vite frontend on port 5173

    The launcher is intentionally idempotent:
      - Re-running it does not create duplicate backend/frontend processes.
      - Existing healthy services are reused.
      - Occupied ports are never blindly killed.
      - Services are considered ready only after health checks succeed.

.PARAMETER NoBrowser
    Do not automatically open the frontend in the browser.
#>

[CmdletBinding()]
param(
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# -------------------------------------------------------------------
# Global paths / constants
# -------------------------------------------------------------------

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $RepoRoot

$BackendDir  = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

$BackendPort  = 8000
$FrontendPort = 5173
$WslDistro    = "Ubuntu"

# Canonical Windows-side PostgreSQL endpoint for WSL mirrored networking.
$PostgresHost = "127.0.0.1"
$PostgresPort = 5432

$BackendHealthUrl  = "http://127.0.0.1:$BackendPort/health"
$FrontendHealthUrl = "http://127.0.0.1:$FrontendPort"

# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------

function Write-Section {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title
    )

    Write-Host ""
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host "=======================================================" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Message)

    Write-Host "  [INFO] $Message" -ForegroundColor Gray
}

function Write-Ok {
    param([string]$Message)

    Write-Host "  [OK]   $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)

    Write-Host "  [WARN] $Message" -ForegroundColor DarkYellow
}

function Write-ErrorMessage {
    param([string]$Message)

    Write-Host "  [ERROR] $Message" -ForegroundColor Red
}

function Test-TcpPort {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ComputerName,

        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    try {
        return [bool](Test-NetConnection `
            -ComputerName $ComputerName `
            -Port $Port `
            -InformationLevel Quiet `
            -WarningAction SilentlyContinue)
    }
    catch {
        return $false
    }
}

function Test-BackendHealth {
    try {
        $response = Invoke-RestMethod `
            -Uri $BackendHealthUrl `
            -TimeoutSec 3 `
            -ErrorAction Stop

        return ($response.status -eq "healthy")
    }
    catch {
        return $false
    }
}

function Test-FrontendHealth {
    try {
        $response = Invoke-WebRequest `
            -Uri $FrontendHealthUrl `
            -UseBasicParsing `
            -TimeoutSec 3 `
            -ErrorAction Stop

        return ($response.StatusCode -eq 200)
    }
    catch {
        try {
            $response = Invoke-WebRequest `
                -Uri "http://localhost:$FrontendPort" `
                -UseBasicParsing `
                -TimeoutSec 3 `
                -ErrorAction Stop

            return ($response.StatusCode -eq 200)
        }
        catch {
            return $false
        }
    }
}

function Get-ListeningProcess {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    try {
        # Materialize the result into an array so PowerShell 5.1 does not
        # ambiguously collapse a single/multiple connection into pipeline
        # behavior that can affect truthiness and property access.
        $connections = @(
            Get-NetTCPConnection `
                -LocalPort $Port `
                -State Listen `
                -ErrorAction SilentlyContinue
        )

        if ($connections.Count -gt 0) {
            return $connections[0]
        }
    }
    catch {
        # Port/process discovery is advisory. Health checks below are
        # authoritative for services managed by this launcher.
    }

    return $null
}

# -------------------------------------------------------------------
# Startup banner
# -------------------------------------------------------------------

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "       VeriSure AI Development Environment             " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " Repository : $RepoRoot" -ForegroundColor DarkGray
Write-Host " Backend    : http://localhost:$BackendPort" -ForegroundColor DarkGray
Write-Host " Frontend   : http://localhost:$FrontendPort" -ForegroundColor DarkGray
Write-Host " PostgreSQL : $PostgresHost`:$PostgresPort (WSL $WslDistro)" -ForegroundColor DarkGray
Write-Host "=======================================================" -ForegroundColor Cyan

try {

    # ===============================================================
    # PHASE 1 - Prerequisites
    # ===============================================================

    Write-Section "[1/5] Verifying System Prerequisites"

    # Python
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue

    if (-not $pythonCmd) {
        throw "Python is not installed or is not available in PATH."
    }

    $pyVersion = & python --version 2>&1

    if ($LASTEXITCODE -ne 0) {
        throw "Python was found but could not be executed."
    }

    Write-Ok "Python: $pyVersion"

    # Node.js
    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue

    if (-not $nodeCmd) {
        throw "Node.js is not installed or is not available in PATH."
    }

    $nodeVersion = & node --version 2>&1

    if ($LASTEXITCODE -ne 0) {
        throw "Node.js was found but could not be executed."
    }

    Write-Ok "Node.js: $nodeVersion"

    # npm
    $npmCmd = Get-Command npm -ErrorAction SilentlyContinue

    if (-not $npmCmd) {
        throw "npm is not installed or is not available in PATH."
    }

    $npmVersion = & npm --version 2>&1

    if ($LASTEXITCODE -ne 0) {
        throw "npm was found but could not be executed."
    }

    Write-Ok "npm: $npmVersion"

    # WSL
    $wslCmd = Get-Command wsl -ErrorAction SilentlyContinue

    if (-not $wslCmd) {
        throw "WSL is not installed or is not available in PATH."
    }

    Write-Ok "WSL command available"

    # Required directories
    if (-not (Test-Path -LiteralPath $BackendDir -PathType Container)) {
        throw "Backend directory not found: $BackendDir"
    }

    if (-not (Test-Path -LiteralPath $FrontendDir -PathType Container)) {
        throw "Frontend directory not found: $FrontendDir"
    }

    if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "package.json") -PathType Leaf)) {
        throw "Frontend package.json not found: $FrontendDir\package.json"
    }

    Write-Ok "Repository structure verified"

    # ===============================================================
    # PHASE 2 - PostgreSQL
    # ===============================================================

    Write-Section "[2/5] Ensuring PostgreSQL Database is Ready"

    # ---------------------------------------------------------------
    # Ensure the WSL distribution is running.
    # ---------------------------------------------------------------

    Write-Info "Ensuring WSL distribution '$WslDistro' is available..."

    try {
        & wsl -d $WslDistro -e true 2>&1 | Out-Null

        if ($LASTEXITCODE -ne 0) {
            throw "WSL returned exit code $LASTEXITCODE."
        }
    }
    catch {
        throw "Unable to start/access WSL distribution '$WslDistro'. $($_.Exception.Message)"
    }

    Write-Ok "WSL distribution ready"

    # ---------------------------------------------------------------
    # Test the canonical Windows-side PostgreSQL endpoint.
    # No WSL IP discovery, portproxy, or relay is required.
    # ---------------------------------------------------------------

    Write-Info "Checking PostgreSQL TCP endpoint $PostgresHost`:$PostgresPort..."

    $dbReachable = Test-TcpPort `
        -ComputerName $PostgresHost `
        -Port $PostgresPort

    if (-not $dbReachable) {

        Write-Warn "PostgreSQL is not reachable on $PostgresHost`:$PostgresPort."
        Write-Info "Attempting to start PostgreSQL inside WSL..."

        try {
            & wsl `
                -d $WslDistro `
                -u root `
                -e /usr/sbin/service postgresql start `
                2>&1 | Out-Null
        }
        catch {
            Write-Warn "Automatic PostgreSQL service start command failed: $($_.Exception.Message)"
        }

        Start-Sleep -Seconds 2

        for ($i = 1; $i -le 15; $i++) {

            if (Test-TcpPort -ComputerName $PostgresHost -Port $PostgresPort) {
                $dbReachable = $true
                break
            }

            Start-Sleep -Seconds 1
        }
    }

    if (-not $dbReachable) {
        throw "PostgreSQL TCP port $PostgresPort is not reachable at $PostgresHost."
    }

    Write-Ok "PostgreSQL TCP endpoint reachable at $PostgresHost`:$PostgresPort"

    # ---------------------------------------------------------------
    # Real application-level PostgreSQL validation.
    # Use the repository's dedicated connectivity checker rather than
    # embedding multiline Python in `python -c`, which is fragile under
    # Windows PowerShell quoting/parsing.
    # ---------------------------------------------------------------

    Write-Info "Verifying application-level PostgreSQL connectivity..."

    $dbCheckOutput = & python scripts\db_connectivity_check.py 2>&1
    $dbCheckExitCode = $LASTEXITCODE

    if ($dbCheckExitCode -ne 0) {
        Write-ErrorMessage "Application-level PostgreSQL connectivity failed."
        Write-Host "$dbCheckOutput" -ForegroundColor Red
        Write-Host ""
        Write-Host "Suggested diagnostic:" -ForegroundColor DarkYellow
        Write-Host "  python scripts\db_connectivity_check.py" -ForegroundColor DarkYellow
        Write-Host "  wsl -d $WslDistro -u root -e service postgresql status" -ForegroundColor DarkYellow
        throw "Database connection validation failed (exit code $dbCheckExitCode)."
    }

    if ($dbCheckOutput) {
        Write-Host "$dbCheckOutput" -ForegroundColor DarkGray
    }

    Write-Ok "PostgreSQL application connection verified"

    # ===============================================================
    # PHASE 3 - Seeds
    # ===============================================================

    Write-Section "[3/5] Verifying Database Seeds"

    Write-Info "Running core product/catalog seed verification..."

    $seedDataOutput = & python -m backend.scripts.seed_data 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMessage "Database seed_data failed."
        Write-Host "$seedDataOutput" -ForegroundColor Red
        throw "Database seed_data failed."
    }

    Write-Ok "Core product catalog seeds verified"

    Write-Info "Running model registry seed verification..."

    $seedModelsOutput = & python -m backend.scripts.seed_models 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMessage "Database seed_models failed."
        Write-Host "$seedModelsOutput" -ForegroundColor Red
        throw "Database seed_models failed."
    }

    Write-Ok "Model registry seeds verified"

    # ===============================================================
    # PHASE 4 - FastAPI Backend
    # ===============================================================

    Write-Section "[4/5] Checking FastAPI Backend"

    $backendReady = $false

    # Health-first idempotency:
    # If VeriSure's health endpoint is already healthy, reuse the existing
    # service even if socket/process enumeration is temporarily inconsistent.
    if (Test-BackendHealth) {
        $backendConnection = Get-ListeningProcess -Port $BackendPort
        $backendPid = if ($backendConnection) {
            $backendConnection.OwningProcess
        }
        else {
            "unknown"
        }

        Write-Ok "VeriSure Backend already healthy (PID: $backendPid)"
        $backendReady = $true
    }
    else {
        $backendConnection = Get-ListeningProcess -Port $BackendPort

        if ($backendConnection) {
            $backendPid = $backendConnection.OwningProcess

            try {
                $backendProcess = Get-CimInstance `
                    Win32_Process `
                    -Filter "ProcessId = $backendPid" `
                    -ErrorAction SilentlyContinue

                $backendProcessName = if ($backendProcess) {
                    $backendProcess.Name
                }
                else {
                    "Unknown"
                }
            }
            catch {
                $backendProcessName = "Unknown"
            }

            Write-ErrorMessage `
                "Port $BackendPort is occupied but the service is not a healthy VeriSure backend."

            Write-Host "  Process: $backendProcessName" -ForegroundColor Red
            Write-Host "  PID:     $backendPid" -ForegroundColor Red
            Write-Host ""
            Write-Host "The launcher will NOT terminate the process automatically." -ForegroundColor DarkYellow
            Write-Host "Free the port manually if this is an orphaned process." -ForegroundColor DarkYellow

            throw "Port $BackendPort is occupied by an unhealthy process."
        }

        Write-Info "Port $BackendPort is available."
        Write-Info "Starting FastAPI Backend..."

        $backendCommand = @(
            "/k",
            "title VeriSure Backend && cd /d `"$RepoRoot`" && set PYTHONPATH=. && python -m uvicorn backend.app.main:app --reload --reload-dir backend/app --port $BackendPort"
        )

        Start-Process `
            -FilePath "cmd.exe" `
            -ArgumentList $backendCommand `
            -WorkingDirectory $RepoRoot `
            -WindowStyle Normal | Out-Null

        Write-Info "Waiting for FastAPI health endpoint..."

        for ($i = 1; $i -le 30; $i++) {
            Start-Sleep -Seconds 1

            if (Test-BackendHealth) {
                $backendReady = $true
                break
            }
        }

        if (-not $backendReady) {
            Write-ErrorMessage `
                "FastAPI Backend failed to become healthy within 30 seconds."

            Write-Host ""
            Write-Host "Check the 'VeriSure Backend' console for the traceback." -ForegroundColor DarkYellow
            Write-Host "Health endpoint: $BackendHealthUrl" -ForegroundColor DarkYellow

            throw "FastAPI Backend startup failed."
        }

        $backendConnection = Get-ListeningProcess -Port $BackendPort
        $backendPid = if ($backendConnection) {
            $backendConnection.OwningProcess
        }
        else {
            "unknown"
        }

        Write-Ok "FastAPI Backend started and healthy (PID: $backendPid)"
    }

    # ===============================================================
    # PHASE 5 - Vite Frontend
    # ===============================================================

    Write-Section "[5/5] Checking Vite Frontend"

    $frontendReady = $false

    # Health-first idempotency:
    # Reuse an already responding Vite server before relying on socket
    # enumeration. This prevents duplicate npm/Vite processes on reruns.
    if (Test-FrontendHealth) {
        $frontendConnection = Get-ListeningProcess -Port $FrontendPort
        $frontendPid = if ($frontendConnection) {
            $frontendConnection.OwningProcess
        }
        else {
            "unknown"
        }

        Write-Ok "Vite Frontend already running and reachable (PID: $frontendPid)"
        $frontendReady = $true
    }
    else {
        $frontendConnection = Get-ListeningProcess -Port $FrontendPort

        if ($frontendConnection) {
            $frontendPid = $frontendConnection.OwningProcess

            try {
                $frontendProcess = Get-CimInstance `
                    Win32_Process `
                    -Filter "ProcessId = $frontendPid" `
                    -ErrorAction SilentlyContinue

                $frontendProcessName = if ($frontendProcess) {
                    $frontendProcess.Name
                }
                else {
                    "Unknown"
                }
            }
            catch {
                $frontendProcessName = "Unknown"
            }

            Write-ErrorMessage `
                "Port $FrontendPort is occupied but the frontend is not responding."

            Write-Host "  Process: $frontendProcessName" -ForegroundColor Red
            Write-Host "  PID:     $frontendPid" -ForegroundColor Red
            Write-Host ""
            Write-Host "The launcher will NOT terminate the process automatically." -ForegroundColor DarkYellow
            Write-Host "Free the port manually if this is an orphaned process." -ForegroundColor DarkYellow

            throw "Port $FrontendPort is occupied by an unhealthy process."
        }

        Write-Info "Port $FrontendPort is available."
        Write-Info "Starting Vite Frontend..."

        $frontendCommand = @(
            "/k",
            "title VeriSure Frontend && cd /d `"$FrontendDir`" && npm run dev"
        )

        Start-Process `
            -FilePath "cmd.exe" `
            -ArgumentList $frontendCommand `
            -WorkingDirectory $FrontendDir `
            -WindowStyle Normal | Out-Null

        Write-Info "Waiting for Vite HTTP endpoint..."

        for ($i = 1; $i -le 30; $i++) {
            Start-Sleep -Seconds 1

            if (Test-FrontendHealth) {
                $frontendReady = $true
                break
            }
        }

        if (-not $frontendReady) {
            Write-ErrorMessage `
                "Vite Frontend failed to become reachable within 30 seconds."

            Write-Host ""
            Write-Host "Check the 'VeriSure Frontend' console for npm/Vite errors." -ForegroundColor DarkYellow
            Write-Host "Frontend URL: $FrontendHealthUrl" -ForegroundColor DarkYellow

            throw "Vite Frontend startup failed."
        }

        $frontendConnection = Get-ListeningProcess -Port $FrontendPort
        $frontendPid = if ($frontendConnection) {
            $frontendConnection.OwningProcess
        }
        else {
            "unknown"
        }

        Write-Ok "Vite Frontend started and reachable (PID: $frontendPid)"
    }

    # ===============================================================
    # FINAL VERIFICATION
    # ===============================================================

    Write-Section "Final Verification"

    if (-not $dbReachable) {
        throw "Final verification failed: PostgreSQL is not reachable."
    }

    if (-not (Test-BackendHealth)) {
        throw "Final verification failed: Backend health check failed."
    }

    if (-not (Test-FrontendHealth)) {
        throw "Final verification failed: Frontend health check failed."
    }

    # Confirm both application ports have active listeners after health checks.
    # This catches unusual proxy/redirect situations while keeping health as
    # the primary readiness signal.
    $finalBackendConnection = Get-ListeningProcess -Port $BackendPort
    if (-not $finalBackendConnection) {
        throw "Final verification failed: Backend port $BackendPort has no listening socket."
    }

    $finalFrontendConnection = Get-ListeningProcess -Port $FrontendPort
    if (-not $finalFrontendConnection) {
        throw "Final verification failed: Frontend port $FrontendPort has no listening socket."
    }

    Write-Host ""
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host "       VeriSure AI Development Environment             " -ForegroundColor Cyan
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host "  Frontend : http://localhost:$FrontendPort" -ForegroundColor White
    Write-Host "  Backend  : http://localhost:$BackendPort" -ForegroundColor White
    Write-Host "  Docs     : http://localhost:$BackendPort/docs" -ForegroundColor White
    Write-Host "  Health   : http://localhost:$BackendPort/health" -ForegroundColor White
    Write-Host "  Database : PostgreSQL / $PostgresHost`:$PostgresPort" -ForegroundColor White
    Write-Host "  Status   : HEALTHY" -ForegroundColor Green
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host ""

    # ---------------------------------------------------------------
    # Browser
    # ---------------------------------------------------------------

    if (-not $NoBrowser) {

        Write-Info "Opening VeriSure Web UI..."

        try {
            Start-Process "http://localhost:$FrontendPort" | Out-Null
        }
        catch {
            Write-Warn "Could not automatically open the browser."
            Write-Host "Open manually: http://localhost:$FrontendPort" -ForegroundColor DarkYellow
        }
    }
    else {
        Write-Info "Browser launch skipped (-NoBrowser)."
    }

    exit 0
}
catch {

    Write-Host ""
    Write-Host "=======================================================" -ForegroundColor Red
    Write-Host "       VeriSure AI Development Startup FAILED          " -ForegroundColor Red
    Write-Host "=======================================================" -ForegroundColor Red
    Write-Host "  Reason: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "=======================================================" -ForegroundColor Red
    Write-Host ""

    exit 1
}