# =====================================================================
#  stop.ps1  -  Stop Affiliate Autopilot (server). Chrome is left running.
#  Run:  ./scripts/stop.ps1
# =====================================================================
$ErrorActionPreference = "Continue"

Write-Host "=== STOP Affiliate Autopilot ===" -ForegroundColor Cyan
$conn = Get-NetTCPConnection -LocalPort 8088 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $conn | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Write-Host "OK: server :8088 stopped" -ForegroundColor Green
}
else {
    Write-Host "server not running" -ForegroundColor Yellow
}
Write-Host "Note: Chrome (Flow) left running -- close it manually if needed" -ForegroundColor Gray
Write-Host "Start again:  ./scripts/start.ps1" -ForegroundColor Cyan
