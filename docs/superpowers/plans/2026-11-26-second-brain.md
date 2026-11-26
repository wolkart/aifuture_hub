# second-brain — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** публичный скилл `skills/second-brain/`: одна фраза — и у человека второй мозг (папка, правила, каталог, правило для агентов, история в Git), по желанию GitHub, сервер и переезд старого волта.

**Architecture:** инструкция (`SKILL.md` + `references/` по моменту) + шаблон волта, который копируется целиком + скрипты только там, где без них нельзя: фоновая синхронизация (bash / PowerShell) и работа с тысячами файлов (Python, только стандартная библиотека).

**Tech Stack:** Markdown, bash 3.2, PowerShell 5.1, Python ≥ 3.9 stdlib, Git, `gh`, launchd / Планировщик заданий / cron, pytest, Pester, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-26-second-brain-design.md` — читать вместе с планом. Оригиналы для переноса — таблица «Откуда переносим» в спеке.

## Global Constraints

- В файлах скилла нет следов автора. Запрещённые строки (проверяет `tests/test_no_traces.py`): `/Users/wolkart`, `Артём`, `AI Future Club`, `content-studio`, `hermes-vps`, `Social Flow`, `Yandex.Disk.localized`, `com.wolkart`. `wolkart` разрешён только в адресе хаба `github.com/wolkart/aifuture_hub` и `codeload.github.com/wolkart/aifuture_hub`.
- Python ≥ 3.9 (системный на Маке — 3.9.6), только стандартная библиотека; каждый `open()` с `encoding="utf-8"` (на Windows иначе cp1251); все пути и имена сравниваются после `unicodedata.normalize("NFC", …)`.
- Запуск скриптов: `python3 -I <скрипт> <аргументы>`. Скрипты не печатают содержимое файлов, где могут быть ключи, — только пути и счётчики.
- bash совместим с 3.2 (Мак); на Маке нет `flock`.
- Тексты для человека и агента — простым русским, по образцу `skills/agent-memory/`; обращение к владельцу — «человек»; без жирного через строку.
- Тесты: `cd skills/second-brain && uv run --python 3.9 --with pytest python -m pytest -q tests`.
- Коммитить только файлы скилла, спека/плана и каталогов хаба. В рабочей папке лежат чужие незакоммиченные правки (reel, motion-assets, reels-script, BACKLOG) — их не добавлять (`git add` только явными путями).
- Каждый коммит заканчивается строкой `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **На свежем компьютере не задано имя в Git** (`user.name`/`user.email` пусто) → `sync.sh`/`sync.ps1` всё равно сохраняют историю (запасное имя «Второй мозг», почта `second-brain@<хост>`). Тест — Task 4, Task 10.
2. **Путь волта с пробелом и кириллицей** (`~/Второй мозг`) → синхронизация, launchd-задача, каталог работают. Тест — Task 3, Task 4.
3. **Пустой или урезанный волт** (нет `content/`, `archive/`, проектов) → `index.py` и `cards.py` не падают. Тест — Task 2, Task 3.
4. **Windows-кодировка и концы строк**: заметки с кириллицей читаются и пишутся без порчи, `index.md` не меняется от повторного запуска. Тест — CI в Task 10.
5. **Повторные запуски при конфликте** → одно уведомление, локальные сохранения продолжаются, отметку снимает только «разбери конфликт». Тест — Task 4.

---

### Task 1: Шаблон волта и раздел для агентов

**Files:**
- Create: `skills/second-brain/templates/vault/_CLAUDE.md`, `README.md`, `About Me.md`, `index.md`, `.gitignore`, `.gitattributes`, `.claude/CLAUDE.md`, `.obsidian/app.json`, `.obsidian/templates.json`, `templates/Карточка проекта.md`, `.gitkeep` в `projects/ content/ wiki/ raw/входящее/ journal/ archive/ files/`
- Create: `skills/second-brain/templates/agents-block.md`
- Test: `skills/second-brain/tests/test_template.py`, `skills/second-brain/tests/test_no_traces.py`

**Interfaces:**
- Produces: путь шаблона `templates/vault/`; плейсхолдер пути волта `<путь к мозгу>` в `agents-block.md` и `_CLAUDE.md`; метки карточки `<!-- заметки проекта: начало (пересобирается скриптом второго мозга cards.py) -->` / `<!-- заметки проекта: конец -->` (их использует Task 2).

