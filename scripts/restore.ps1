# ============================================================
#  ♻️  Restore ฐานข้อมูล n8n เข้า DB ที่ "รันอยู่แล้ว"
#  ใช้เมื่อ: เครื่องใหม่เผลอ up จน DB ถูกสร้างว่างไปแล้ว (auto-restore เลยไม่ทำงาน)
#  หรืออยากกู้ทับด้วย backup เก่า
#  วิธีใช้:  .\scripts\restore.ps1                       (ใช้ data\db_init\01-restore.sql)
#           .\scripts\restore.ps1 data\backups\n8n-XXXX.sql
#  ⚠️ ทับ workflow/credential ปัจจุบันของ n8n ทั้งหมด
# ============================================================
param([string]$File = "data\db_init\01-restore.sql")
$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
Set-Location $proj

if (-not (Test-Path $File)) {
    Write-Host "❌ ไม่พบไฟล์: $File" -ForegroundColor Red
    exit 1
}
$dbUp = docker compose ps --status running --services 2>$null
if ($dbUp -notcontains "db") {
    Write-Host "❌ container 'db' ยังไม่รัน — สั่ง 'docker compose up -d' ก่อน" -ForegroundColor Red
    exit 1
}

Write-Host "⚠️  กำลังจะ restore '$File' ทับฐานข้อมูล n8n ปัจจุบัน" -ForegroundColor Yellow
Write-Host "♻️  กำลัง restore ..." -ForegroundColor Cyan
Get-Content -Raw $File | docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ restore ล้มเหลว" -ForegroundColor Red
    exit 1
}
Write-Host "✅ restore สำเร็จ — รีสตาร์ท n8n ให้เห็นผล: docker compose restart n8n" -ForegroundColor Green
