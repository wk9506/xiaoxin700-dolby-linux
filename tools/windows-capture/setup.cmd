@echo off
setlocal
cd /d %~dp0

echo === [1/4] unzip portable python ===
if not exist py\python312 mkdir py\python312
py\python312\python.exe --version >nul 2>&1
if errorlevel 1 (
  tar -xf py\python-embed.zip -C py\python312
  if not exist py\python312\python.exe powershell -NoProfile -Command "Expand-Archive -LiteralPath 'py\python-embed.zip' -DestinationPath 'py\python312' -Force"
)
if not exist py\python312\python.exe (echo FAIL: python.exe not found & pause & exit /b 1)

echo === [2/4] enable site-packages in embeddable python ===
> py\python312\python312._pth echo python312.zip
>> py\python312\python312._pth echo .
>> py\python312\python312._pth echo Lib\site-packages
>> py\python312\python312._pth echo import site

echo === [3/4] bootstrap pip offline ===
py\python312\python.exe py\get-pip.py --no-index --find-links py\wheels --no-setuptools --no-wheel --no-warn-script-location
if errorlevel 1 (echo FAIL: pip bootstrap & pause & exit /b 1)

echo === [4/4] install deps offline ===
py\python312\python.exe -m pip install --no-index --find-links py\wheels --no-warn-script-location numpy scipy soundfile sounddevice pycaw comtypes pyaudiowpatch
if errorlevel 1 (echo FAIL: deps install & pause & exit /b 1)

echo.
py\python312\python.exe -c "import numpy, scipy, soundfile, sounddevice, pycaw, pyaudiowpatch; print('[ALL DEPS OK]')"
echo.
echo If you saw [ALL DEPS OK], setup is done. Read the checklist file.
pause
