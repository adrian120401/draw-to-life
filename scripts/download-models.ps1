$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) { throw "Ejecutá primero .\scripts\install.ps1" }
& $VenvPython -m draw_to_life.models download-models
if ($LASTEXITCODE -ne 0) { throw "Descarga incompleta. Podés ejecutar este script de nuevo para continuar." }
& $VenvPython -m draw_to_life.models doctor
if ($LASTEXITCODE -ne 0) { throw "Los modelos no pasaron la verificación. Revisá el diagnóstico." }
Write-Host "Modelos listos. Iniciá con .\scripts\start.ps1"
