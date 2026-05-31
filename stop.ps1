<#
.SYNOPSIS
    Stop the CityShield / VisionScan stack.
.EXAMPLE
    .\stop.ps1            # stop containers (data + models are kept)
    .\stop.ps1 -Wipe      # stop AND delete all data/model volumes (full reset)
#>
[CmdletBinding()]
param([switch]$Wipe)

# 'Continue' (not 'Stop'): docker writes progress to stderr, which under 'Stop'
# would be turned into a fatal error by Windows PowerShell.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

if ($Wipe) {
    Write-Host "==> Stopping and DELETING all volumes (cases, videos, models)..." -ForegroundColor Yellow
    docker compose down -v
} else {
    Write-Host "==> Stopping containers (data and downloaded models are preserved)..." -ForegroundColor Cyan
    docker compose down
}
Write-Host "Done. Restart any time with .\start.ps1" -ForegroundColor Green
