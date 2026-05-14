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

echo Deleting ChArUco stereo pairs where either side has fewer than 12 corners...
echo.

"%PYTHON_EXE%" scripts\filter_stereo_charuco.py --min-corners 12 --yes

pause
