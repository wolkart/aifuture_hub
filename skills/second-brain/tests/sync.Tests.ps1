# Pester 5. Те же сценарии, что tests/test_sync_sh.py, для scripts/sync.ps1 и регистрация задачи.
# Запуск: Invoke-Pester skills/second-brain/tests/sync.Tests.ps1

BeforeAll {
    $Sync = Join-Path $PSScriptRoot '..\scripts\sync.ps1'
    $Task = Join-Path $PSScriptRoot '..\scripts\windows-task.ps1'
    $PsExe = if ($env:OS -eq 'Windows_NT') { 'powershell.exe' } else { 'pwsh' }
    $Setup = @('-c', 'user.name=Настройка', '-c', 'user.email=setup@test')

    function G { param([Parameter(ValueFromRemainingArguments)]$rest) $o = & git @rest 2>&1; if ($LASTEXITCODE) { throw "git $rest : $o" }; $o }
    function Write-Note($dir, $name, $text) { [IO.File]::WriteAllText((Join-Path $dir $name), $text, (New-Object Text.UTF8Encoding $false)) }
    function Invoke-Sync($vault) {
        $script:out = & $PsExe -NoProfile -ExecutionPolicy Bypass -File $Sync -Vault $vault -Notify $script:notify 2>&1 | Out-String
        $LASTEXITCODE
    }
    function Get-Notices { if (Test-Path $script:notices) { @(Get-Content $script:notices -Encoding UTF8) } else { @() } }
    function Get-Tree($dir, $rev = 'HEAD') { (G -C $dir ls-tree --name-only $rev) -join "`n" }
}

Describe 'second-brain на Windows' {

BeforeEach {
    $root = Join-Path $TestDrive ([guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory $root | Out-Null
    $env:GIT_CONFIG_NOSYSTEM = '1'
    $env:GIT_CONFIG_GLOBAL = Join-Path $root 'no-global-config'
    $script:notices = Join-Path $root 'notices.txt'
    $script:notify = Join-Path $root 'notify.ps1'
    [IO.File]::WriteAllText($script:notify, "param(`$t, `$m) Add-Content -LiteralPath '$($script:notices)' -Value `"`$t|`$m`" -Encoding UTF8", (New-Object Text.UTF8Encoding $true))
    $script:remote = Join-Path $root 'remote.git'
    $script:a = Join-Path $root 'Второй мозг'
    $script:b = Join-Path $root 'b'
    G init -q --bare -b main $remote | Out-Null
    G init -q -b main $a | Out-Null
    Write-Note $a 'note.md' "строка`n"
    G -C $a add -A | Out-Null
    G -C $a @Setup commit -q -m init | Out-Null
    G -C $a remote add origin $remote | Out-Null
    G -C $a push -q -u origin main 2>&1 | Out-Null
    G clone -q $remote $b 2>&1 | Out-Null
}

Describe 'sync.ps1' {
    It 'без origin только сохраняет, подписываясь «Второй мозг»' {
        $solo = Join-Path $root 'solo'
        G init -q -b main $solo | Out-Null
        Write-Note $solo 'a.md' "текст`n"
        Invoke-Sync $solo | Should -Be 0
        (G -C $solo log -1 --format=%s) | Should -Match '^auto: '
        (G -C $solo log -1 --format=%an) | Should -Be 'Второй мозг'
    }
    It 'отправляет на GitHub' {
        Write-Note $a 'new.md' "новое`n"
        Invoke-Sync $a | Should -Be 0
        Get-Tree $remote 'main' | Should -Match 'new.md'
        $out | Should -Match 'ок'
    }
    It 'забирает правки другого устройства и совмещает без имени в Git' {
        Write-Note $a 'from-a.md' "a`n"; Invoke-Sync $a | Should -Be 0
        Write-Note $b 'from-b.md' "b`n"; Invoke-Sync $b | Should -Be 0
        Test-Path (Join-Path $b 'from-a.md') | Should -BeTrue
        Get-Tree $remote 'main' | Should -Match 'from-b.md'
    }
    It 'пропускает ход, если замок занят' {
        $lock = Join-Path $a '.git\second-brain-sync.lock'
        New-Item -ItemType Directory $lock -Force | Out-Null
        try {
            Write-Note $a 'x.md' "x`n"
            Invoke-Sync $a | Should -Be 0
            $out | Should -Match 'пропуск'
            Get-Tree $a | Should -Not -Match 'x.md'
        } finally { Remove-Item $lock -Recurse -Force }
    }
    It 'конфликт: отметка, одно уведомление, дальше локальные сохранения' {
        Write-Note $a 'note.md' "версия A`n"; Invoke-Sync $a | Should -Be 0
        Write-Note $b 'note.md' "версия B`n"
        Invoke-Sync $b | Should -Be 1
        Test-Path (Join-Path $b '.git\second-brain-conflict') | Should -BeTrue
        Test-Path (Join-Path $b '.git\rebase-merge') | Should -BeFalse
        [IO.File]::ReadAllText((Join-Path $b 'note.md')) | Should -Be "версия B`n"
        (Get-Notices).Count | Should -Be 1
        Write-Note $b 'later.md' "позже`n"
        Invoke-Sync $b | Should -Be 0
        $out | Should -Match 'стоит конфликт'
        Get-Tree $b | Should -Match 'later.md'
        (Get-Notices).Count | Should -Be 1
    }
    It 'папка менялась во время синхронизации — не конфликт' {
        Write-Note $a 'from-a.md' "a`n"; Invoke-Sync $a | Should -Be 0
        $hook = Join-Path $b '.git\hooks\post-commit'
        [IO.File]::WriteAllText($hook, "#!/bin/sh`necho changed >> note.md`n", (New-Object Text.UTF8Encoding $false))
        Write-Note $b 'x.md' "x`n"
        Invoke-Sync $b | Should -Be 2
        Test-Path (Join-Path $b '.git\second-brain-conflict') | Should -BeFalse
        (Get-Notices).Count | Should -Be 0
        Remove-Item $hook
        Invoke-Sync $b | Should -Be 0
        Test-Path (Join-Path $b 'from-a.md') | Should -BeTrue
    }
    It 'нет связи — не конфликт' {
        G -C $a remote set-url origin (Join-Path $root 'нет.git') | Out-Null
        Write-Note $a 'x.md' "x`n"
        Invoke-Sync $a | Should -Be 2
        Test-Path (Join-Path $a '.git\second-brain-conflict') | Should -BeFalse
        Get-Tree $a | Should -Match 'x.md'
    }
    It 'пишет лог в UTF-8' {
        $log = Join-Path $root 'sync.log'
        & $PsExe -NoProfile -ExecutionPolicy Bypass -File $Sync -Vault $a -Log $log | Out-Null
        [IO.File]::ReadAllText($log, [Text.Encoding]::UTF8) | Should -Match 'ок'
    }
}

Describe 'windows-task.ps1' -Skip:($env:OS -ne 'Windows_NT') {
    It 'ставит и снимает задачу каждые 5 минут' {
        $name = 'second-brain-sync-test-' + [guid]::NewGuid().ToString('N').Substring(0, 6)
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Task -Vault $a -Name $name | Out-Null
        $LASTEXITCODE | Should -Be 0
        $t = Get-ScheduledTask -TaskName $name
        $t.Triggers[0].Repetition.Interval | Should -Be 'PT5M'
        ($t.Actions[0].Execute + ' ' + $t.Actions[0].Arguments) | Should -Match 'sync.ps1'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Task -Vault $a -Name $name -Remove | Out-Null
        Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue | Should -BeNullOrEmpty
    }
}

}
