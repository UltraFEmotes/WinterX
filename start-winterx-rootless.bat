@echo off
rem Windows: WinterX on Android without root (see docs\rootless-android.md).
cd /d "%~dp0"
if "%WINTERX_PYTHON%"=="" (py -3 tools\rootless_launch.py start %*) else ("%WINTERX_PYTHON%" tools\rootless_launch.py start %*)
pause
