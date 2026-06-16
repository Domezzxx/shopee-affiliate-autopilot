# ============================================================
#  Push this project to GitHub as a PRIVATE repo (one run)
#  Usage:
#     cd C:\Users\PronHub\affiliate-autopilot
#     .\setup_github.ps1
# ============================================================
$ErrorActionPreference = "Stop"
$repo = "shopee-affiliate-autopilot"
$visibility = "--private"

# 1) locate gh.exe (PATH may not be refreshed in this window)
$gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
if (-not $gh) {
    $gh = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter gh.exe -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
}
if (-not $gh) { Write-Host "gh.exe not found - open a NEW PowerShell window and retry" -ForegroundColor Red; exit 1 }
Write-Host "Using gh: $gh" -ForegroundColor Cyan

Set-Location "C:\Users\PronHub\affiliate-autopilot"

# 2) login GitHub if needed (opens browser)
& $gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host ">> Not logged in - opening GitHub login" -ForegroundColor Yellow
    Write-Host ">> Choose: GitHub.com -> HTTPS -> Login with a web browser" -ForegroundColor Yellow
    Write-Host ""
    & $gh auth login --hostname github.com --git-protocol https --web
    if ($LASTEXITCODE -ne 0) { Write-Host "login failed" -ForegroundColor Red; exit 1 }
}
Write-Host "GitHub login OK" -ForegroundColor Green

# 3) create repo (if missing) + set remote origin
& $gh repo view $repo 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host ">> Creating private repo: $repo" -ForegroundColor Cyan
    & $gh repo create $repo $visibility --source . --remote origin --disable-wiki
} else {
    Write-Host ">> Repo exists - setting remote origin" -ForegroundColor Cyan
    $owner = (& $gh api user --jq .login)
    git remote remove origin 2>$null
    git remote add origin "https://github.com/$owner/$repo.git"
}

# 4) push both branches
git push -u origin main
git push -u origin sprint2-connect-apis

$owner = (& $gh api user --jq .login)
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Done! Repo: https://github.com/$owner/$repo" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
