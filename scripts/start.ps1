# =====================================================================
#  start.ps1  -  Start Affiliate Autopilot (one command, idempotent)
#  - start server :8088 (kill stale -> fresh, always latest code)
#  - start Chrome remote-debugging :9222 for Flow video (if not running)
#  - wait for health + show status (no guessing / no debugging needed)
#  Safe to run anytime:  ./scripts/start.ps1
#  (ASCII only — Windows PowerShell 5.1 ไม่รองรับ Thai/emoji ใน .ps1)
# =====================================================================
$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root "venv\Scripts\python.exe"
$dataDir = Join-Path $root "data"
$log = Join-Path $dataDir "server.log"
$env:DATA_DIR = $dataDir.Replace("\", "/")
$env:PYTHONIOENCODING = "utf-8"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

Write-Host "=== START Affiliate Autopilot ===" -ForegroundColor Cyan

# 1) Server :8088 -- kill stale + start fresh (always loads latest code)
$conn = Get-NetTCPConnection -LocalPort 8088 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "[1/3] server :8088 running -> restart fresh" -ForegroundColor Yellow
    $conn | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Start-Sleep 2
}
else {
    Write-Host "[1/3] starting server :8088 ..." -ForegroundColor Cyan
}
Start-Process -FilePath $py `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8088" `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput $log -RedirectStandardError "$log.err"

# 2) Chrome debug :9222 (Flow video) -- start only if not already up (idempotent)
$cdp = $false
try { $cdp = (Invoke-WebRequest "http://127.0.0.1:9222/json/version" -TimeoutSec 2 -UseBasicParsing).StatusCode -eq 200 } catch {}
if ($cdp) {
    Write-Host "[2/3] Chrome debug :9222 already up (Flow video ready)" -ForegroundColor Green
}
else {
    Write-Host "[2/3] starting Chrome debug :9222 for Flow video ..." -ForegroundColor Cyan
    $chrome = @("C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe") |
    Where-Object { Test-Path $_ } | Select-Object -First 1
    $profileDir = Join-Path $dataDir "chrome_profile"
    New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
    if ($chrome) {
        Start-Process -FilePath $chrome -ArgumentList "--remote-debugging-port=9222", "--user-data-dir=`"$profileDir`"", "--no-first-run", "https://labs.google/fx/tools/flow"
        Write-Host "    ** First time: log in to Google Flow in the Chrome window (profile is remembered) **" -ForegroundColor Yellow
    }
    else {
        Write-Host "    Chrome not found -> Flow video disabled (rest works fine)" -ForegroundColor Yellow
    }
}

# 3) wait for health + show status
Write-Host "[3/3] waiting for server ..." -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    try { if ((Invoke-RestMethod "http://127.0.0.1:8088/health" -TimeoutSec 2).status -eq "ok") { $ok = $true; break } } catch {}
    Start-Sleep 1
}
Write-Host ""
if ($ok) {
    $s = Invoke-RestMethod "http://127.0.0.1:8088/api/system"
    $h = $s.health
    $yn = { param($v) if ($v) { "YES" } else { "no" } }
    Write-Host "READY -> http://127.0.0.1:8088/" -ForegroundColor Green
    Write-Host ("   Automation: " + $(if ($s.enabled) { "ON" } else { "OFF (turn on in dashboard)" }))
    Write-Host ("   AI-write:$(& $yn $h.content_ai)  Flow-video:$(& $yn $h.flow_chrome)  Phones:$($h.phone_devices)")
    Write-Host ("   Pexels:$(& $yn $h.stock_video)  Freesound:$(& $yn $h.ambience_sfx)  YouTube:$(& $yn $h.youtube)  Meta:$(& $yn $h.meta)")
    Start-Process "http://127.0.0.1:8088/"
}
else {
    Write-Host "FAILED: server did not come up in 30s -- check log: $log" -ForegroundColor Red
}
