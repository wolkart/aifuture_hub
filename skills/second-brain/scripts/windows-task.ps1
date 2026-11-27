<#
Ставит фоновое сохранение второго мозга на Windows: копия sync.ps1 в %LOCALAPPDATA%\second-brain\
и задача Планировщика раз в 5 минут, без окна. Повторный запуск обновляет скрипт и задачу.
Запуск: powershell -NoProfile -ExecutionPolicy Bypass -File windows-task.ps1 -Vault <путь>
        [-Name second-brain-sync] [-Launcher conhost|vbs] [-Remove]
Launcher — чем запускать без окна: conhost (conhost.exe --headless) или vbs (wscript.exe). Если при
conhost каждые 5 минут мелькает окно — поставь заново с -Launcher vbs.
#>
param(
    [Parameter(Mandatory = $true)][string]$Vault,
    [string]$Name = 'second-brain-sync',
    [ValidateSet('conhost', 'vbs')][string]$Launcher = 'conhost',
    [switch]$Remove
)
$ErrorActionPreference = 'Stop'

if ($Remove) {
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Задача $Name снята."
    exit 0
}

$Vault = (Resolve-Path -LiteralPath $Vault).ProviderPath
$dir = Join-Path $env:LOCALAPPDATA 'second-brain'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$script = Join-Path $dir 'sync.ps1'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'sync.ps1') -Destination $script -Force
$log = Join-Path $dir 'sync.log'
$ps = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$psArgs = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`" -Vault `"$Vault`" -Log `"$log`""

if ($Launcher -eq 'vbs') {
    $vbs = Join-Path $dir 'run-hidden.vbs'
    $cmd = ("`"$ps`" $psArgs") -replace '"', '""'
    $text = "Set sh = CreateObject(""WScript.Shell"")`r`nsh.Run ""$cmd"", 0, True`r`n"
    [IO.File]::WriteAllText($vbs, $text, [Text.Encoding]::Unicode)   # UTF-16 с BOM: wscript читает кириллицу в путях
    $action = New-ScheduledTaskAction -Execute (Join-Path $env:SystemRoot 'System32\wscript.exe') -Argument "//B //Nologo `"$vbs`""
} else {
    $action = New-ScheduledTaskAction -Execute (Join-Path $env:SystemRoot 'System32\conhost.exe') -Argument "--headless `"$ps`" $psArgs"
}

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Output "Готово: задача $Name каждые 5 минут сохраняет $Vault. Лог — $log"
