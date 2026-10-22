@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-cpu\Scripts\python.exe" (
 echo Run setup_windows.bat cpu first.
 exit /b 1
)
".venv-cpu\Scripts\python.exe" main.py --backend cpu %*
if errorlevel 1 pause
