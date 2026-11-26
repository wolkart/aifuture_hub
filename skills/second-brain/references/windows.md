# Второй мозг на Windows

**Когда читать:** установка или переезд на Windows — до первого шага `SKILL.md`. Здесь только
то, что на Windows иначе; остальное — как в `SKILL.md`.

> Проверено автоматически на Windows-машине GitHub Actions: синхронизация, конфликт, замок,
> регистрация задачи, скрипты Python. Вживую ещё не проверено, мелькает ли окно Планировщика и
> показывается ли уведомление о конфликте. Человек заметил окно — поставь задачу с `-Launcher vbs`
> (шаг «Фоновое сохранение»).

Команды — в PowerShell. `<скилл>` — `$HOME\.agents\skills\second-brain`, `<мозг>` — путь к мозгу.

## Шаг 0 — скачать скилл

```powershell
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
curl.exe -fsSL https://codeload.github.com/wolkart/aifuture_hub/tar.gz/main | tar -xz -C "$HOME\.agents\skills" --strip-components=2 aifuture_hub-main/skills/second-brain
```

Нужен Git: `git --version`. Нет — `winget install --id Git.Git`.

## Место не в облаке

«Документы» и «Рабочий стол» на Windows часто забирает OneDrive. Проверка:
`[Environment]::GetFolderPath('MyDocuments')` — в пути есть `OneDrive`, значит, туда нельзя. По
умолчанию — `$HOME\second-brain`.

## Шаблон и AGENTS.md

```powershell
New-Item -ItemType Directory -Force "<мозг>" | Out-Null
Copy-Item -Recurse -Force "<скилл>\templates\vault\*" "<мозг>\"
```

Проверь, что в мозге есть `.gitignore`, `.gitattributes`, `.claude\CLAUDE.md`, `.obsidian\app.json`.

`AGENTS.md` — не ярлык (ярлык на файл без режима разработчика не создаётся, копия разойдётся), а
файл-указатель в одну строку:

```powershell
Set-Content -Encoding UTF8 "<мозг>\AGENTS.md" "Правила — в ``_CLAUDE.md`` рядом. Прочитай его до любой работы в этой папке."
```

## Git

Как в `SKILL.md`, но вместо `core.precomposeunicode`:

```powershell
git config core.longpaths true
```

`.gitattributes` из шаблона (`* text=auto eol=lf`) держит концы строк одинаковыми на Маке и Windows.

## Проекты

Поиск папок с `.git`:

```powershell
Get-ChildItem $HOME -Directory -Recurse -Depth 3 -Force -Filter .git -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch 'node_modules|AppData' } | ForEach-Object { $_.Parent.FullName }
```

## Python

Нужен только для каталога, карточек и переезда. `python --version`; нет — с согласия:
`winget install --id Python.Python.3.12`, потом новое окно PowerShell. Команды — `python -I …`
вместо `python3 -I …`. Не хочет ставить — каталог и карточки агент ведёт сам по правилам
`_CLAUDE.md`; переезд без Python не делается.

## Правило для агентов

Как в `SKILL.md`, шаг 7. Ярлыки для Codex и OpenCode на Windows не ставятся — как подключить их
без ярлыков, сказано в скилле agent-memory, «Установка», шаг 3, пункт «Windows».

## Фоновое сохранение

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<скилл>\scripts\windows-task.ps1" -Vault "<мозг>"
```

Скрипт копирует `sync.ps1` в `%LOCALAPPDATA%\second-brain\` и ставит задачу `second-brain-sync` в
Планировщике заданий: раз в 5 минут, пока человек вошёл в Windows, без окна. Прав администратора
не нужно. Лог — `%LOCALAPPDATA%\second-brain\sync.log`.

Проверка сразу, не дожидаясь расписания:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\second-brain\sync.ps1" -Vault "<мозг>"
```

Последняя строка — `ок` (или `ок: сохранено на компьютере`, пока нет GitHub).

- **Мелькает окно** каждые 5 минут — поставь заново с `-Launcher vbs`.
- **Снять задачу** — тот же скрипт с `-Remove`.
- **Уведомление о конфликте** — всплывающее окно Windows. Не показалось — строка «КОНФЛИКТ» в логе.

## GitHub (уровень 2)

`winget install --id GitHub.cli`, дальше как в [sync.md](sync.md). Проверка — команда выше, лог —
`%LOCALAPPDATA%\second-brain\sync.log`.

## Переезд

Копия старого волта — `robocopy` из [migration.md](migration.md), шаг 1. Остальное — так же, с
`python` вместо `python3`.
