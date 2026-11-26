<#
Фоновое сохранение второго мозга на Windows. Запускает Планировщик заданий раз в 5 минут
(scripts/windows-task.ps1). Логика та же, что у sync.sh:
  1. сохраняет все изменения в историю Git (коммит «auto: …»);
  2. есть GitHub (origin) — забирает чужие правки и отправляет свои.
Коды: 0 — ок или пропуск, 1 — конфликт, 2 — нет связи / push не удался, 3 — нет папки.
Конфликт оставляет отметку .git\second-brain-conflict: дальше только локальное сохранение,
без уведомлений, пока человек не скажет агенту «разбери конфликт».
Запуск: powershell -NoProfile -ExecutionPolicy Bypass -File sync.ps1 -Vault <путь> [-Log <файл>] [-Notify <команда>]
#>
param(
    [Parameter(Mandatory = $true)][string]$Vault,
    [string]$Log = '',
    [string]$Notify = $env:SECOND_BRAIN_NOTIFY
)
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding $false
$Utf8 = New-Object Text.UTF8Encoding $false

function Write-Log([string]$m) {
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m
    [Console]::Out.WriteLine($line)
    if ($Log) { [IO.File]::AppendAllText($Log, $line + "`n", $Utf8) }
}

function Show-Notice([string]$title, [string]$text) {
    if ($Notify) { & $Notify $title $text; return }
    try {
        [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
        $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $nodes = $xml.GetElementsByTagName('text')
        [void]$nodes.Item(0).AppendChild($xml.CreateTextNode($title))
        [void]$nodes.Item(1).AppendChild($xml.CreateTextNode($text))
        $app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($xml))
    } catch { Write-Log "уведомление не показалось: $($_.Exception.Message)" }
}

function Invoke-Sync {
    if (Test-Path -LiteralPath '.git\rebase-merge' -PathType Container) { Write-Log 'пропуск: идёт rebase'; return 0 }
    if (Test-Path -LiteralPath '.git\rebase-apply' -PathType Container) { Write-Log 'пропуск: идёт rebase'; return 0 }
    if (Test-Path -LiteralPath '.git\MERGE_HEAD') { Write-Log 'пропуск: идёт merge'; return 0 }

    # на свежем компьютере имя в Git может быть не задано — тогда подписываемся «Второй мозг»
    $G = @()
    if (-not (git config user.email)) { $G = @('-c', 'user.name=Второй мозг', '-c', "user.email=second-brain@$env:COMPUTERNAME") }

    git add -A 2>$null
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        $n = @(git diff --cached --name-only).Count
        git @G commit -q -m ("auto: {0} · {1} · файлов: {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm'), $env:COMPUTERNAME, $n) | Out-Null
    }

    git remote get-url origin *> $null
    if ($LASTEXITCODE -ne 0) { Write-Log 'ок: сохранено на компьютере'; return 0 }
    if (Test-Path -LiteralPath '.git\second-brain-conflict') {
        Write-Log 'стоит конфликт: сохранено на компьютере, на GitHub не отправляю — скажи агенту «разбери конфликт»'
        return 0
    }

    $branch = (git symbolic-ref --short HEAD).Trim()
    git fetch -q origin *> $null
    if ($LASTEXITCODE -ne 0) { Write-Log 'нет связи с GitHub — повторю в следующий раз'; return 2 }
    git rev-parse -q --verify "origin/$branch" *> $null
    if ($LASTEXITCODE -eq 0) {
        git @G rebase -q "origin/$branch" *> $null
        if ($LASTEXITCODE -ne 0) {
            git rebase --abort *> $null
            [IO.File]::WriteAllText((Join-Path (Get-Location).ProviderPath '.git\second-brain-conflict'), '', $Utf8)
            Write-Log 'КОНФЛИКТ — нужна ручная правка'
            Show-Notice 'Второй мозг: нужна ручная правка' 'Изменения с двух устройств пересеклись. Ничего не потеряно — попроси агента разобрать конфликт.'
            return 1
        }
    }
    git push -q origin $branch *> $null
    if ($LASTEXITCODE -ne 0) { Write-Log 'push не удался — повторю в следующий раз'; return 2 }
    Write-Log 'ок'
    return 0
}

if (-not (Test-Path -LiteralPath $Vault -PathType Container)) { Write-Log "пропуск: нет папки $Vault"; exit 3 }
Set-Location -LiteralPath $Vault
$V = (Resolve-Path -LiteralPath $Vault).ProviderPath
if (-not (Test-Path -LiteralPath '.git' -PathType Container)) { Write-Log "пропуск: $V — не Git-репозиторий"; exit 0 }

# один запуск за раз: расписание и ручной запуск не должны тянуть изменения одновременно
$hash = [BitConverter]::ToString((New-Object Security.Cryptography.SHA1Managed).ComputeHash([Text.Encoding]::UTF8.GetBytes($V))).Replace('-', '').Substring(0, 12)
$Lock = Join-Path ([IO.Path]::GetTempPath()) "second-brain-sync-$hash.lock"
if ((Test-Path -LiteralPath $Lock) -and (Get-Item -LiteralPath $Lock).LastWriteTime -lt (Get-Date).AddMinutes(-15)) {
    Remove-Item -LiteralPath $Lock -Recurse -Force
}
try { New-Item -ItemType Directory -Path $Lock -ErrorAction Stop | Out-Null }
catch { Write-Log 'пропуск: синхронизация уже идёт'; exit 0 }

$code = 0
try { $code = Invoke-Sync | Select-Object -Last 1 }   # случайный вывод git не должен попасть в код
finally { Remove-Item -LiteralPath $Lock -Recurse -Force -ErrorAction SilentlyContinue }
exit $code
