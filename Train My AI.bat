@echo off
title Train My AI
cd /d "%~dp0"
"%~dp0..\.venv-train\Scripts\python.exe" "%~dp0start_studio.py"
if errorlevel 1 pause
