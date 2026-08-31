@echo off
title Train My AI - Setup
cd /d "%~dp0"

rem Setup runs on whatever Python the computer already has -- install.py is
rem stdlib-only precisely so it can. It builds its own private environment and
rem installs everything else into that.
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"

if not defined PY (
    echo.
    echo   Python is not installed on this computer, and setup needs it.
    echo.
    echo   1. Go to https://www.python.org/downloads/
    echo   2. Download Python 3.10 or newer.
    echo   3. IMPORTANT: tick "Add python.exe to PATH" in the installer.
    echo   4. Run this file again.
    echo.
    pause
    exit /b 1
)

"%PY%" "%~dp0install.py" %*
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
