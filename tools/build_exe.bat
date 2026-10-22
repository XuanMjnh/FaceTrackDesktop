@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv-cpu\Scripts\python.exe" exit /b 1
".venv-cpu\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onedir --windowed --name FaceTrackDesktop --collect-all insightface --collect-all onnxruntime --collect-all skimage main.py
if errorlevel 1 exit /b 1
echo Build at dist\FaceTrackDesktop. Install model separately; data belongs in the user profile.
