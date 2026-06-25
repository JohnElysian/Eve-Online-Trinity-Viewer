@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0StartTrinityViewer.ps1" %*
set "EXITCODE=%ERRORLEVEL%"
echo.
if not "%EXITCODE%"=="0" (
  echo Jessica exited with error %EXITCODE%.
  pause
)
exit /b %EXITCODE%
