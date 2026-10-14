$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) { throw "Ejecutá primero scripts/install.ps1" }
& $VenvPython -m draw_to_life.models download-models
if ($LASTEXITCODE -ne 0) { throw "No se pudieron preparar los modelos." }
& $VenvPython scripts/prepare_characters.py @args
if ($LASTEXITCODE -ne 0) { throw "El catálogo quedó pendiente. Repetí el comando para reanudar." }
