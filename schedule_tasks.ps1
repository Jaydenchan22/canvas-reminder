# Registers two Windows scheduled tasks:
#   - Daily digest at 8:00 AM
#   - Urgent check (due within 24h) at 6:00 PM
# Run once from this folder:  powershell -ExecutionPolicy Bypass -File .\schedule_tasks.ps1
# Remove later with:          Unregister-ScheduledTask -TaskName "UniReminder*" -Confirm:$false

$dir = $PSScriptRoot
$py  = Join-Path $dir ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $py)) { throw "Virtual env not found. Run setup first (see README)." }

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

$digest = New-ScheduledTaskAction -Execute $py -Argument "`"$dir\reminder.py`"" -WorkingDirectory $dir
Register-ScheduledTask -TaskName "UniReminder Digest" -Action $digest `
    -Trigger (New-ScheduledTaskTrigger -Daily -At 8:00AM) -Settings $settings -Force | Out-Null

$urgent = New-ScheduledTaskAction -Execute $py -Argument "`"$dir\reminder.py`" --urgent" -WorkingDirectory $dir
Register-ScheduledTask -TaskName "UniReminder Urgent" -Action $urgent `
    -Trigger (New-ScheduledTaskTrigger -Daily -At 6:00PM) -Settings $settings -Force | Out-Null

Write-Host "Scheduled: 'UniReminder Digest' (8 AM) and 'UniReminder Urgent' (6 PM)."
Write-Host "Note: they only run when your laptop is on. If it was off, they run next time it starts."
