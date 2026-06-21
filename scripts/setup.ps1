# =====================================================================
#  setup.ps1  -  One-time setup on a NEW machine (NATIVE, no Docker)
#  Move to a new PC:  git clone -> ./scripts/setup.ps1 -> ./scripts/start.ps1
#  (ASCII only - Windows PowerShell 5.1 cannot parse Thai/emoji in .ps1)
# =====================================================================
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "=== Affiliate Autopilot - NATIVE setup ===" -ForegroundColor Cyan

# 1) Python check
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) {
    Write-Host "Python not found. Install Python 3.11+ from https://www.python.org (tick 'Add to PATH')" -ForegroundColor Red
    exit 1
}
Write-Host "[1/5] python: $py"

# 2) venv
$venvPy = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "[2/5] creating venv ..." -ForegroundColor Cyan
    & python -m venv (Join-Path $root "venv")
}
else { Write-Host "[2/5] venv exists -> reuse" }

# 3) deps
Write-Host "[3/5] installing dependencies (this may take a few minutes) ..." -ForegroundColor Cyan
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r (Join-Path $root "backend\requirements.txt")

# 4) ffmpeg check (needed for video/audio)
Write-Host "[4/5] checking ffmpeg ..." -ForegroundColor Cyan
$ff = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source
if ($ff) { Write-Host "    ffmpeg: $ff" -ForegroundColor Green }
else { Write-Host "    ffmpeg NOT found -> install:  winget install Gyan.FFmpeg   (then reopen terminal)" -ForegroundColor Yellow }

# 5) .env
$envFile = Join-Path $root ".env"
$envEx = Join-Path $root ".env.example"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envEx) {
        Copy-Item $envEx $envFile
        Write-Host "[5/5] created .env from .env.example -> EDIT IT and fill your keys" -ForegroundColor Yellow
    }
    else { Write-Host "[5/5] .env.example missing -> create .env manually" -ForegroundColor Yellow }
}
else { Write-Host "[5/5] .env exists -> keep" }

Write-Host ""
Write-Host "DONE." -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1) Edit .env  (GEMINI_API_KEY etc - see docs/manual)"
Write-Host "  2) Run:  ./scripts/start.ps1   (starts server + Chrome for Flow + opens web)"
