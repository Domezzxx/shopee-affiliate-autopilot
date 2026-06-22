# ============================================================
#  เปิด Chrome โหมด Remote Debugging (port 9222) สำหรับ Google Flow
#  - ใช้ได้ทั้ง backend แบบ native และ Docker
#    (Docker Desktop forward host.docker.internal -> host 127.0.0.1:9222
#     ให้คอนเทนเนอร์ต่อ CDP ได้ — ไม่ต้อง bind 0.0.0.0)
#  Usage:  .\scripts\start_chrome_debug.ps1
# ============================================================
$root       = Split-Path -Parent $PSScriptRoot
$profileDir = Join-Path $root "data\chrome_profile"

$chromePath = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $chromePath) {
    Write-Host "[ERROR] ไม่พบ Google Chrome ในตำแหน่งมาตรฐาน" -ForegroundColor Red
    Write-Host "เปิดเองด้วยคำสั่ง:" -ForegroundColor Yellow
    Write-Host "  chrome.exe --remote-debugging-port=9222 --user-data-dir=`"$profileDir`"" -ForegroundColor Yellow
    exit 1
}

Write-Host "ปิด Chrome เดิมเพื่อเปิดโหมด Remote Debugging..." -ForegroundColor Yellow
taskkill /F /IM chrome.exe 2>&1 | Out-Null
Start-Sleep -Seconds 2

New-Item -ItemType Directory -Force -Path $profileDir | Out-Null

Write-Host "เปิด Chrome (port 9222)..." -ForegroundColor Green
Write-Host "Profile: $profileDir" -ForegroundColor Cyan
Write-Host "--------------------------------------------------" -ForegroundColor Gray
Write-Host "ล็อกอิน Google Flow ในหน้าต่างที่เปิดมา (ครั้งเดียว แล้วค้างไว้)" -ForegroundColor Green
Write-Host "--------------------------------------------------" -ForegroundColor Gray

Start-Process -FilePath $chromePath -ArgumentList "--remote-debugging-port=9222 --user-data-dir=`"$profileDir`" --no-first-run https://labs.google/fx/tools/flow"
