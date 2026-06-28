# ============================================================
#  Run Affiliate Autopilot NATIVELY (no Docker / no WSL2)
#  Usage:
#     cd C:\Users\PronHub\affiliate-autopilot
#     .\run_local.ps1
#  Dashboard -> http://127.0.0.1:8088   (Ctrl+C to stop)
# ============================================================
$ErrorActionPreference = "Stop"
$proj = "C:\Users\ChaiwatA\shopee-affiliate-autopilot"
Set-Location $proj

# 1) .env (holds API keys) - create from template if missing
if (-not (Test-Path "$proj\.env")) {
    Copy-Item "$proj\.env.example" "$proj\.env"
    Write-Host "Created .env - add ANTHROPIC_API_KEY / GEMINI_API_KEY later (mock mode works now)" -ForegroundColor Yellow
}

# 2) venv + dependencies
if (-not (Test-Path "$proj\venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv "$proj\venv"
}
Write-Host "Installing/updating dependencies..." -ForegroundColor Cyan
& "$proj\venv\Scripts\python.exe" -m pip install -q --upgrade pip
& "$proj\venv\Scripts\python.exe" -m pip install -q -r "$proj\backend\requirements.txt"

# 3) store data + media under the project's data folder (not Docker's /app/data)
$env:DATA_DIR = ("$proj/data" -replace '\\', '/')
New-Item -ItemType Directory -Force -Path "$($env:DATA_DIR)/media" | Out-Null

# 3.5) ให้ server เรียก adb ได้ (phone farm) — ใช้ adb ที่มากับ adbutils
$adbDir = "$proj\venv\Lib\site-packages\adbutils\binaries"
if (Test-Path "$adbDir\adb.exe") { $env:PATH = "$adbDir;$env:PATH" }

# 4) run backend + Dashboard
Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "  Dashboard: http://127.0.0.1:8088   (Ctrl+C to stop)" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
& "$proj\venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir "$proj\backend" --host 127.0.0.1 --port 8088
