@echo off
cd /d "%~dp0"
set PYTHONPATH=%CD%\vendor
set DEBUG_LEDS=1
set DEBUG_NAV=1
"C:\Users\Albertxie.DESKTOP-BID7N0E\.workbuddy\binaries\python\versions\3.11.9\python.exe" xair-remote.py 169.254.53.169
pause
