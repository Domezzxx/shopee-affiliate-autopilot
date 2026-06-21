# =====================================================================
#  watchdog.ps1  -  keep the backend server ALWAYS up (ASCII only)
#  - check http://127.0.0.1:8088/health
#  - if down OR hung -> kill stale + (re)start run_server.py (detached)
#  Run by Task "AffiliateAutopilotWatchdog" at logon + every 1 minute.
# =====================================================================
$root   = Split-Path -Parent $PSScriptRoot
$py     = Join-Path $root "venv\Scripts\python.exe"
$runner = Join-Path $root "scripts\run_server.py"
$log    = Join-Path $root "data\watchdog.log"
$ts     = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# 1) healthy? -> done
$healthy = $false
try { if ((Invoke-RestMethod "http://127.0.0.1:8088/health" -TimeoutSec 5 -ErrorAction Stop).status -eq "ok") { $healthy = $true } } catch {}
if ($healthy) { exit 0 }

# 2) down/hung -> log + kill anything stuck on 8088 (handles hangs) + restart
try { Add-Content -Path $log -Value "$ts DOWN -> restarting server" -ErrorAction SilentlyContinue } catch {}
try {
    $conns = Get-NetTCPConnection -LocalPort 8088 -State Listen -ErrorAction SilentlyContinue
    if ($conns) { $conns | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }
} catch {}
Start-Sleep -Milliseconds 800

# 3) start fresh (detached, hidden) — survives after this script exits
if (Test-Path $py) {
    Start-Process -FilePath $py -ArgumentList ('"' + $runner + '"') -WorkingDirectory $root -WindowStyle Hidden
    try { Add-Content -Path $log -Value "$ts started" -ErrorAction SilentlyContinue } catch {}
} else {
    try { Add-Content -Path $log -Value "$ts ERROR: venv python not found ($py)" -ErrorAction SilentlyContinue } catch {}
}
exit 0
