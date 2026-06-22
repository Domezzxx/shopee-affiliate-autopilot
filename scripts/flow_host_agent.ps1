# ============================================================
#  Flow Host Agent (ASCII-only)
#  ตัวกลางบนโฮสต์: ให้ backend ที่อยู่ใน Docker สั่งเปิด Chrome (Google Flow,
#  remote-debugging 9222) บนเครื่องโฮสต์ได้ — ผ่าน "trigger file" ใน ./data ที่ mount ร่วมกัน
#    backend เขียน  data/.flow_launch_request  -> agent เห็น -> เปิด Chrome -> ลบ trigger
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
    if (Test-Cdp) { W "chrome 9222 already up - skip"; return }
    $exe = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $exe) { W "ERROR: chrome.exe not found"; return }
    New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
    # โปรไฟล์เฉพาะ (data/chrome_profile) = แยกจาก Chrome หลักของผู้ใช้ ไม่ต้อง kill อะไร
    Start-Process -FilePath $exe -ArgumentList "--remote-debugging-port=9222 --user-data-dir=`"$profileDir`" --no-first-run --no-default-browser-check https://labs.google/fx/tools/flow"
    W "launched chrome (debug profile, port 9222)"
}

New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
W "flow host agent started (watching $req)"
while ($true) {
    try {
        if (Test-Path $req) {
            Remove-Item $req -Force -ErrorAction SilentlyContinue
            W "launch request received"
            Launch-Flow
        }
    } catch { W "loop err: $($_.Exception.Message)" }
    Start-Sleep -Seconds 1
}