- [ ] **Step 1: Тесты.** `test_no_traces.py::test_no_author_traces` — обходит все файлы `skills/second-brain/` (кроме `tests/`), ни одна запрещённая строка из Global Constraints не встречается; `wolkart` — только внутри `github.com/wolkart/aifuture_hub` и `codeload.github.com/wolkart/aifuture_hub`. `test_template.py`: `test_required_files` (все файлы и папки из Files), `test_six_questions` (в `_CLAUDE.md` есть `journal/`, `projects/`, `content/`, `raw/`, `wiki/`, `archive/` в разделе «Куда класть», именно в этом порядке), `test_gitignore` (`.obsidian/workspace*.json`, `.trash/`, `.DS_Store`, `*.sync-conflict-*`), `test_gitattributes` (`* text=auto eol=lf`), `test_claude_import` (`.claude/CLAUDE.md` == `@../_CLAUDE.md\n`), `test_obsidian_settings` (`app.json`: `attachmentFolderPath == "files"`, `newFileLocation == "folder"`, `newFileFolderPath == "raw/входящее"`; `templates.json`: `folder == "templates"`), `test_card_markers` (метки в карточке), `test_agents_block` (начинается с `## Второй мозг`, содержит `<путь к мозгу>/index.md`, `<путь к мозгу>/_CLAUDE.md`, «Git в этой папке не трогай», не ссылается на раздел «Память»).
- [ ] **Step 2: Запустить** — FAIL (файлов нет).
- [ ] **Step 3: Перенести и обезличить** по таблице «Откуда переносим» и разделу «Шаблоны — что в них» спека. Решения спека: без `Logs/`/`log.md`; свойства заметок `date`, `type`, `tags`, `description`; нет раздела «Проекты сейчас»; раздел синхронизации в `_CLAUDE.md` и README — с пометкой, что агент дописывает его под уровень. `About Me.md` — только устройство разделов с подсказками в угловых скобках.
- [ ] **Step 4: Запустить** — PASS.
- [ ] **Step 5: Коммит** `second-brain: шаблон волта и раздел для агентов`.

### Task 2: Общие функции, ссылки, карточки проектов

**Files:**
- Create: `skills/second-brain/scripts/vaultlib.py`, `scripts/links.py`, `scripts/cards.py`
- Create: `skills/second-brain/tests/conftest.py` (фикстуры волтов)
- Test: `tests/test_links.py`, `tests/test_cards.py`

**Interfaces:**
- Produces (`vaultlib.py`): `nfc(s: str) -> str`; `SKIP_DIRS = {".git", ".obsidian", ".trash", "_переезд"}`; `iter_files(root: Path, skip=SKIP_DIRS) -> Iterator[str]` (относительные пути, NFC, `/` как разделитель); `read_text(path: Path) -> str` (utf-8, errors="replace"); `LINK_RE` (`!?\[\[([^\]|#^]+)`).
- Produces: `links.broken_links(root: Path) -> set[tuple[str, str]]` (заметка, цель; цель сравнивается по имени без папки и `.md`; карточки в `*/cards/*` не проверяются); CLI `links.py <волт>` печатает пары, код 1 если есть.
- Produces: `cards.update_cards(root: Path) -> dict[str, int]` (проект → число ссылок); CLI `cards.py <волт>`.
- Produces (`conftest.py`): фикстура `vault(tmp_path)` — копия `templates/vault/` + 2 проекта с заметками; фикстура `messy_vault(tmp_path)` — используется в Task 7–8 (заводится там).

- [ ] **Step 1: Тесты.** `test_broken_links_found` (ссылка на несуществующую заметку → пара в наборе), `test_link_forms` (`[[Имя]]`, `[[Имя|текст]]`, `[[папка/Имя]]`, `![[картинка.png]]`, `[[Имя#раздел]]` к существующим — не битые), `test_nfd_name` (файл с именем в NFD, ссылка в NFC — не битая), `test_cards_groups` (заметки корня проекта первыми, потом по подпапкам, карточка сама себя не перечисляет), `test_cards_idempotent` (второй запуск не меняет файл), `test_cards_keeps_text` (текст карточки вне меток не тронут; меток нет — раздел дописан в конец), `test_cards_empty_project` (строка «Пока только карточка…»), `test_cards_no_projects_dir` (нет `projects/` → `{}` без ошибки).
- [ ] **Step 2: Запустить** — FAIL.
- [ ] **Step 3: Реализовать** — перенос `cards.py` и `broken_links()` из `move.py` автора на `vaultlib`.
- [ ] **Step 4: Запустить** — PASS.
- [ ] **Step 5: Коммит** `second-brain: ссылки и карточки проектов`.

