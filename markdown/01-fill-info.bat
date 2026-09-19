@echo off
chcp 65001 >nul
cd /d "%~dp0"
call :find_python
if errorlevel 1 goto no_python

echo.
echo === 填写论文基本信息 ===
echo.
%PYTHON_CMD% xit.py setup
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%

:find_python
set "PYTHON_CMD=python"
where python >nul 2>nul
if not errorlevel 1 exit /b 0
where py >nul 2>nul
if errorlevel 1 exit /b 1
set "PYTHON_CMD=py -3"
exit /b 0

:no_python
echo.
echo [错误] 没有找到 Python 3。请先安装 Python 3.10 或更高版本。
echo.
pause
exit /b 1
