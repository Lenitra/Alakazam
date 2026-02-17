@echo off
if not defined ALCASAR_LAUNCHED (
    set ALCASAR_LAUNCHED=1
    start "" conhost.exe cmd /k "%~f0"
    exit
)
title ALCASAR AUTO-CONNECT
mode con cols=50 lines=30
cd /d "%~dp0"
call .venv\Scripts\activate
python main.py
pause
