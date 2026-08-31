@echo off
title Train My AI
cd /d "%~dp0"

rem Find the Python that has torch installed. INSTALL.bat builds .venv next to
rem this file; a development checkout has one a level up. Neither is assumed --
rem if there is no usable Python this stops and says what to run. The previous
rem version pointed at a fixed path and, when that path was missing, printed
rem "The system cannot find the path specified" and STILL EXITED 0.
set "PY="
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if not defined PY if exist "%~dp0..\.venv-train\Scripts\python.exe" set "PY=%~dp0..\.venv-train\Scripts\python.exe"

if not defined PY (
    echo.
    echo   This app is not set up on this computer yet.
    echo.
    echo   Run INSTALL.bat in this folder first. It installs what is needed
    echo   and picks the right version for your graphics card.
    echo.
    pause
    exit /b 1
)

"%PY%" "%~dp0start_studio.py"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
    echo.
    echo   Train My AI stopped with an error ^(code %RC%^).
    pause
)
exit /b %RC%
