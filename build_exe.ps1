$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
  Write-Host "PyInstaller was not found."
  Write-Host "Install it first:"
  Write-Host "  pip install pyinstaller"
  exit 1
}

pyinstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name "挑战杯提醒" `
  --icon "assets\reminder-icon.ico" `
  --add-data "web;web" `
  --hidden-import "tkinter" `
  --hidden-import "tkinter.filedialog" `
  app.py

if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

Write-Host "Build complete: dist\挑战杯提醒.exe"
