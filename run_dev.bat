@echo off
setlocal EnableExtensions

title VeriSure AI - Development Platform

cd /d "%~dp0"

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to switch to repository directory:
    echo   "%~dp0"
    echo.
    pause
    exit /b 1
)

echo =======================================================
echo   VeriSure AI Platform - Development Environment
echo =======================================================
echo.

set "CONTROLLER=%~dp0run_dev.ps1"

if not exist "%CONTROLLER%" (
    echo [ERROR] Required controller script 'run_dev.ps1' not found.
    echo.
    echo Expected:
    echo   "%CONTROLLER%"
    echo.
    echo Please ensure all repository files are present.
    echo.
    pause
    exit /b 1
)

rem -------------------------------------------------------
rem Translate BAT-friendly browser arguments to PowerShell.
rem -------------------------------------------------------

set "PS_ARGS="

if /i "%~1"=="--no-browser" set "PS_ARGS=-NoBrowser"
if /i "%~1"=="-no-browser"  set "PS_ARGS=-NoBrowser"
if /i "%~1"=="-n"           set "PS_ARGS=-NoBrowser"

echo [INFO] Starting VeriSure AI development controller...
echo.

powershell.exe ^
    -NoLogo ^
    -NoProfile ^
    -NonInteractive ^
    -ExecutionPolicy Bypass ^
    -File "%CONTROLLER%" %PS_ARGS%

set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo =======================================================
    echo [ERROR] VeriSure AI launcher failed.
    echo         Exit code: %EXIT_CODE%
    echo =======================================================
    echo.
    pause
)

exit /b %EXIT_CODE%