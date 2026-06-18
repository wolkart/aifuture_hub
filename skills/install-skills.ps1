# Подключает все скиллы из этой папки в глобальную папку Claude Code (~/.claude/skills)
# через junction-ссылки. Работает на Windows БЕЗ прав админа и без Developer Mode.
# Идемпотентно: повторный запуск только добавляет недостающие ссылки, существующие не трогает.
#
# Запуск:  powershell -ExecutionPolicy Bypass -File .\skills\install-skills.ps1

$ErrorActionPreference = 'Stop'
$skillsDir = $PSScriptRoot
$globalDir = Join-Path $env:USERPROFILE '.claude\skills'

if (-not (Test-Path $globalDir)) { New-Item -ItemType Directory -Path $globalDir -Force | Out-Null }

Get-ChildItem -Path $skillsDir -Directory |
  Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') } |
  ForEach-Object {
    $name   = $_.Name
    $target = $_.FullName
    $link   = Join-Path $globalDir $name

    if (Test-Path $link) {
      Write-Host "= уже подключён: $name"
      return
    }
    cmd /c mklink /J "`"$link`"" "`"$target`"" | Out-Null
    Write-Host "+ подключён:     $name"
  }

Write-Host ""
Write-Host "Готово. Скиллы доступны во всех проектах. Если переместишь репозиторий —"
Write-Host "ссылки станут битыми: удали их из ~/.claude/skills и запусти скрипт заново."
