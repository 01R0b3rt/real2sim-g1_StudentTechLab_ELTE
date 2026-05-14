@echo off
setlocal
call "%~dp0scripts\maximize_self.bat" "%~f0"
if errorlevel 1 exit /b
cd /d "%~dp0"
mode con: cols=110 lines=36 >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\set_console_compact.ps1" -FontSize 12 -Columns 110 -Rows 36 >nul 2>nul

if exist "assets\unitree_mujoco\unitree_robots\g1\scene.xml" (
  echo Unitree MuJoCo assets already found.
  exit /b 0
)

echo Downloading Unitree MuJoCo assets...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\download_unitree_assets.ps1"
exit /b %errorlevel%
