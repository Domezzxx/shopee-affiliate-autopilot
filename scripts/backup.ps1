# ============================================================
#  💾 Backup ฐานข้อมูล n8n (Postgres) ออกมาเป็นไฟล์ .sql
#  - เขียนทับ  ./data/db_init/01-restore.sql  → ใช้ "auto-restore" ตอนย้ายเครื่อง
#  - เก็บสำเนาพร้อม timestamp ไว้ใน ./data/backups/  (กันพลาด ย้อนได้)
#  วิธีใช้:  .\scripts\backup.ps1     (รันตอน docker compose up อยู่)
# ============================================================
$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
Set-Location $proj

# ต้องมี container db รันอยู่
$dbUp = docker compose ps --status running --services 2>$null
if ($dbUp -notcontains "db") {
    Write-Host "❌ container 'db' ยังไม่รัน — สั่ง 'docker compose up -d' ก่อน" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path "$proj\data\db_init" | Out-Null
New-Item -ItemType Directory -Force -Path "$proj\data\backups" | Out-Null

Write-Host "💾 กำลัง dump ฐานข้อมูล n8n ..." -ForegroundColor Cyan
# อ่าน user/db จาก env ใน container เอง → ตรงเสมอ ไม่ต้องเดา
$sql = docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl --clean --if-exists'
if ($LASTEXITCODE -ne 0 -or -not $sql) {
    Write-Host "❌ pg_dump ล้มเหลว" -ForegroundColor Red
    exit 1
}

$utf8 = New-Object System.Text.UTF8Encoding($false)   # UTF-8 ไม่มี BOM (postgres import ได้)
$seed = "$proj\data\db_init\01-restore.sql"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$copy = "$proj\data\backups\n8n-$stamp.sql"
[System.IO.File]::WriteAllLines($seed, $sql, $utf8)
[System.IO.File]::WriteAllLines($copy, $sql, $utf8)

$kb = [math]::Round((Get-Item $seed).Length / 1KB, 1)
Write-Host "✅ เสร็จ ($kb KB)" -ForegroundColor Green
Write-Host "   seed (auto-restore): data\db_init\01-restore.sql" -ForegroundColor Gray
Write-Host "   สำเนา              : data\backups\n8n-$stamp.sql" -ForegroundColor Gray
Write-Host ""
Write-Host "➡  ย้ายเครื่อง: ก๊อปโฟลเดอร์ .\data + ไฟล์ .env ไปเครื่องใหม่ แล้ว 'docker compose up -d'" -ForegroundColor Yellow
