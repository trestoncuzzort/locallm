@echo off
title Check My Computer
cd /d "%~dp0"
"%~dp0..\.venv-train\Scripts\python.exe" "%~dp0check_my_computer.py"
pause
