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

echo Starting stable two-arm demo...
"%PYTHON_EXE%" src\openclaw_real2sim_tool.py --config configs\g1_arm_mapping_STABLE_ARMS.yaml run-demo ^
  --stereo ^
  --stereo-config configs\stereo_calibration.yaml ^
  --left-camera 0 ^
  --right-camera 1 ^
  --camera-backend dshow ^
  --right-rotation cw ^
  --confidence 0.35 ^
  --display-scale 0.5

pause
