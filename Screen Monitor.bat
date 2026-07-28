@echo off
REM Double-click to open the live screening monitor.
REM Read-only: it watches data\screen_results.jsonl and never touches the run.
cd /d "%~dp0"
start "" pythonw screen_monitor.py %*
