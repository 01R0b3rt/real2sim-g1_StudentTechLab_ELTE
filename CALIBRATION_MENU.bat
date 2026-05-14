@echo off
setlocal
call "%~dp0scripts\maximize_self.bat" "%~f0"
if errorlevel 1 exit /b
cd /d "%~dp0"
title Real2Sim G1 - SZTAKI Calibration Console
color 0A
mode con: cols=110 lines=36 >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\set_console_compact.ps1" -FontSize 12 -Columns 110 -Rows 36 >nul 2>nul

:menu
cls
if exist "%~dp0docs\calibration_menu_banner.txt" (
  type "%~dp0docs\calibration_menu_banner.txt"
) else (
  echo Real2Sim G1 Calibration Console
)
echo.
echo   [1]  Clear old calibration images
echo   [2]  Capture new ChArUco image pairs
echo   [3]  Delete weak pairs below 12 corners
echo   [4]  Compute stereo calibration
echo   [5]  Exit
echo.
echo   Recommended flow: 1 - 2 - 3 - 4
echo.
choice /c 12345 /n /m "Select mission [1/2/3/4/5]: "

if errorlevel 5 exit 0
if errorlevel 4 (
  call "%~dp0RUN_STEREO_CALIBRATION.bat"
  goto menu
)
if errorlevel 3 (
  call "%~dp0FILTER_WEAK_CALIBRATION_IMAGES.bat"
  goto menu
)
if errorlevel 2 (
  call "%~dp0CAPTURE_CALIBRATION_IMAGES.bat"
  goto menu
)
if errorlevel 1 (
  call "%~dp0CLEAR_CALIBRATION_IMAGES.bat"
  goto menu
)
