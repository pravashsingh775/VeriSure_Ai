@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_dev.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Launcher encountered an error
    pause
    exit /b %ERRORLEVEL%
)
exit /b 0