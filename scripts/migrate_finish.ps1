# =====================================================================
#  migrate_finish.ps1  -  ONE-CLICK finish migration on a NEW machine
#  ใช้ตอนย้ายเครื่อง: หลัง git clone + ก๊อป zip มาวางแล้ว -> รันตัวนี้ตัวเดียวจบ
#    1) แตก affiliate_migrate.zip  (.env + data: db/state/persona/products)
#    2) แตก affiliate_media.zip     (คลิป/รูปเก่า ถ้ามี) -> data\media
#    3) setup.ps1   (สร้าง venv + ลง dependency)
#    4) start.ps1   (รันเซิร์ฟเวอร์ + Chrome Flow + เปิดเว็บ)
#  หา zip จาก: โฟลเดอร์โปรเจกต์ / Downloads / Desktop / home
#  (ASCII only - Windows PowerShell 5.1)
# =====================================================================
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Write-Host "=== FINISH MIGRATION (new machine) ===" -ForegroundColor Cyan

$searchDirs = @($root, "$env:USERPROFILE\Downloads", "$env:USERPROFILE\Desktop", "$env:USERPROFILE")
function Find-Zip($name) {
    foreach ($d in $searchDirs) { $p = Join-Path $d $name; if (Test-Path $p) { return $p } }
    return $null
}

# 1) essential bundle (.env + data\...) -> extract into project root
$mig = Find-Zip "affiliate_migrate.zip"
if ($mig) {
    Write-Host "[1/4] extracting $mig -> project root" -ForegroundColor Cyan
    Expand-Archive -Path $mig -DestinationPath $root -Force
} else {
    Write-Host "[1/4] affiliate_migrate.zip NOT found -> .env/db will be missing!" -ForegroundColor Red
    Write-Host "      copy it (from old machine) into this folder, then re-run." -ForegroundColor Yellow
}

# 2) media bundle (media\...) -> extract into data\  (optional)
$media = Find-Zip "affiliate_media.zip"
if ($media) {
    Write-Host "[2/4] extracting media -> data\ (may take a minute)" -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path (Join-Path $root "data") | Out-Null
    Expand-Archive -Path $media -DestinationPath (Join-Path $root "data") -Force
} else {
    Write-Host "[2/4] affiliate_media.zip not found -> skip (clips regenerate later, OK)" -ForegroundColor Yellow
}

# verify .env
if (-not (Test-Path (Join-Path $root ".env"))) {
    Write-Host "WARNING: .env missing -> system runs in MOCK mode until you add keys" -ForegroundColor Red
}

# 3) native setup (venv + deps)
Write-Host "[3/4] running setup.ps1 ..." -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "setup.ps1")

# 4) start
Write-Host "[4/4] starting system ..." -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "start.ps1")

Write-Host ""
Write-Host "DONE. Web: http://127.0.0.1:8088/" -ForegroundColor Green
Write-Host "Last step: in the Chrome window that opened, LOG IN to Google Flow (labs.google/flow) once." -ForegroundColor Yellow
