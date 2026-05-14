@echo off
setlocal
call "%~dp0scripts\maximize_self.bat" "%~f0"
if errorlevel 1 exit /b
cd /d "%~dp0"
title Real2Sim G1 - First Run Setup
color 0A
mode con: cols=110 lines=36 >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\set_console_compact.ps1" -FontSize 12 -Columns 110 -Rows 36 >nul 2>nul

cls
echo.
if exist "%~dp0docs\first_run_banner.txt" (
  type "%~dp0docs\first_run_banner.txt"
) else (
  echo ===============================================================================
  echo                         REAL2SIM G1 FIRST RUN SETUP
  echo ===============================================================================
)
echo.
echo This script prepares a fresh GitHub clone on Windows.
echo It creates .venv, installs Python dependencies, downloads Unitree assets,
echo then runs the project status check.
echo.

if not exist "logs" mkdir logs >nul 2>nul
set "FIRST_RUN_LOG=%~dp0logs\first_run_setup.log"
> "%FIRST_RUN_LOG%" echo Real2Sim G1 first-run setup log
>> "%FIRST_RUN_LOG%" echo Started: %date% %time%
>> "%FIRST_RUN_LOG%" echo Project: %cd%
>> "%FIRST_RUN_LOG%" echo.

if not exist ".venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  py -3.11 -m venv .venv
  if errorlevel 1 (
    py -3.10 -m venv .venv
  )
  if errorlevel 1 (
    python -m venv .venv
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo ERROR: Could not create .venv.
  echo Install Python 3.10 or 3.11, then run this script again.
  pause
  exit /b 1
)

echo.
echo Installing Python dependencies...
echo Detailed pip output is saved to:
echo   logs\first_run_setup.log
".venv\Scripts\python.exe" -m pip install --upgrade pip >> "%FIRST_RUN_LOG%" 2>&1
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt >> "%FIRST_RUN_LOG%" 2>&1
if errorlevel 1 goto fail
echo Dependencies ready.

echo.
call "%~dp0DOWNLOAD_UNITREE_ASSETS.bat"
if errorlevel 1 goto fail

cls
echo.
if exist "%~dp0docs\first_run_banner.txt" (
  type "%~dp0docs\first_run_banner.txt"
) else (
  echo ===============================================================================
  echo                         REAL2SIM G1 FIRST RUN SETUP
  echo ===============================================================================
)
echo.
echo.
echo Running status check...
".venv\Scripts\python.exe" src\openclaw_real2sim_tool.py status

echo.
echo ===============================================================================
echo Setup complete.
echo Next:
echo   1. Run CALIBRATION_MENU.bat for a fresh stereo calibration.
echo   2. Run START_DEMO.bat for the demo launcher.
echo ===============================================================================
pause
exit 0

:fail
echo.
echo ERROR: First-run setup failed.
echo Detailed log:
echo   logs\first_run_setup.log
pause
exit 1
