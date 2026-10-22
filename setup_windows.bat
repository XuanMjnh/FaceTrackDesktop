@echo off
setlocal
cd /d "%~dp0"
set "FT_MODE=%~1"
if "%FT_MODE%"=="" set "FT_MODE=cpu"
if /i "%FT_MODE%"=="cpu" goto valid
if /i "%FT_MODE%"=="cuda" goto valid
echo Usage: setup_windows.bat cpu ^| cuda
exit /b 1
:valid
set "FT_ENV=.venv-%FT_MODE%"
if not exist "%FT_ENV%\Scripts\python.exe" py -3.11 -m venv "%FT_ENV%"
if errorlevel 1 goto error
"%FT_ENV%\Scripts\python.exe" -c "import struct,sys; assert struct.calcsize('P')==8, 'Python x64 required'; assert sys.version_info[:2]==(3,11), 'Python 3.11 required'"
if errorlevel 1 goto error
"%FT_ENV%\Scripts\python.exe" -m pip install --upgrade "pip<26" setuptools wheel "Cython==3.0.11" "numpy==1.26.4"
if errorlevel 1 goto error
if /i "%FT_MODE%"=="cuda" goto gpu
"%FT_ENV%\Scripts\python.exe" -m pip install --no-build-isolation -r requirements.txt -r requirements-dev.txt
goto checked
:gpu
"%FT_ENV%\Scripts\python.exe" -m pip install --no-build-isolation -r requirements-cuda.txt -r requirements-dev.txt
:checked
if errorlevel 1 goto error
"%FT_ENV%\Scripts\python.exe" -m pip check
if errorlevel 1 goto error
echo Installed. Read README.md to install the model, then run_%FT_MODE%.bat
exit /b 0
:error
echo Installation failed. If InsightFace reports a missing C++ compiler, install VS 2022 Build Tools with Desktop development with C++, MSVC v143, and a Windows SDK.
echo Then run setup_windows.bat %FT_MODE% from the x64 Native Tools Command Prompt for VS 2022. Review the pip error above for other causes.
pause
exit /b 1
