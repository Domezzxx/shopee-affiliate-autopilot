# =====================================================================
#  watchdog_docker.ps1  -  keep the DOCKER stack ALWAYS up (ASCII only)
#  - ensure Docker engine is up (start Docker Desktop if needed)
#  - docker compose up -d   (idempotent: restart stopped/missing containers)
#  - if backend container reports HEALTH=unhealthy -> restart it
#  Health is read from the container's own healthcheck (docker inspect),
#  NOT an external HTTP call -> avoids WSL mirrored-mode loopback issues.
#  Run by Task "AffiliateAutopilotDockerWatchdog" at logon + every 1 minute.
# =====================================================================
$root = Split-Path -Parent $PSScriptRoot
$log  = Join-Path $root "data\watchdog_docker.log"
$ts   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
function W([string]$m) { try { Add-Content -Path $log -Value "$ts $m" -ErrorAction SilentlyContinue } catch {} }

# 0) resolve docker.exe (PATH first, then Docker Desktop default bin)
$docker = (Get-Command docker -ErrorAction SilentlyContinue).Source
if (-not $docker) { $docker = Join-Path $env:ProgramFiles "Docker\Docker\resources\bin\docker.exe" }
if (-not (Test-Path $docker)) { W "ERROR: docker.exe not found"; exit 0 }

# 1) engine up?  (empty/err output = down)
$srv = & $docker version --format "{{.Server.Version}}" 2>$null
if (-not $srv) {
    $dd = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (Get-Process "Docker Desktop" -ErrorAction SilentlyContinue) {
        W "engine starting (Docker Desktop running) - wait for next tick"
    } elseif (Test-Path $dd) {
        Start-Process $dd
        W "engine DOWN -> started Docker Desktop"
    } else {
        W "ERROR: Docker Desktop.exe not found"
    }
    exit 0   # next tick continues once engine is ready
}

# 2) ensure whole stack is up (no-op if already running)
Set-Location $root
$up = & $docker compose up -d 2>&1
$acted = $up | Select-String "Started|Starting|Recreate|Created"
if ($acted) { W ("stack heal -> " + (($acted | ForEach-Object { $_.ToString().Trim() }) -join " | ")) }

# 3) heal backend if its own healthcheck says unhealthy
$h = (& $docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" affiliate-backend 2>$null)
if ($null -ne $h) { $h = ("$h").Trim() }
switch ($h) {
    "unhealthy" { W "backend UNHEALTHY -> restart"; $null = & $docker compose restart backend 2>&1 }
    ""          { W "backend container MISSING -> up -d recreate"; $null = & $docker compose up -d backend 2>&1 }
    default     { }   # healthy / starting / none -> leave alone
}
exit 0
