$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) { throw "Ejecutá primero .\scripts\install.ps1" }
& $VenvPython app.py
if ($LASTEXITCODE -ne 0) { throw "La aplicación no pudo iniciarse. Revisá el mensaje anterior." }
