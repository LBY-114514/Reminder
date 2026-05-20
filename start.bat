@echo off
cd /d "%~dp0"
where conda >nul 2>nul
if errorlevel 1 (
  echo Conda was not found in this command window.
  echo Please run this from Anaconda Prompt / Miniforge Prompt, or initialize Conda for cmd.exe.
  pause
  exit /b 1
)
call conda activate forskills
if errorlevel 1 (
  echo Failed to activate Conda environment: forskills
  echo Please make sure the forskills environment exists.
  pause
  exit /b 1
)
pythonw app.py
pause
