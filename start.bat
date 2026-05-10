@echo off
cd /d "%~dp0"
call conda activate forskills
python app.py
pause
