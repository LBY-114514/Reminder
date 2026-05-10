@echo off
cd /d "%~dp0"
call conda activate forskills
if errorlevel 1 (
  echo 无法激活 Conda 环境 forskills，请确认已安装 Conda 并创建该环境。
  pause
  exit /b 1
)
python app.py
pause
