@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-cuda\Scripts\python.exe" (
 echo Run setup_windows.bat cuda first.
 exit /b 1
)
set "FT_NVIDIA=%~dp0.venv-cuda\Lib\site-packages\nvidia"
set "PATH=%FT_NVIDIA%\cudnn\bin;%FT_NVIDIA%\cublas\bin;%FT_NVIDIA%\cufft\bin;%FT_NVIDIA%\cuda_runtime\bin;%FT_NVIDIA%\cuda_nvrtc\bin;%FT_NVIDIA%\nvjitlink\bin;%PATH%"
".venv-cuda\Scripts\python.exe" main.py --backend cuda %*
if errorlevel 1 pause
