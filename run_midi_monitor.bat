@echo off
cd /d "%~dp0"
set PYTHONPATH=%CD%\vendor
"C:\Users\Albertxie.DESKTOP-BID7N0E\.workbuddy\binaries\python\versions\3.11.9\python.exe" tools\midi_monitor.py
pause
