@echo off
chcp 65001 >nul
cd /d "%~dp0"
call :find_python
if errorlevel 1 goto no_python

echo.
echo === 第一次使用：检查写作环境 ===
echo.
%PYTHON_CMD% tools\doctor.py
echo.
echo 如有 [缺少] 项，请按屏幕提示或 docs\BEGINNER_GUIDE.md 处理。
echo.
pause
exit /b 0

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
echo 安装后重新双击此文件。
echo.
pause
exit /b 1
