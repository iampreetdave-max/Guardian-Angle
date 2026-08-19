# Keep the hosted demo awake by polling it.
#
# Codespaces measures inactivity by connection to the EDITOR, not by traffic to a
# forwarded port. So judges opening your link does NOT reset the idle timer, and
# the codespace stops mid-demo. Keeping the codespace browser tab open is the
# real fix; this is the belt-and-braces version for when you cannot babysit it.
#
# It also keeps the app warm: the first request after a quiet spell pays for
# model load, so a judge's click should never be the request that wakes it.
#
# Run it in its own terminal before you present and leave it running:
#   .\deploy\keepalive.ps1 -Url https://YOUR-CODESPACE-8080.app.github.dev
#   .\deploy\keepalive.ps1 -Url <url> -IntervalSeconds 120

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Url,
    [int]$IntervalSeconds = 180
)

$ErrorActionPreference = "Continue"
$Url = $Url.TrimEnd('/')

Write-Host ""
Write-Host "Keeping the demo awake" -ForegroundColor Cyan
Write-Host "  $Url"
Write-Host "  polling every $IntervalSeconds seconds - Ctrl+C to stop"
Write-Host ""

$fails = 0
while ($true) {
    $stamp = Get-Date -Format "HH:mm:ss"
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $r = Invoke-WebRequest -UseBasicParsing -Uri "$Url/api/health" -TimeoutSec 45
        $sw.Stop()
        $ms = $sw.ElapsedMilliseconds
        if ($r.StatusCode -eq 200) {
            $fails = 0
            Write-Host "  $stamp  awake - $ms ms" -ForegroundColor Green
        }
        else {
            $code = $r.StatusCode
            Write-Host "  $stamp  HTTP $code" -ForegroundColor Yellow
        }
    }
    catch {
        $fails++
        $msg = $_.Exception.Message
        Write-Host "  $stamp  unreachable, fail $fails - $msg" -ForegroundColor Red
        if ($fails -eq 3) {
            Write-Host ""
            Write-Host "  The codespace looks stopped. Polling cannot restart it." -ForegroundColor Yellow
            Write-Host "  Open the codespace in the browser to bring it back." -ForegroundColor Yellow
            Write-Host ""
        }
    }
    Start-Sleep -Seconds $IntervalSeconds
}
