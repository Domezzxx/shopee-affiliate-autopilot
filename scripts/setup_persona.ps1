# =====================================================================
#  setup_persona.ps1  -  ติดตั้ง AI persona พูดได้ (Wav2Lip lip-sync, ฟรี รันบน CPU)
#  - ลง torch (CPU) + deps
#  - clone Wav2Lip + โหลด checkpoint (~500MB) ลง tools/Wav2Lip (gitignored)
#  - แพตช์โค้ดเก่าให้รันบน Python 3.11 / torch ใหม่
#  รันครั้งเดียว:  ./scripts/setup_persona.ps1
# =====================================================================
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root "venv\Scripts\python.exe"
$w2l = Join-Path $root "tools\Wav2Lip"

Write-Host "[1/4] ลง torch (CPU) + deps..." -ForegroundColor Cyan
& $py -m pip install --quiet torch torchvision --index-url https://download.pytorch.org/whl/cpu
& $py -m pip install --quiet opencv-python librosa numba scipy tqdm edge-tts gtts

Write-Host "[2/4] clone Wav2Lip..." -ForegroundColor Cyan
if (-not (Test-Path "$w2l\inference.py")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $root "tools") | Out-Null
    git clone --depth 1 https://github.com/Rudrabha/Wav2Lip.git $w2l
}

Write-Host "[3/4] โหลด checkpoint (~500MB ครั้งเดียว)..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "$w2l\checkpoints" | Out-Null
New-Item -ItemType Directory -Force -Path "$w2l\face_detection\detection\sfd" | Out-Null
$base = "https://github.com/justinjohn0306/Wav2Lip/releases/download/models"
if (-not (Test-Path "$w2l\checkpoints\wav2lip_gan.pth")) {
    curl.exe -s -L -o "$w2l\checkpoints\wav2lip_gan.pth" "$base/wav2lip_gan.pth"
}
if (-not (Test-Path "$w2l\face_detection\detection\sfd\s3fd.pth")) {
    curl.exe -s -L -o "$w2l\face_detection\detection\sfd\s3fd.pth" "$base/s3fd.pth"
}

Write-Host "[4/4] แพตช์โค้ด (torch 2.6+ weights_only + librosa keyword)..." -ForegroundColor Cyan
# inference.py: torch.load(..., weights_only=False)
$inf = "$w2l\inference.py"
(Get-Content $inf -Raw) `
    -replace "torch\.load\(checkpoint_path\)", "torch.load(checkpoint_path, weights_only=False)" `
    -replace "map_location=lambda storage, loc: storage\)", "map_location=lambda storage, loc: storage, weights_only=False)" `
    | Set-Content $inf -Encoding UTF8
# sfd_detector.py
$sfd = "$w2l\face_detection\detection\sfd\sfd_detector.py"
(Get-Content $sfd -Raw) -replace "torch\.load\(path_to_detector\)", "torch.load(path_to_detector, weights_only=False)" | Set-Content $sfd -Encoding UTF8
# audio.py: librosa.filters.mel positional -> keyword
$aud = "$w2l\audio.py"
(Get-Content $aud -Raw) -replace "librosa\.filters\.mel\(hp\.sample_rate, hp\.n_fft,", "librosa.filters.mel(sr=hp.sample_rate, n_fft=hp.n_fft," | Set-Content $aud -Encoding UTF8

Write-Host "เสร็จ! persona พร้อมใช้ — สร้างหน้า: ./venv/Scripts/python.exe scripts/_make_chef.py" -ForegroundColor Green
