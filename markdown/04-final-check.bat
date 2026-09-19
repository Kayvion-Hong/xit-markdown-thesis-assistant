@echo off
chcp 65001 >nul
cd /d "%~dp0"
call :find_python
if errorlevel 1 goto no_python

echo.
echo === 定稿前严格检查 ===
echo.
%PYTHON_CMD% xit.py final-check
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo 严格检查通过。仍请人工检查最终 PDF 的版式。
) else (
  echo 定稿检查未通过，请处理上面的提醒或错误。
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