### Task 3: Каталог index.py

**Files:**
- Create: `skills/second-brain/scripts/index.py`
- Test: `tests/test_index.py`

**Interfaces:**
- Consumes: `vaultlib.nfc`, `vaultlib.iter_files`, `vaultlib.read_text`.
- Produces: `index.describe(path: Path) -> str` (≤ 140 знаков: `description` → `тема` в свойствах → первый абзац после `## For future agent` → первая содержательная строка); `index.build_index(root: Path, big: int = 30, today: str | None = None) -> str`; CLI `index.py <волт> [--big N]` пишет `index.md`, печатает «index.md: N строк».

- [ ] **Step 1: Тесты.** `test_sections_order` (Обо мне → Проекты → Знания → Контент → Сырьё → Дневник → Архив → Шаблоны), `test_project_card_first`, `test_big_folder_one_line` (папка с 31 заметкой при `big=30` → одна строка «`путь/` — 31 заметок», ни одной ссылки из неё), `test_cards_dir_one_line` (папка `cards/` — строкой при любом размере), `test_same_name_with_path` (две `План.md` в разных проектах → обе ссылки вида `[[projects/А/План|План (А)]]`), `test_journal_no_content` (одна строка, имён заметок дневника в каталоге нет), `test_describe_order` (каждый из четырёх источников описания), `test_missing_sections` (нет `content/`, `archive/`, `raw/` → без ошибки, разделы пропущены), `test_cyrillic_space_path` (волт в `tmp/Второй мозг`), `test_idempotent` (два запуска с одним `today` — одинаковый текст).
- [ ] **Step 2: Запустить** — FAIL.
- [ ] **Step 3: Реализовать** — обобщённый `index.py` автора без разделов «Разведка»/«курсы»/«AI Mindset»; порог `big` применяется к любой подпапке во всех разделах, кроме карточек проектов.
- [ ] **Step 4: Запустить** — PASS.
- [ ] **Step 5: Коммит** `second-brain: каталог index.py`.

### Task 4: Синхронизация sync.sh и установка задачи на Маке

**Files:**
- Create: `skills/second-brain/scripts/sync.sh`, `scripts/install-sync.sh`
- Test: `tests/test_sync_sh.py` (skip на win32)

**Interfaces:**
- Produces: `sync.sh <волт> [--chown uid:gid]`; коды: 0 — ок или пропуск, 1 — конфликт, 2 — push не удался; строки лога в stdout с датой; уведомление: если задана `SECOND_BRAIN_NOTIFY` — вызвать `$SECOND_BRAIN_NOTIFY "<заголовок>" "<текст>"`, иначе на Darwin `osascript`, иначе ничего; замок `${TMPDIR:-/tmp}/second-brain-sync-<cksum пути>.lock`, протухший > 15 минут снимается; отметка конфликта `.git/second-brain-conflict`.
- Produces: `install-sync.sh <волт> [--label local.second-brain.sync] [--no-load]` — копирует `sync.sh` в `$HOME/.local/bin/second-brain-sync.sh`, пишет `$HOME/Library/LaunchAgents/<label>.plist` (`StartInterval` 300, `RunAtLoad`, лог `$HOME/Library/Logs/second-brain-sync.log`), без `--no-load` — `launchctl bootout` старой + `launchctl bootstrap gui/$(id -u)`.

