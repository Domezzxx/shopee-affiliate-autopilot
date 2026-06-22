# ============================================================
#  ติดตั้ง Flow Host Agent เป็น Scheduled Task (รันตอน logon, ค้างตลอด)
#    Install:    .\scripts\install_flow_host_agent.ps1
#    Uninstall:  .\scripts\install_flow_host_agent.ps1 -Uninstall
#  ต้อง admin -> สคริปต์ self-elevate (UAC เด้งครั้งเดียว)
# ============================================================
param([switch]$Uninstall)
$TaskName = "AffiliateAutopilotFlowAgent"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    $a = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($Uninstall) { $a += " -Uninstall" }
    Start-Process powershell.exe -Verb RunAs -ArgumentList $a
    return
}

if ($Uninstall) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed task: $TaskName" -ForegroundColor Yellow
    return
}

$root  = Split-Path -Parent $PSScriptRoot
$agent = Join-Path $root "scripts\flow_host_agent.ps1"
if (-not (Test-Path $agent)) { Write-Host "ERROR: $agent not found" -ForegroundColor Red; return }

$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$agent`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
# loop ค้างตลอด -> ไม่จำกัดเวลา + กันรันซ้อน + รีสตาร์ทถ้าหลุด
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "Installed + started task: $TaskName" -ForegroundColor Green
Write-Host "Log: $root\data\flow_host_agent.log" -ForegroundColor Gray
