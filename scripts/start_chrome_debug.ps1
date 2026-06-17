# ============================================================
#  Start Chrome in Remote Debugging Mode (Port 9222)
#  Usage:
#     .\scripts\start_chrome_debug.ps1
# ============================================================

$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

$chromePath = $null
foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        $chromePath = $path
        break
    }
}

if ($null -eq $chromePath) {
    Write-Host "[ERROR] Google Chrome was not found in standard directories." -ForegroundColor Red
    Write-Host "Please start Chrome manually from your terminal with these arguments:" -ForegroundColor Yellow
    Write-Host 'chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\Users\PronHub\affiliate-autopilot\data\chrome_profile"' -ForegroundColor Yellow
    exit 1
}

Write-Host "Stopping existing Google Chrome processes to enable Remote Debugging..." -ForegroundColor Yellow
taskkill /F /IM chrome.exe 2>&1 | Out-Null
Start-Sleep -Seconds 2

$profileDir = "C:\Users\PronHub\affiliate-autopilot\data\chrome_profile"
if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
}

Write-Host "Launching Google Chrome on Port 9222..." -ForegroundColor Green
Write-Host "Profile Directory: $profileDir" -ForegroundColor Cyan
Write-Host "Target URL: https://labs.google/fx/tools/flow" -ForegroundColor Cyan
Write-Host "--------------------------------------------------" -ForegroundColor Gray
Write-Host "Please log in to Google Flow on the browser window that opens." -ForegroundColor Green
Write-Host "--------------------------------------------------" -ForegroundColor Gray

Start-Process -FilePath $chromePath -ArgumentList "--remote-debugging-port=9222 --user-data-dir=`"$profileDir`" --no-first-run https://labs.google/fx/tools/flow"