- [ ] **Step 1: Тесты** (фикстура: голый репозиторий `remote.git` + два клона, `HOME` во временной папке без `.gitconfig`): `test_commit_only_without_origin` (нет `origin` → коммит `auto: …`, код 0), `test_push` (изменение в клоне A → после запуска есть в `remote.git`), `test_pull_other_side` (B запускает — получает правку A), `test_no_identity` (без `user.name` коммит есть, автор «Второй мозг»), `test_lock_skip` (замок существует и свежий → «пропуск», коммита нет), `test_stale_lock_removed` (замок старше 15 мин → снят, запуск прошёл), `test_conflict_marks_and_notifies_once` (A и B правят одну строку; запуск B → код 1, отметка есть, rebase не висит, файл уведомлений содержит 1 строку; повторный запуск B → код 0, «стоит конфликт», локальный коммит есть, уведомлений всё ещё 1), `test_space_cyrillic_path` (волт `Второй мозг`), `test_install_sync_plist` (`--no-load`, `HOME` временный: скрипт скопирован и исполняемый, `plutil -lint` ок, в plist путь волта и `StartInterval` 300; skip не на Darwin).
- [ ] **Step 2: Запустить** — FAIL.
- [ ] **Step 3: Реализовать** — перенос `second-brain-sync.sh` автора: текущая ветка вместо `main`, замок по пути волта, запасное имя через `git -c user.name=… -c user.email=…` только если своё не задано, отметка конфликта, `--chown` (из серверного скрипта).
- [ ] **Step 4: Запустить** — PASS.
- [ ] **Step 5: Коммит** `second-brain: синхронизация и фоновая задача на Маке`.

### Task 5: SKILL.md и README скилла

**Files:**
- Create: `skills/second-brain/SKILL.md`, `skills/second-brain/README.md`

**Interfaces:**
- Consumes: шаблон (Task 1), `index.py`, `cards.py`, `links.py` (Task 2–3), `install-sync.sh`, `sync.sh` (Task 4); имена будущих `references/sync.md`, `server.md`, `migration.md`, `windows.md` (Task 6, 9, 10).

- [ ] **Step 1: SKILL.md.** Frontmatter `name: second-brain`; `description` — русские фразы установки («поставь второй мозг», «сделай второй мозг», «перенеси мой волт / Obsidian во второй мозг», «подключи второй мозг на втором компьютере») и просьб («разложи входящее», «проверь второй мозг», «пересобери каталог», «разбери конфликт во втором мозге», «верни заметку как было», «запиши во второй мозг»); явное «команды `/obsidian-*` — не сюда». Тело: устройство (таблица «мозг ≠ память»), установка уровня 1 (шаги 0–10 спека, шаг 0 — скачать папку скилла как у `agent-memory`), ветка «Второй компьютер», повторный запуск, когда читать каждый `references/*.md`, повседневные просьбы, «где спотыкаются».
- [ ] **Step 2: README.md.** Для человека: что получится, три уровня, фраза установки `Поставь второй мозг по этому скиллу: https://github.com/wolkart/aifuture_hub/tree/main/skills/second-brain`, просьбы в окне, чего не делает, раздел «Для продвинутых: вместе с obsidian-second-brain» (из спека).
- [ ] **Step 3: Проверка.** `test_no_traces.py` PASS; в `SKILL.md` каждая ссылка на файл скилла указывает на существующий или запланированный файл (`references/*.md`, `scripts/*`, `templates/*`); длина `SKILL.md` ≤ 250 строк.
- [ ] **Step 4: Коммит** `second-brain: SKILL.md и README`.

### Task 6: Уровни 2 и 3 — GitHub и сервер

**Files:**
- Create: `skills/second-brain/references/sync.md`, `references/server.md`

- [ ] **Step 1: sync.md** — по разделу «Уровень 2» спека: `gh` с согласия, `gh auth login --web --git-protocol https`, `gh auth setup-git`, вопрос имени и подтверждение до `gh repo create <имя> --private --source <волт> --push`, проверка `gh repo view --json visibility`, проверка через 5 минут, дописать README волта.
- [ ] **Step 2: server.md** — по разделу «Уровень 3» спека и живому серверу автора: ключ развёртывания, `gh repo deploy-key add --allow-write`, `ssh://git@ssh.github.com:443/<владелец>/<репо>.git`, `core.sshCommand`, клон в новую папку до переключения, cron `*/5 * * * * <путь>/second-brain-sync.sh <волт> [--chown uid:gid] >> /var/log/second-brain-sync.log 2>&1`, исключение в инструкции агента, проверка с телефона.
- [ ] **Step 3: Проверка.** `test_no_traces.py` PASS; команды в обоих файлах сверены с `--help` (`gh repo create`, `gh repo deploy-key add`).
- [ ] **Step 4: Коммит** `second-brain: уровни 2 и 3 — GitHub и сервер`.

