@echo off
if "%REAL2SIM_MAXIMIZED%"=="1" exit /b 0
set "REAL2SIM_MAXIMIZED=1"
start "Real2Sim G1" /max "%~f1"
exit /b 1
