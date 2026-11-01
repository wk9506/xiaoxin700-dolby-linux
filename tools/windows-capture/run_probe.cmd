@echo off
cd /d %~dp0stim
copy /Y ..\capture_dax.py . >nul
..\py\python312\python.exe capture_dax.py --stimulus stimulus_pink.wav --label off
echo.
echo Probe done (this file is reused by the OFF run, re-capturing is fine).
pause
