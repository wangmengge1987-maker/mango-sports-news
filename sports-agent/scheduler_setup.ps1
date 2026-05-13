# Mango 体育简报 — Windows 计划任务自动注册脚本
# 以管理员身份运行: 右键 → 使用 PowerShell 运行
# 作用：每天早上 09:55 自动生成简报并推送到微信

$TaskName = "Mango体育简报"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatPath = Join-Path $ScriptDir "run.bat"

# 检查是否管理员权限
$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $IsAdmin) {
    Write-Host "[!] 请以管理员身份运行此脚本（右键 → 使用 PowerShell 运行）" -ForegroundColor Red
    exit 1
}

# 删除已有任务（如有）
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[*] 删除已有计划任务: $TaskName" -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# 创建触发器：每天 09:55
$Trigger = New-ScheduledTaskTrigger -Daily -At "09:55"

# 动作：运行 run.bat 带 push 参数
$Action = New-ScheduledTaskAction -Execute $BatPath -Argument "push" -WorkingDirectory $ScriptDir

# 以当前用户身份运行（无需特殊权限）
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

# 设置：错过启动时间后尽快运行
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

# 注册任务
Register-ScheduledTask -TaskName $TaskName -Trigger $Trigger -Action $Action -Principal $Principal -Settings $Settings -Force

Write-Host ""
Write-Host "[✓] 计划任务已注册！" -ForegroundColor Green
Write-Host "[i] 任务名称: $TaskName" -ForegroundColor Cyan
Write-Host "[i] 执行时间: 每天 09:55" -ForegroundColor Cyan
Write-Host "[i] 执行脚本: $BatPath push" -ForegroundColor Cyan
Write-Host ""
Write-Host "[i] 如需取消，请在任务计划程序中删除 $TaskName" -ForegroundColor Yellow
Write-Host "[i] 或运行: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false" -ForegroundColor Yellow

# 打开任务计划程序确认
$choice = Read-Host "是否打开任务计划程序查看？(y/N)"
if ($choice -eq "y") {
    Start-Process taskschd.msc
}
