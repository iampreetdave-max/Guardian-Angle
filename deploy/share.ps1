<#
.SYNOPSIS
    Put the locally-running CityShield / VisionScan on a public HTTPS URL.

.DESCRIPTION
    Demo-day insurance. Starts the stack if it isn't already up, then opens a
    Cloudflare Quick Tunnel to the frontend and prints the public URL.

    No Cloudflare account, no domain, no credit card, no DNS setup.

    This works because the frontend is same-origin: src/api.js uses
    baseURL "/api" and nginx.conf proxies /api/ and /thumbnails/ to the backend
    container. Tunnelling the single frontend port therefore exposes the entire
    application, backend included.

    Known limits of a Quick Tunnel (none of which affect a judged demo):
      * the URL is random and changes every run - copy it fresh on the day
      * no Server-Sent Events (this app uses none)
      * ~200 concurrent in-flight requests
      * no SLA; Cloudflare bills it as "testing and development only"

.EXAMPLE
    .\deploy\share.ps1
    .\deploy\share.ps1 -Port 8080
#>
[CmdletBinding()]
param(
    [int]$Port = 0,
    [switch]$SkipStart
)

$ErrorActionPreference = "Continue"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

function Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "    $m" -ForegroundColor Green }
function Warn($m) { Write-Host "    $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "`nERROR: $m" -ForegroundColor Red; exit 1 }

# Frontend host port: -Port wins, else .env, else the compose default.
if ($Port -eq 0) {
    $Port = 8080
    if (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match '^\s*FRONTEND_PORT\s*=\s*(\d+)') { $Port = [int]$Matches[1] }
        }
    }
}

$exe = Join-Path $PSScriptRoot "tools\cloudflared.exe"
if (-not (Test-Path $exe)) {
    Step "cloudflared not found - downloading (~55 MB, one time)"
    New-Item -ItemType Directory -Force (Split-Path $exe) | Out-Null
    try {
        Invoke-WebRequest -UseBasicParsing -Uri `
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" `
            -OutFile $exe
        Ok "cloudflared downloaded."
    } catch {
        Die "Could not download cloudflared. $($_.Exception.Message)"
    }
}

# ---- make sure the app is actually up before we publish it -----------------
if (-not $SkipStart) {
    $up = $false
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:$Port" -TimeoutSec 5
        $up = ($r.StatusCode -eq 200)
    } catch { }

    if (-not $up) {
        Step "App is not responding on port $Port - starting the stack"
        & (Join-Path $root "start.ps1")
    } else {
        Ok "App already running on port $Port."
    }
}

# Publishing a URL that serves an error page is worse than not publishing one.
try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:$Port" -TimeoutSec 10
    if ($r.StatusCode -ne 200) { Die "App on port $Port returned HTTP $($r.StatusCode)." }
} catch {
    Die "Nothing is serving http://localhost:$Port. Run .\start.ps1 first."
}

Step "Opening the public tunnel (Ctrl+C to close it)"
Warn "The URL below is live only while this window stays open."
Warn "It also dies if the laptop sleeps, closes, or drops Wi-Fi - everything is"
Warn "served from this machine. And it is a NEW random URL every run, so"
Warn "generate it on the day rather than putting it on a slide in advance."
Write-Host ""

# cloudflared writes the assigned hostname to stderr; surface it prominently
# rather than making the user spot it in the banner.
$found = $false
# --protocol http2 is deliberate. The default QUIC transport failed here in a
# retry loop ("control stream encountered a failure while serving" /
# "failed to run the datagram handler: context canceled") — UDP is throttled on
# some networks, and cloudflared reports the tunnel as registered while it
# actually serves HTTP 530. http2 connects first try.
& $exe tunnel --url "http://localhost:$Port" --protocol http2 --no-autoupdate 2>&1 | ForEach-Object {
    $line = "$_"
    if (-not $found -and $line -match 'https://[a-z0-9-]+\.trycloudflare\.com') {
        $found = $true
        $url = $Matches[0]
        Write-Host ""
        Write-Host "  ============================================================" -ForegroundColor Green
        Write-Host "   PUBLIC DEMO URL:  $url" -ForegroundColor Green
        Write-Host "  ============================================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "   Demo accounts (password = role + 123):" -ForegroundColor Magenta
        Write-Host "     admin@city.gov / admin123      lead@city.gov / lead123"
        Write-Host "     officer@city.gov / officer123   citizen\@example.com / citizen123"
        Write-Host ""
        Write-Host "   Open it once yourself before sharing - the first request"
        Write-Host "   warms the tunnel and confirms it is really reachable."
        Write-Host ""
        try { Set-Clipboard -Value $url; Write-Host "   (copied to clipboard)" -ForegroundColor DarkGray } catch { }
        Write-Host ""
    }
    Write-Host $line -ForegroundColor DarkGray
}
