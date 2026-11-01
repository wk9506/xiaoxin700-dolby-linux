@echo off
cd /d %~dp0stim
copy /Y ..\capture_dax.py . >nul
for %%s in (sweep sweep_quiet pink pink_quiet multitone) do ..\py\python312\python.exe capture_dax.py --stimulus stimulus_%%s.wav --label dynamic
echo.
echo dynamic capture done. Files: stim\captures\loopback_*_dynamic.wav
pause
