param([string]$Python = "")
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# Aceptar un ejecutable explícito; si no, usar Python 3.11 de Windows.
if ($Python) {
    & $Python -c "import sys; assert sys.version_info[:2] == (3, 11), 'Se requiere Python 3.11'"
    if ($LASTEXITCODE -ne 0) { throw "Seleccioná un Python 3.11 válido." }
    & $Python -m venv .venv
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.11 -m venv .venv
} else {
    $FallbackPython = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"
    if (-not (Test-Path $FallbackPython)) { throw "Instalá Python 3.11 o pasá -Python 'C:\ruta\python.exe'." }
    & $FallbackPython -m venv .venv
}
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno virtual." }
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "No se pudo actualizar pip." }
& $VenvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias." }
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Write-Host "Dependencias listas. Descargá los modelos con .\scripts\download-models.ps1"
