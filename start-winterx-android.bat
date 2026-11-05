@echo off
rem Windows: start Spring with WinterX on a rooted device (see docs\rooted-android.md). Keep this window open.
cd /d "%~dp0"
if "%WINTERX_PYTHON%"=="" (py -3 tools\rooted_launch.py start %*) else ("%WINTERX_PYTHON%" tools\rooted_launch.py start %*)
pause