### Task 7: Переезд — поиск ключей и опись

**Files:**
- Create: `skills/second-brain/scripts/migrate/scan_keys.py`, `scripts/migrate/inventory.py`
- Modify: `skills/second-brain/tests/conftest.py` — фикстура `messy_vault`
- Test: `tests/test_scan_keys.py`, `tests/test_inventory.py`

**Interfaces:**
- Consumes: `vaultlib` (через `sys.path.insert(0, <scripts>)`).
- Produces: `scan_keys.scan(root: Path) -> list[Hit]`, `Hit = namedtuple("Hit", "path line kind masked placeholder")`; CLI печатает `путь:строка:вид:маска[ (похоже на заглушку)]`. Имя не `secrets.py` — оно перекрыло бы стандартный модуль `secrets`.
- Produces: формат правил `rules.json`: `{"rules": [{"from": "папка/ или путь/начало имени", "to": "новая/папка/" | null, "why": "…", "ask": "" | "вопрос"}]}`; `null` — «не берём»; первое совпадение решает. Отличие от `rules.py` автора — JSON вместо Python: правила, написанные агентом, не исполняются как код.
- Produces: `inventory.tree(root: Path, depth: int = 3) -> str`; `inventory.build(root: Path, rules: list[dict]) -> dict` с ключами `rules` (копия правил), `dest` (путь → новый путь или `None`), `unmatched`, `collisions`, `same_name`; `inventory.render(plan: dict, rules: list[dict], today: str) -> str` (Опись: новая структура, итог по папкам, «Вопросы к тебе», таблица); CLI `inventory.py tree <волт> [--depth N]`, `inventory.py build <волт> <rules.json> [--out <папка>]` → `<папка>/plan.json` + `<папка>/Опись.md` (по умолчанию `<волт>/_переезд/`).
- Produces (`conftest.messy_vault`): `0-Входящие/`, `2-Контент/Рилсы/`, `bases/` (строчными), `Заметка (2).md` рядом с `Заметка.md`, `План.md` в двух папках, имя в NFD, `.base` с фильтром `"2-Контент"`, `.obsidian/app.json` с `attachmentFolderPath: "Вложения"`, `.env` с настоящим на вид ключом `sk-proj-` + 40 знаков, `README.md` с `sk-xxx`, ссылки между заметками.

- [ ] **Step 1: Тесты.** `test_scan_finds_key` (ключ из `.env` найден, `masked` показывает ≤ 4 знака), `test_scan_placeholder` (`sk-xxx` → `placeholder=True`), `test_scan_no_content_printed` (вывод CLI не содержит ключ целиком), `test_tree_counts`, `test_build_first_rule_wins`, `test_build_folder_rule_keeps_subpath` (`2-Контент/Рилсы/а.md` по правилу `2-Контент/ → content/` → `content/Рилсы/а.md`), `test_build_file_rule_basename`, `test_build_skip_null` (`Заметка (2).md` → `None`), `test_build_unmatched`, `test_build_collisions`, `test_build_same_name` (две `План.md` в `same_name`), `test_render_questions` (правило с `ask` → строка в «Вопросы к тебе» и `**?**` в таблице; без `ask` — «Нет»), `test_nfd_paths` (правило в NFC ловит файл с именем в NFD).
- [ ] **Step 2: Запустить** — FAIL.
- [ ] **Step 3: Реализовать** — `build.py` + `render.py` автора, без его разделов и проектов; разделы описи — по верхним папкам новой структуры.
- [ ] **Step 4: Запустить** — PASS.
- [ ] **Step 5: Коммит** `second-brain: переезд — поиск ключей и опись`.

### Task 8: Переезд — перенос и пути вне волта

**Files:**
- Create: `skills/second-brain/scripts/migrate/move.py`, `scripts/migrate/switch.py`
- Test: `tests/test_move.py`, `tests/test_switch.py`

