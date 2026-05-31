<#
.SYNOPSIS
    CityShield / VisionScan - one-command launcher for Windows.

.DESCRIPTION
    Starts the entire stack in Docker with a single command. It will:
      1. Verify Docker is installed and start Docker Desktop if it isn't running.
      2. Create a .env (with a freshly generated JWT secret) on first run.
      3. Build + start the backend and frontend containers.
      4. Wait until the backend is healthy, then open the app in your browser.

.EXAMPLE
    .\start.ps1            # build + start + open browser
    .\start.ps1 -Logs      # ...then stream container logs
    .\start.ps1 -Rebuild   # force a clean rebuild (use after dependency changes)
#>
[CmdletBinding()]
param(
    [switch]$Logs,
    [switch]$Rebuild
)

# NOTE: deliberately NOT 'Stop'. Docker CLI commands print progress to stderr,
# and under 'Stop' Windows PowerShell turns that into a fatal NativeCommandError.
# We check $LASTEXITCODE explicitly after each command instead.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

function Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "    $m" -ForegroundColor Green }
function Warn($m) { Write-Host "    $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "`nERROR: $m" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------------------
# 1. Docker installed?
# ---------------------------------------------------------------------------
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Die "Docker is not installed. Get Docker Desktop: https://www.docker.com/products/docker-desktop/"
}

function Test-DockerUp {
    # Run through cmd so PowerShell never sees Docker's stderr (which, under
    # $ErrorActionPreference='Stop', would otherwise throw a NativeCommandError
    # when the daemon is down). We only care about the exit code.
    cmd /c "docker info >nul 2>nul"
    return ($LASTEXITCODE -eq 0)
}

# ---------------------------------------------------------------------------
# 2. Docker daemon running? If not, launch Docker Desktop and wait.
# ---------------------------------------------------------------------------
if (-not (Test-DockerUp)) {
    Step "Docker daemon is not running - starting Docker Desktop..."
    $candidates = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )
    $exe = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($exe) { Start-Process $exe } else { Warn "Could not find Docker Desktop.exe - start it manually." }

    $deadline = (Get-Date).AddMinutes(3)
    while (-not (Test-DockerUp)) {
        if ((Get-Date) -gt $deadline) { Die "Docker did not start within 3 minutes. Start Docker Desktop and re-run." }
        Start-Sleep -Seconds 3
        Write-Host "." -NoNewline
    }
    Write-Host ""
    Ok "Docker is ready."
}

# ---------------------------------------------------------------------------
# 3. .env bootstrap (generate a strong JWT secret on first run)
# ---------------------------------------------------------------------------
if (-not (Test-Path ".env")) {
    Step "First run - creating .env from .env.example"
    try {
        Copy-Item ".env.example" ".env" -ErrorAction Stop
        $chars  = ((48..57) + (65..90) + (97..122)) | ForEach-Object { [char]$_ }
        $secret = -join (1..48 | ForEach-Object { $chars | Get-Random })
        (Get-Content ".env") -replace 'VISIONSCAN_JWT_SECRET=.*', "VISIONSCAN_JWT_SECRET=$secret" | Set-Content ".env"
        Ok "Generated a random JWT secret. Edit .env to add a Gemini key or SMTP if you want them."
    } catch {
        Die "Could not create .env (is .env.example present?). $($_.Exception.Message)"
    }
}

# Read host ports from .env (fallback to defaults) for the URLs we print/open.
$frontPort = 8080
$backPort  = 8000
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*FRONTEND_PORT\s*=\s*(\d+)') { $frontPort = $Matches[1] }
        if ($_ -match '^\s*BACKEND_PORT\s*=\s*(\d+)')  { $backPort  = $Matches[1] }
    }
}

# ---------------------------------------------------------------------------
# 4. Build + start
# ---------------------------------------------------------------------------
if ($Rebuild) {
    Step "Rebuilding images from scratch (no cache)..."
    docker compose build --no-cache
    if ($LASTEXITCODE -ne 0) { Die "docker compose build failed." }
}

Step "Starting the stack..."
Warn "First run pulls base images, downloads AI models and compiles the face engine."
Warn "That can take 10-15 minutes. Subsequent starts are seconds."
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { Die "docker compose up failed. See: docker compose logs" }

# ---------------------------------------------------------------------------
# 5. Wait for health, then open the browser
# ---------------------------------------------------------------------------
Step "Waiting for the backend to become healthy..."
$health   = "http://localhost:$backPort/api/health"
$frontUrl = "http://localhost:$frontPort"
$deadline = (Get-Date).AddMinutes(6)
$ready    = $false
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri $health -TimeoutSec 5
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 4
    Write-Host "." -NoNewline
}
Write-Host ""

if ($ready) {
    Step "CityShield is up and running!"
    Write-Host ""
    Ok "App ............ $frontUrl"
    Ok "API docs ....... http://localhost:$backPort/docs"
    Write-Host ""
    Write-Host "    Demo accounts (password = role + 123):" -ForegroundColor Magenta
    Write-Host "      admin@city.gov / admin123       lead@city.gov / lead123"
    Write-Host "      officer@city.gov / officer123    citizen@example.com / citizen123"
    Write-Host ""
    Write-Host "    Stop with:  .\stop.ps1        Logs with:  docker compose logs -f"
    Start-Process $frontUrl
} else {
    Warn "Backend hasn't reported healthy yet (models may still be downloading)."
    Warn "Watch progress with:  docker compose logs -f backend"
    Warn "Then open:            $frontUrl"
}

if ($Logs) {
    Step "Streaming logs (Ctrl+C to stop; containers keep running)..."
    docker compose logs -f
}
