param([switch]$Lan)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) { throw "Ejecutá primero .\scripts\install.ps1" }
if ($Lan) {
    $Port = & $VenvPython -c "from draw_to_life.config import Settings; print(Settings.from_env().port)"
    if ($LASTEXITCODE -ne 0) { throw "No se pudo leer la configuración." }
    # Direcciones de los adaptadores con una puerta de enlace real (no WSL).
    $Networks = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address }
    foreach ($Network in $Networks) {
        foreach ($Address in $Network.IPv4Address) {
            Write-Host "Abrí en tu teléfono, conectado a la misma Wi-Fi: http://$($Address.IPAddress):$Port" -ForegroundColor Magenta
        }
    }
    if (-not $Networks) { Write-Warning "No encontramos una red con puerta de enlace. Revisá la conexión Wi-Fi de la PC." }
    & $VenvPython app.py --lan
} else {
    & $VenvPython app.py
}
if ($LASTEXITCODE -ne 0) { throw "La aplicación no pudo iniciarse. Revisá el mensaje anterior." }
