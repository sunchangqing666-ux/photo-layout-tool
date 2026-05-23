$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

$FallbackPython = "C:\Users\sunch\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if ($env:PYTHON) {
  $Python = $env:PYTHON
} elseif (Test-Path $FallbackPython) {
  $Python = $FallbackPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $Python = "python"
} else {
  throw "Python not found. Install Python or set the PYTHON environment variable."
}

& $Python -m pip install -r requirements.txt
& $Python -m pip install pyinstaller
& $Python -m PyInstaller `
  --noconfirm `
  --onefile `
  --windowed `
  --name PhotoLayoutTool `
  --icon assets\app.ico `
  --add-data "assets\app.ico;assets" `
  --add-data "assets\logo.png;assets" `
  --hidden-import windnd `
  --hidden-import win32print `
  --hidden-import win32ui `
  --hidden-import win32con `
  --hidden-import pywintypes `
  --hidden-import pythoncom `
  photo_layout_tool.py

Write-Host "Build complete: dist\PhotoLayoutTool.exe"
