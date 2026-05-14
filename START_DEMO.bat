@echo off
setlocal
call "%~dp0scripts\maximize_self.bat" "%~f0"
if errorlevel 1 exit /b
cd /d "%~dp0"
title Real2Sim G1 - SZTAKI Demo Console
color 0A
mode con: cols=110 lines=36 >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\set_console_compact.ps1" -FontSize 12 -Columns 110 -Rows 36 >nul 2>nul

:menu
cls
if exist "%~dp0docs\demo_menu_banner.txt" (
  type "%~dp0docs\demo_menu_banner.txt"
) else (
  echo Real2Sim G1 demo launcher
)
echo.
echo   [1]  Stable two-arm demo for submission
echo   [2]  Experimental full-body demo
echo   [3]  Exit
echo.
echo   Recommended for judging: start with [1], then show [2] as an extra.
echo.
choice /c 123 /n /m "Select demo [1/2/3]: "

if errorlevel 3 exit 0
if errorlevel 2 (
  call "%~dp0START_FULL_BODY.bat"
  goto menu
)

call "%~dp0START_ARMS_ONLY.bat"
goto menu
