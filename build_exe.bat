@echo off
cd /d "%~dp0"

where pyinstaller >nul 2>nul
if errorlevel 1 (
  echo PyInstaller was not found.
  echo Install it first:
  echo   pip install pyinstaller
  pause
  exit /b 1
)

pyinstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --name "?????" ^
  --icon "assets\reminder-icon.ico" ^
  --add-data "web;web" ^
  app.py

if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)

echo Build complete: dist\?????.exe
pause
