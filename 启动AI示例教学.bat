@echo off
setlocal
set "XIT_ARCH=%PROCESSOR_ARCHITECTURE%"
if defined PROCESSOR_ARCHITEW6432 set "XIT_ARCH=%PROCESSOR_ARCHITEW6432%"
if /i "%XIT_ARCH%"=="x86" goto unsupported_system
cd /d "%~dp0markdown" || goto missing_project
if exist "%~dp0runtime\pandoc\pandoc.exe" set "XIT_PANDOC=%~dp0runtime\pandoc\pandoc.exe"

set "PYTHON_CMD="
if exist "%~dp0runtime\python\python.exe" set "PYTHON_CMD="%~dp0runtime\python\python.exe" -X utf8"
if defined PYTHON_CMD goto python_ready
for /f "delims=" %%P in ('where.exe python.exe 2^>nul') do call :try_python "%%P"
if defined PYTHON_CMD goto python_ready
py -3 -X utf8 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 goto no_python
set "PYTHON_CMD=py -3 -X utf8"

:python_ready
%PYTHON_CMD% -c "import yaml, bibtexparser" >nul 2>nul
if not errorlevel 1 goto launch
echo.
echo Installing PyYAML for the first launch. Internet access is required.
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto install_failed

:launch
%PYTHON_CMD% "%~dp0preflight.py"
if errorlevel 1 goto preflight_failed
echo.
echo Starting XIT Thesis Assistant. The browser will open automatically.
echo Keep this window open while using the assistant.
echo.
%PYTHON_CMD% assistant\app.py --project ai %*
if not errorlevel 1 exit /b 0
echo.
echo The assistant could not start. See the error above.
pause
exit /b 1

:no_python
echo.
echo Python 3.10 or newer was not found.
echo Install Python from https://www.python.org/downloads/
echo Select "Add Python to PATH", then run this launcher again.
echo.
pause
exit /b 1

:install_failed
echo.
echo PyYAML installation failed. Check your connection, then run:
echo python -m pip install -r requirements.txt
echo.
pause
exit /b 1

:missing_project
echo The markdown folder was not found. Extract the complete ZIP first.
pause
exit /b 1

:try_python
if defined PYTHON_CMD exit /b 0
"%~1" -X utf8 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 exit /b 0
set "PYTHON_CMD="%~1" -X utf8"
exit /b 0

:unsupported_system
echo This complete package needs Windows 10/11 x64, or Windows 11 ARM64 x64 emulation.
pause
exit /b 1

:preflight_failed
echo Startup checks failed. Fix the issue shown above, then retry.
pause
exit /b 1
