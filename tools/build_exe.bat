@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv-cpu\Scripts\python.exe" exit /b 1
".venv-cpu\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onedir --windowed --name TimNguoi --icon "app\ui\assets\branding.ico" --collect-all insightface --collect-all onnxruntime --collect-all skimage --add-data "app\ui\assets\fonts;app\ui\assets\fonts" main.py
if errorlevel 1 exit /b 1
echo Build at dist\TimNguoi. Install model separately; data belongs in the user profile.
