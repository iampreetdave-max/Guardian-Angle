# VisionScan — expose the locally-running app via a free Cloudflare Quick Tunnel.
#
# Use on demo day: run the stack locally (full hardware = fast, face-matching
# works, no cold start), then share a public https URL with judges.
#
#   1. Start the app:   docker compose up --build      (serves UI on :8080)
#      …or for local dev without Docker, run backend (:8000) + `npm run dev`
#      and set $Port = 5173 below.
#   2. Run this script: .\deploy\tunnel.ps1
#
# It auto-installs cloudflared via winget if missing. No Cloudflare account or
# domain is required — you get a random https://<name>.trycloudflare.com URL.

param(
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"

function Test-Cmd($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

if (-not (Test-Cmd "cloudflared")) {
    Write-Host "cloudflared not found — attempting install via winget…" -ForegroundColor Yellow
    if (Test-Cmd "winget") {
        winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
    } else {
        Write-Host "winget unavailable. Install cloudflared manually:" -ForegroundColor Red
        Write-Host "  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        exit 1
    }
}

Write-Host "Exposing http://localhost:$Port via Cloudflare Quick Tunnel…" -ForegroundColor Cyan
Write-Host "Share the https://<...>.trycloudflare.com URL it prints below." -ForegroundColor Green
cloudflared tunnel --url "http://localhost:$Port"
