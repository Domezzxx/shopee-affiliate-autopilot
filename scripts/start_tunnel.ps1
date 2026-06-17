# =====================================================================
#  start_tunnel.ps1  -  เปิด public URL ฟรีให้ /media (จำเป็นสำหรับ IG Reels)
#  ใช้ cloudflared quick tunnel (ฟรี ไม่ต้องสมัคร ไม่ต้องล็อกอิน)
#  - โหลด cloudflared.exe อัตโนมัติถ้ายังไม่มี (เป็นไฟล์เดี่ยว ไม่ต้องติดตั้ง)
#  - เปิด tunnel ชี้ไปที่ http://localhost:8088
#  - ดึง URL https://xxxx.trycloudflare.com มาเขียนลง .env (PUBLIC_BASE_URL)
#  วิธีใช้ (PowerShell):  ./scripts/start_tunnel.ps1
#  เปิดทิ้งไว้ขณะโพสต์ IG — ปิดหน้าต่างนี้ = tunnel หยุด
# =====================================================================
$ErrorActionPreference = "Stop"
$root  = Split-Path -Parent $PSScriptRoot
$exe   = Join-Path $PSScriptRoot "cloudflared.exe"
$envf  = Join-Path $root ".env"
$logf  = Join-Path $PSScriptRoot "cloudflared.log"
$port  = 8088

if (-not (Test-Path $exe)) {
    Write-Host "[1/3] โหลด cloudflared.exe (ครั้งแรกเท่านั้น ~17MB)..." -ForegroundColor Cyan
    $url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    Invoke-WebRequest -Uri $url -OutFile $exe
    Write-Host "    เสร็จ -> $exe" -ForegroundColor Green
} else {
    Write-Host "[1/3] พบ cloudflared.exe แล้ว" -ForegroundColor Green
}

# เช็คว่า server :8088 รันอยู่ไหม
try { Invoke-RestMethod "http://127.0.0.1:$port/health" -TimeoutSec 3 | Out-Null }
catch { Write-Host "เตือน: ไม่พบ server ที่ :$port  (รัน ./run_local.ps1 ก่อน)" -ForegroundColor Yellow }

if (Test-Path $logf) { Remove-Item $logf -Force }
# ใช้ 127.0.0.1 (ไม่ใช่ localhost — กัน IPv6 ::1 ที่ uvicorn ไม่ฟัง)
# --protocol http2 : บางเครือข่ายบล็อก QUIC/UDP 7844 -> ต้อง http2 ไม่งั้นได้ 530
Write-Host "[2/3] เปิด cloudflared tunnel -> http://127.0.0.1:$port (http2) ..." -ForegroundColor Cyan
$proc = Start-Process -FilePath $exe `
    -ArgumentList "tunnel","--url","http://127.0.0.1:$port","--protocol","http2","--logfile",$logf `
    -PassThru -WindowStyle Hidden

# รอ URL โผล่ใน log (สูงสุด 30 วิ)
$pubUrl = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep 1
    if (Test-Path $logf) {
        $m = Select-String -Path $logf -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($m) { $pubUrl = $m.Matches[0].Value; break }
    }
}

if (-not $pubUrl) {
    Write-Host "ไม่พบ public URL ใน 30 วิ — ดู log: $logf" -ForegroundColor Red
    exit 1
}

# เขียน/อัปเดต PUBLIC_BASE_URL ใน .env
Write-Host "[3/3] public URL = $pubUrl" -ForegroundColor Green
if (Test-Path $envf) {
    $lines = Get-Content $envf
    if ($lines -match "^PUBLIC_BASE_URL=") {
        $lines = $lines -replace "^PUBLIC_BASE_URL=.*", "PUBLIC_BASE_URL=$pubUrl"
    } else {
        $lines += "PUBLIC_BASE_URL=$pubUrl"
    }
    Set-Content -Path $envf -Value $lines -Encoding UTF8
    Write-Host "    เขียนลง .env แล้ว (PUBLIC_BASE_URL)" -ForegroundColor Green
} else {
    Write-Host "    ไม่พบ .env — ตั้งเอง: PUBLIC_BASE_URL=$pubUrl" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "พร้อมโพสต์ IG แล้ว! ทดสอบสื่อ public:" -ForegroundColor Cyan
Write-Host "  $pubUrl/media/<ชื่อไฟล์>" -ForegroundColor White
Write-Host "** restart server เพื่อให้โหลด PUBLIC_BASE_URL ใหม่ **" -ForegroundColor Yellow
Write-Host "เปิดหน้าต่างนี้ทิ้งไว้ขณะโพสต์ (Ctrl+C = หยุด tunnel). PID=$($proc.Id)" -ForegroundColor DarkGray
Wait-Process -Id $proc.Id
