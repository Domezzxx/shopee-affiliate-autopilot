# ============================================================
#  setup_ssh.ps1  — ติดตั้ง + เปิด OpenSSH Server บน Windows 11
#  รันแบบ Administrator:  คลิกขวา > Run with PowerShell (Admin)
#  หรือใน Admin PowerShell:  Set-ExecutionPolicy -Scope Process Bypass -Force ; .\scripts\setup_ssh.ps1
#  เสร็จแล้ว remote เข้าจากอีกเครื่อง:  ssh ChaiwatA@<IP>
# ============================================================
$ErrorActionPreference = "Stop"

# ตรวจสิทธิ์ admin
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Write-Host "ต้องรันแบบ Administrator!" -ForegroundColor Red; exit 1 }

Write-Host "[1/5] ติดตั้ง OpenSSH Server..." -ForegroundColor Cyan
$cap = Get-WindowsCapability -Online -Name OpenSSH.Server*
if ($cap.State -ne "Installed") { Add-WindowsCapability -Online -Name $cap.Name } else { Write-Host "   ติดตั้งอยู่แล้ว" }

Write-Host "[2/5] ตั้ง service ให้เริ่มเองตอนบูต + start..." -ForegroundColor Cyan
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd
Set-Service -Name ssh-agent -StartupType Automatic -ErrorAction SilentlyContinue

Write-Host "[3/5] เปิด firewall พอร์ต 22 (inbound)..." -ForegroundColor Cyan
if (-not (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH SSH Server (sshd)' `
        -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
}

Write-Host "[4/5] ตั้ง PowerShell เป็น shell เริ่มต้นของ SSH (สะดวกเวลา remote)..." -ForegroundColor Cyan
New-Item -Path "HKLM:\SOFTWARE\OpenSSH" -Force | Out-Null
New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell `
    -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -PropertyType String -Force | Out-Null

Write-Host "[5/5] เสร็จ! สถานะ:" -ForegroundColor Green
Get-Service sshd | Format-Table Name, Status, StartType -AutoSize
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like '192.168.*' } | Select-Object -First 1).IPAddress
Write-Host ""
Write-Host "  เชื่อมจากอีกเครื่อง (วง Wi-Fi เดียวกัน):" -ForegroundColor Yellow
Write-Host "      ssh $env:USERNAME@$ip" -ForegroundColor White
Write-Host ""
Write-Host "  cd ไปโปรเจกต์หลัง login:  cd $PSScriptRoot\.." -ForegroundColor DarkGray
