@echo off
title VeriSure AI - Development Platform
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo =======================================================
echo   VeriSure AI Platform - Development Environment
echo =======================================================
echo.

if not exist "%~dp0run_dev.ps1" (
    echo [ERROR] Required controller script 'run_dev.ps1' not found in:
    echo   "%~dp0"
    echo Please ensure all repository files are present.
    echo.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_dev.ps1"
set "EXIT_CODE=!ERRORLEVEL!"

if !EXIT_CODE! neq 0 (
    echo.
    echo [ERROR] VeriSure launcher halted with error code: !EXIT_CODE!
    echo.
    pause
    exit /b !EXIT_CODE!
)

if "%1"=="--no-browser" exit /b 0
if "%1"=="-n" exit /b 0

echo.
echo -------------------------------------------------------
echo [INFO] Press [ENTER] to open http://localhost:5173 in browser,
echo        or type 'N' to skip.
echo -------------------------------------------------------
set /p OPEN_UI="Open Web UI now? (Y/n): "
if /i not "!OPEN_UI!"=="n" (
    start http://localhost:5173
)

exit /b 0