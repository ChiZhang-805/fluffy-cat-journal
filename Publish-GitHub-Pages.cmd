@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish.ps1"
set "exitcode=%errorlevel%"
echo.
pause
exit /b %exitcode%
