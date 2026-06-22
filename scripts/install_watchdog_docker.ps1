# =====================================================================
#  install_watchdog_docker.ps1  -  register the Docker watchdog as a
#  Scheduled Task that runs at logon + every 1 minute (ASCII only).
#    Install:    .\scripts\install_watchdog_docker.ps1
#    Uninstall:  .\scripts\install_watchdog_docker.ps1 -Uninstall
#  Needs admin -> the script self-elevates (one UAC prompt).
# =====================================================================
param([switch]$Uninstall)

$TaskName = "AffiliateAutopilotDockerWatchdog"

# self-elevate
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($Uninstall) { $argList += " -Uninstall" }
    Start-Process powershell.exe -Verb RunAs -ArgumentList $argList
    return
}

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed task: $TaskName" -ForegroundColor Yellow
    return
}

$root  = Split-Path -Parent $PSScriptRoot
$wd    = Join-Path $root "scripts\watchdog_docker.ps1"
if (-not (Test-Path $wd)) { Write-Host "ERROR: $wd not found" -ForegroundColor Red; return }

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$wd`""

# at logon + repeat every 1 minute (indefinitely)
$trigger = New-ScheduledTaskTrigger -AtLogOn
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1)).Repetition

$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Installed task: $TaskName (at logon + every 1 min)" -ForegroundColor Green
Write-Host "Log: $root\data\watchdog_docker.log" -ForegroundColor Gray