**Interfaces:**
- Consumes: `vaultlib`, `links.broken_links`, `plan.json` из Task 7 (правила внутри, ключ `rules`).
- Produces: `move.run(root: Path, plan: dict, dry: bool) -> dict` с ключами `moved`, `skipped`, `rewritten`, `obsidian`, `broken_before`, `broken_after`, `new_broken`; CLI `move.py <волт> <plan.json> [--dry]`.
- Produces: `switch.run(files: list[Path], old: str, new: str, plan: dict | None, dry: bool) -> list[tuple[str, int, int]]` (файл, замен, осталось старых); CLI `switch.py --old <путь> --new <путь> [--plan plan.json] [--dry] <файл>…`.

- [ ] **Step 1: Тесты.** `test_dry_changes_nothing`, `test_moves_files`, `test_skip_removed` (`None` в плане → файла нет в новой структуре), `test_case_only_rename` (`bases/` → `Bases/`: после запуска в листинге корня именно `Bases`), `test_rewrites_paths_in_text` (упоминание `2-Контент/Рилсы/а.md` в заметке → `content/Рилсы/а.md`; длинные пути заменяются раньше коротких), `test_rewrites_base_filter` (`"2-Контент"` в `.base` → `"content"`), `test_obsidian_settings` (`attachmentFolderPath` переписан по правилам), `test_no_new_broken_links`, `test_occupied_target_stops` (цель занята другим файлом → остановка с сообщением, ничего не перенесено после), `test_switch_counts_only` (вывод — счётчики, без строк файла), `test_switch_abs_root` (`/old/vault/x` → `/new/brain/x`), `test_switch_dry`.
- [ ] **Step 2: Запустить** — FAIL.
- [ ] **Step 3: Реализовать** — `move.py` и `switch.py` автора: старые верхние папки и замены настроек Obsidian выводятся из правил (`from` с `/` → `to`), без захардкоженных списков; переименование по регистру — через временное имя.
- [ ] **Step 4: Запустить** — PASS.
- [ ] **Step 5: Коммит** `second-brain: переезд — перенос и пути вне волта`.

### Task 9: references/migration.md

**Files:**
- Create: `skills/second-brain/references/migration.md`

- [ ] **Step 1: Написать** — 10 шагов раздела «Переезд старого волта» спека с точными командами скриптов Task 7–8, формат `rules.json` с примером на 5 правил (папка, файл, «не берём», с вопросом, исключение раньше общего правила), правило «машина раскладывает, человек отвечает на спорное», копирование без `.git`/`.trash`/`workspace*.json`/конфликтов облака (`rsync` на Маке, `robocopy` на Windows), выключение плагина Obsidian Git, поиск старого пути вне волта, критерий готовности: ноль вопросов в описи, ноль новых битых ссылок.
- [ ] **Step 2: Проверка.** `test_no_traces.py` PASS; каждая команда в файле запускается на `messy_vault` из тестов вручную в черновой папке.
- [ ] **Step 3: Коммит** `second-brain: инструкция переезда`.

### Task 10: Windows

**Files:**
- Create: `skills/second-brain/scripts/sync.ps1`, `scripts/windows-task.ps1`, `references/windows.md`, `tests/sync.Tests.ps1`
- Create: `.github/workflows/second-brain-windows.yml`

