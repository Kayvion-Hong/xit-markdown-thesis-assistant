@echo off
chcp 65001 >nul
cd /d "%~dp0"
call :find_python
if errorlevel 1 goto no_python

echo.
echo === 生成毕业论文 PDF ===
echo.
%PYTHON_CMD% xit.py pdf
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" goto failed

echo.
echo PDF 已生成：build\thesis.pdf
if exist "build\thesis.pdf" start "" "build\thesis.pdf"
echo.
pause
exit /b 0

:failed
echo.
echo 生成失败。优先查看屏幕上的第一条错误。
echo 也可以双击 00-first-check.bat 检查环境。
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
