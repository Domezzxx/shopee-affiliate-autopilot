# ============================================================
#  Flow Host Agent (ASCII-only) — keeper + singleton
#  ตัวกลางบนโฮสต์: ทำให้ Chrome (Google Flow, remote-debugging 9222) "พร้อมเสมอ"
#   - keeper: ถ้า Chrome 9222 ดับ -> เปิดให้เองอัตโนมัติ (มี cooldown กันสแปม)
#   - on-demand: backend (ใน Docker) เขียน data/.flow_launch_request -> เปิดทันที
#   - singleton: ตอนเริ่มจะฆ่า agent ตัวเก่าทิ้ง เหลือตัวเดียว (กันแย่ง profile)
#  รันค้างเป็น Scheduled Task (ดู install_flow_host_agent.ps1)
# ============================================================
$ErrorActionPreference = "Continue"
$root       = Split-Path -Parent $PSScriptRoot
$dataDir    = Join-Path $root "data"
$req        = Join-Path $dataDir ".flow_launch_request"
$profileDir = Join-Path $dataDir "chrome_profile"
$log        = Join-Path $dataDir "flow_host_agent.log"

function W([string]$m) { try { Add-Content -Path $log -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" -ErrorAction SilentlyContinue } catch {} }

function Test-Cdp {
    try { return ((Invoke-WebRequest "http://127.0.0.1:9222/json/version" -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200) }
    catch { return $false }
}

function Launch-Flow {
    if (Test-Cdp) { return }
    $exe = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $exe) { W "ERROR: chrome.exe not found"; return }
    New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
    Start-Process -FilePath $exe -ArgumentList "--remote-debugging-port=9222 --user-data-dir=`"$profileDir`" --no-first-run --no-default-browser-check https://labs.google/fx/tools/flow"
    W "launched chrome (debug profile, port 9222)"
}

# --- singleton: ฆ่า agent ตัวอื่นทิ้ง เหลือเฉพาะตัวนี้ ---
try {
    Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'flow_host_agent' -and $_.ProcessId -ne $PID } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
} catch {}
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
"$PID" | Out-File (Join-Path $dataDir ".flow_agent.pid") -Encoding ascii -Force
W "flow host agent started (keeper+singleton, pid $PID)"

$lastLaunch = (Get-Date).AddMinutes(-1)
while ($true) {
    try {
        $force = $false
        if (Test-Path $req) { Remove-Item $req -Force -ErrorAction SilentlyContinue; W "launch request"; $force = $true }
        if (-not (Test-Cdp)) {
            if ($force -or ((Get-Date) - $lastLaunch).TotalSeconds -gt 20) {
                Launch-Flow
                $lastLaunch = Get-Date
            }
        }
    } catch { W "loop err: $($_.Exception.Message)" }
    Start-Sleep -Seconds 5
}