**Interfaces:**
- Produces: `sync.ps1 -Vault <путь> [-Notify <команда>]` — логика и коды как у `sync.sh` (Task 4); замок `$env:TEMP\second-brain-sync-<хеш пути>.lock`; лог — вызывающий перенаправляет в `$env:LOCALAPPDATA\second-brain-sync.log`.
- Produces: `windows-task.ps1 -Vault <путь> [-Name second-brain-sync] [-Remove]` — копирует `sync.ps1` в `$env:LOCALAPPDATA\second-brain\`, регистрирует задачу: при входе + повтор каждые 5 минут бессрочно, запуск без окна (`conhost.exe --headless powershell.exe -NoProfile -ExecutionPolicy Bypass -File …`; запасной путь — `.vbs` через `wscript.exe`, выбор — флаг `-Launcher conhost|vbs`, по умолчанию `conhost`).

- [ ] **Step 1: Тесты Pester** `tests/sync.Tests.ps1` — те же сценарии, что в Task 4 (без origin, push, pull, без имени, замок, конфликт с одним уведомлением, путь `Второй мозг`), плюс `windows-task.ps1` регистрирует и снимает задачу (`Get-ScheduledTask`).
- [ ] **Step 2: Реализовать** `sync.ps1`, `windows-task.ps1`.
- [ ] **Step 3: windows.md** — по разделу «Windows» спека; пометка «проверено автоматически на GitHub Actions; мелькание окна и уведомление вживую не проверены».
- [ ] **Step 4: Workflow** — `on: push/pull_request` с `paths: skills/second-brain/**` и `workflow_dispatch`; `runs-on: windows-latest`; `actions/setup-python` 3.9; `pip install pytest`; `python -m pytest -q skills/second-brain/tests`; `Invoke-Pester skills/second-brain/tests/sync.Tests.ps1`; `git config --global core.autocrlf true` перед тестами (как у учеников по умолчанию).
- [ ] **Step 5: Коммит, push ветки, прогон.** `git push -u origin second-brain`; `gh run watch` → зелёный. Красный — чинить до зелёного.

### Task 11: Хаб

**Files:**
- Modify: `skills/README.md` (строка после `agent-memory`), `README.md` (витрина, строка «Второй мозг» в группе с «Память агента»)
- Modify: `BACKLOG.md` — одна строка «second-brain: живая проверка на Windows — мелькает ли окно Планировщика, приходит ли уведомление о конфликте»

- [ ] **Step 1: Строки каталога и витрины.** Витрина — одна простая фраза о пользе, без терминов: «Агенты сами ведут твою базу знаний: проекты, решения, знания. Говоришь одну фразу — и папка, правила и история готовы».
- [ ] **Step 2: Подключить глобально** — `bash skills/install-skills.sh`; проверить `ls -la ~/.claude/skills/second-brain`.
- [ ] **Step 3: BACKLOG** — в `BACKLOG.md` есть чужие незакоммиченные правки: в индекс добавить только свою строку (`git diff -U0 BACKLOG.md` → оставить свой кусок → `git apply --cached`), проверить `git diff --cached BACKLOG.md` — одна строка.
- [ ] **Step 4: Коммит** `second-brain: каталог, витрина, бэклог`.

### Task 12: Живые прогоны и PR

- [ ] **Step 1: Уровень 1 на пустой папке.** Свежий агент с `HOME` во временной папке в черновике, фраза из README; задача launchd — `--label local.second-brain.sync.test`. Проверить: шаблон на месте, `AGENTS.md` — ярлык, первый коммит, `About Me.md` заполнен по ответам, карточки, раздел в `$HOME/.agents/AGENTS.md`, строка в `$HOME/.claude/CLAUDE.md`, через 5 минут коммит `auto:`. После — `launchctl bootout` тестовой задачи, папку удалить.
- [ ] **Step 2: Уровень 2.** Спросить автора, можно ли создать тестовый приватный репозиторий; да — прогон `references/sync.md`, проверить push; после — спросить, удалить ли репозиторий.
- [ ] **Step 3: Переезд.** `git -C ~/second-brain archive old-vault-2026-11-26 | tar -x -C <черновик>/old-vault`; свежий агент по `references/migration.md`; сравнить с `~/second-brain`: раскладка по верхним папкам (таблица «у автора / у скилла»), новых битых ссылок 0, число вопросов в описи. Расхождения — в отчёт автору, ничего не копировать в хаб.
- [ ] **Step 4: Найденное в прогонах** — чинить по закону хаба: один раз — не дописывать; система — механизм; только потом правило.
- [ ] **Step 5: Ревью ветки** — свежий ревьюер на всю ветку; найденное — исправить.
- [ ] **Step 6: PR** `gh pr create` в `main`: что за скилл, уровни, что проверено (pytest, Pester на Windows-машине GitHub, живые прогоны), что не проверено (Windows вживую — в BACKLOG). Тело кончается строкой `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 7: После слияния** (вне git): третья часть фразы в `~/Products/Клуб - AI Future/Прод/10 Рабочий сетап/Telegram (тема Работа с агентом)/9 Архив solution-kit.zip — подпись.txt` — «3. Второй мозг — по этому скиллу: https://github.com/wolkart/aifuture_hub/tree/main/skills/second-brain».
