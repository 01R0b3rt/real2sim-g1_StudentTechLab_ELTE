@echo off
setlocal
call "%~dp0scripts\maximize_self.bat" "%~f0"
if errorlevel 1 exit /b
cd /d "%~dp0"
mode con: cols=110 lines=36 >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\set_console_compact.ps1" -FontSize 12 -Columns 110 -Rows 36 >nul 2>nul

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  set "PYTHON_EXE=python"
)

echo Starting ChArUco stereo image capture...
echo.
echo Controls:
echo   SPACE  save image pair when both cameras are READY
echo   q/ESC  quit capture
echo.

"%PYTHON_EXE%" scripts\capture_stereo_charuco.py

pause
