@echo off
chcp 65001 >nul
cd /d "%~dp0"
call :find_python
if errorlevel 1 goto no_python

echo.
echo === 检查论文 ===
echo.
%PYTHON_CMD% xit.py check
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo 检查完成。没有阻断构建的问题。
) else (
  echo 检查未通过。请先处理上面的第一条错误，再重新运行。
)
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
