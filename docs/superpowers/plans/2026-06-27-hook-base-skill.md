# hook-base Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать скилл `hook-base` — библиотеку+резолвер хук-паттернов (положить молча / взять адаптированно) со складом в Obsidian-волте, и подключить его к reels-script и carousel-script.

**Architecture:** Один скилл `skills/hook-base/` несёт логику двух операций (ПОЛОЖИТЬ/ВЗЯТЬ) и схему записи. Каноничный склад — в волте `2-Контент/База хуков/` (путь из конвенции глобального CLAUDE.md); в репо — схема, логика и 1 обезличенный пример-затравка. Контентные скиллы на шаге 2 резолва вызывают `hook-base` (взять); встроенный хребет остаётся фоллбэком. Доступ — обычный вызов скилла, без суб-агентов.

**Tech Stack:** Markdown-скиллы (SKILL.md + references/), YAML-фронтматтер записей, evals.json (eval-харнес skill-creator), маршрут meta-prompt→skill-creator. Контент — RU.

## Global Constraints

- Язык всех артефактов скилла и записей — **русский**; кириллица в значениях фронтматтера, translit в именах файлов.
- Конвенция проекта: один скилл = `skills/<имя>/SKILL.md` + `references/`/`assets/`/`scripts/`; описание применения — в `README.md` рядом; каждый новый скилл — строкой в `skills/README.md`; после создания — `skills/install-skills.sh` для глобального симлинка.
- Маршрут создания скилла: `meta-prompt` (ядро SKILL.md) → `skill-creator` (упаковка, evals, итерации). Вывод meta-prompt — сырьё, не финальный SKILL.md.
- Склад в волте: `2-Контент/База хуков/` (Mac: `/Users/wolkart/Yandex.Disk.localized/Obsidian/AI Automation Knowledge Base/2-Контент/База хуков/`). Отдельно от `Разведка/`.
- Схема записи (расширённая, с `формат` и `шаблон`) — единственный источник истины в `references/schema.md`.
- CTA НЕ трогаем: база — только хуки; CTA остаётся константой в content-studio/CLAUDE.md.
- `тип_хука` ∈ {провокация, неожиданность, интрига, отрицание, обещание}. `формат` ∈ {рилс, карусель, универсальный}.
- Имя файла записи: `hook-<типхука-translit>-<ниша-translit>-NN.md`.

---

### Task 1: Каркас скилла + схема записи

**Files:**
- Create: `skills/hook-base/references/schema.md`
- Create: `skills/hook-base/references/patterns/.gitkeep` (пустой, чтобы папка существовала)

**Interfaces:**
- Produces: `references/schema.md` — каноническая схема записи, правила молчаливой классификации, конвенция имён, путь к складу. На неё ссылаются SKILL.md (Task 2), сид (Task 6), evals (Task 7).

- [ ] **Step 1: Написать `references/schema.md`**

Содержимое: блок-схема YAML (точно как в спеке, секция «Схема записи»), плюс:
- перечисление допустимых значений `тип_хука`, `формат`, `кросс_нишевость`;
- правила молчаливой классификации (как из текста хука вывести тип_хука: маркеры «не …, а …» → отрицание; «секрет/мало кто знает» → интрига; «X за Y минут / без усилий» → обещание; вызов/спор → провокация; «оказывается/на самом деле» → неожиданность);
- как строить `шаблон` (заменить конкретику на `{X}`/`{Y}`-слоты, сохранив каркас);
- конвенция имени файла и выбор `NN` (следующий свободный для пары тип+ниша);
- путь к складу в волте и фоллбэк на `references/patterns/` в репо, если волт не сконфигурирован.

- [ ] **Step 2: Проверка**

Run: `test -f skills/hook-base/references/schema.md && grep -c "тип_хука" skills/hook-base/references/schema.md`
Expected: файл есть, совпадений ≥ 2.

- [ ] **Step 3: Commit**

```bash
git add skills/hook-base/references/schema.md skills/hook-base/references/patterns/.gitkeep
git commit -m "hook-base: схема записи + каркас references"
```

---

### Task 2: Ядро SKILL.md (через meta-prompt) — диспетчер ПОЛОЖИТЬ/ВЗЯТЬ

**Files:**
- Create: `skills/hook-base/SKILL.md`

**Interfaces:**
- Consumes: `references/schema.md` (Task 1).
- Produces: `SKILL.md` с фронтматтером `name: hook-base` + `description` (триггеры обеих операций); тело — диспетчер: определить операцию → выполнить ПОЛОЖИТЬ или ВЗЯТЬ по логике из спека.

- [ ] **Step 1: Сгенерировать ядро через meta-prompt**

Вызвать скилл `meta-prompt` с задачей: «системная инструкция для скилла-библиотеки хуков с двумя операциями (положить: молчаливая классификация по схеме → запись .md, ответ одной строкой; взять: фильтр+ранг+подстановка шаблона под тему, фоллбэк при пустоте). Роль — библиотекарь-резолвер. Дисциплина ответа: для ПОЛОЖИТЬ — одна строка-подтверждение; для ВЗЯТЬ — 2–3 хука с пометкой дефолта, без думания вслух».
Вывод meta-prompt сохранить как сырьё.

- [ ] **Step 2: Адаптировать сырьё в SKILL.md**

Собрать `SKILL.md`:
- фронтматтер: `name: hook-base`; `description` (RU, с триггерами: «внеси/добавь хук», «залетел ролик с хуком», «дай/подбери хук под рилс/карусель про…»; явно — НЕ путать с reels-script/carousel-script/instagram-analytics; скилл хранит и отдаёт хуки, не пишет сценарии);
- «Дисциплина ответа» (молча классифицирует; ПОЛОЖИТЬ → одна строка; ВЗЯТЬ → 2–3 хука + дефолт; без рассуждений вслух);
- «Определение операции» (положить vs взять по входу);
- «ПОЛОЖИТЬ» — шаги из спека, ссылка на `references/schema.md`;
- «ВЗЯТЬ» — фильтр/ранг/подстановка шаблона/фоллбэк из спека;
- «Где склад» — путь волта из конвенции + фоллбэк на репо `references/patterns/`.

- [ ] **Step 3: Проверка структуры**

Run: `grep -E "^name: hook-base" skills/hook-base/SKILL.md && grep -c -iE "положить|взять" skills/hook-base/SKILL.md`
Expected: name найден; обе операции упомянуты (≥ 2).

- [ ] **Step 4: Commit**

```bash
git add skills/hook-base/SKILL.md
git commit -m "hook-base: SKILL.md — диспетчер положить/взять (ядро из meta-prompt)"
```

---

### Task 3: README скилла + пример-затравка + витрина

**Files:**
- Create: `skills/hook-base/README.md`
- Create: `skills/hook-base/references/patterns/hook-obeshchanie-fitnes-01.md`
- Modify: `skills/README.md` (добавить строку каталога)
- Delete: `skills/hook-base/references/patterns/.gitkeep` (больше не нужен — появился реальный файл)

**Interfaces:**
- Consumes: `references/schema.md` (Task 1).
- Produces: обезличенный пример записи (для тех, кто заберёт харнес) + витринная строка.

- [ ] **Step 1: Перенести fitnes-пример в репо-затравку**

Скопировать содержимое `skills/reels-script/references/patterns/hook-obeshchanie-fitnes-01.md` в `skills/hook-base/references/patterns/hook-obeshchanie-fitnes-01.md`, дополнив поля до расширенной схемы (`формат`, `шаблон`).

- [ ] **Step 2: Написать `skills/hook-base/README.md`**

Что делает скилл, когда применять (положить/взять), где склад (волт + фоллбэк репо), ссылка на схему. По образцу `skills/reels-script/README.md`.

- [ ] **Step 3: Добавить строку в `skills/README.md`**

Run сперва: `grep -n "reels-script\|carousel-script" skills/README.md | head`
Затем вставить строку про `hook-base` в том же формате каталога рядом с контентными скиллами.

- [ ] **Step 4: Проверка**

Run: `test -f skills/hook-base/README.md && grep -c "hook-base" skills/README.md`
Expected: README есть; в витрине ≥ 1 упоминание.

- [ ] **Step 5: Commit**

```bash
git rm skills/hook-base/references/patterns/.gitkeep
git add skills/hook-base/README.md skills/hook-base/references/patterns/hook-obeshchanie-fitnes-01.md skills/README.md
git commit -m "hook-base: README, пример-затравка, строка витрины"
```

---

### Task 4: Проводка в reels-script + удаление старого сид-каталога

**Files:**
- Modify: `skills/reels-script/SKILL.md` (раздел «Порядок разрешения источника хука», шаг 2)
- Delete: `skills/reels-script/references/patterns/` (вся папка — заменена базой)
- Modify: `skills/reels-script/README.md` (если упоминает встроенную базу паттернов)

**Interfaces:**
- Consumes: `hook-base` SKILL.md (Task 2) — вызывается как скилл.
- Produces: обновлённый контракт reels: шаг 2 = вызов hook-base.

- [ ] **Step 1: Прочитать текущий шаг 2**

Run: `grep -n -A2 "Внешняя база" skills/reels-script/SKILL.md`

- [ ] **Step 2: Заменить шаг 2**

С «Внешняя база паттернов — если подключена. Сегодня этот шаг пуст…» на: «Внешняя база паттернов подключена: вызови скилл `hook-base` (операция ВЗЯТЬ) с (ниша, стадия воронки, формат=рилс, угол); возьми кандидатов. Если база пуста по теме — иди к шагу 3 (встроенный хребет)». Обновить ссылку (убрать указание на `references/patterns/README.md`).

- [ ] **Step 3: Удалить старый каталог паттернов**

```bash
git rm -r skills/reels-script/references/patterns
```

- [ ] **Step 4: Подчистить README reels, если ссылается на удалённое**

Run: `grep -n "patterns\|база паттернов" skills/reels-script/README.md` — при наличии поправить на упоминание hook-base.

- [ ] **Step 5: Проверка**

Run: `grep -c "hook-base" skills/reels-script/SKILL.md && test ! -d skills/reels-script/references/patterns && echo OK`
Expected: ≥ 1 упоминание hook-base; папки нет; `OK`.

- [ ] **Step 6: Commit**

```bash
git add -A skills/reels-script
git commit -m "reels-script: шаг 2 резолва хука → hook-base; убран встроенный сид-каталог"
```

---

### Task 5: Проводка в carousel-script

**Files:**
- Modify: `skills/carousel-script/SKILL.md` (раздел «Порядок разрешения источника обложки-хука», шаг 2)
- Modify: `skills/carousel-script/README.md` (если упоминает базу паттернов)

**Interfaces:**
- Consumes: `hook-base` SKILL.md (Task 2).
- Produces: обновлённый контракт carousel: шаг 2 = вызов hook-base, формат=карусель.

- [ ] **Step 1: Прочитать текущий шаг 2**

Run: `grep -n -A2 "Внешняя база" skills/carousel-script/SKILL.md`

- [ ] **Step 2: Заменить шаг 2**

На: «Внешняя база паттернов подключена: вызови скилл `hook-base` (операция ВЗЯТЬ) с (ниша, стадия, формат=карусель, угол/тип хука); возьми кандидатов на обложку-хук. Пусто по теме — к шагу 3 (встроенный хребет)».

- [ ] **Step 3: Проверка**

Run: `grep -c "hook-base" skills/carousel-script/SKILL.md`
Expected: ≥ 1.

- [ ] **Step 4: Commit**

```bash
git add -A skills/carousel-script
git commit -m "carousel-script: шаг 2 резолва обложки-хука → hook-base"
```

---

### Task 6: Сид склада в волте (2 ИИ-хука + 10 хуков Ника) + .base-вид

**Files:**
- Create: `<волт>/2-Контент/База хуков/hook-*.md` (12 записей)
- Create: `<волт>/2-Контент/База хуков/База хуков.base` (Obsidian-вид)

**Interfaces:**
- Consumes: `references/schema.md` (Task 1), исходный сид `reels-script/.../patterns` (2 ИИ-хука, до удаления в Task 4 — взять из git-истории или скопировать заранее) и `2-Контент/Разведка/nick_saraev/` (10 enriched-хуков).

- [ ] **Step 1: Перенести 2 ИИ-хука в волт**

Создать в `2-Контент/База хуков/` записи `hook-otritsanie-ai-01.md` и `hook-provokatsiya-ai-01.md` по расширенной схеме (добавить `формат: рилс`, `шаблон`). Контент взять из текущего `skills/reels-script/references/patterns/` (выполнить Task 6 до удаления в Task 4, либо восстановить из git).

- [ ] **Step 2: Повысить 10 хуков Ника**

Из `2-Контент/Разведка/nick_saraev/index.md` (топ-10 enriched, строки 8–17) для каждого: выделить хук-фразу из карточки, обобщить в `шаблон`, перевести/адаптировать тело под RU, проставить `тип_хука`, `ниша: ИИ`, `формат: рилс`, `когда_работает`, `кросс_нишевость`, `источник` (ссылка на карточку/«скаут nick_saraev»), `метрики` (просмотры/охват из таблицы). Имена: `hook-<тип>-ai-NN.md` с уникальными NN.

- [ ] **Step 3: Создать `База хуков.base`**

Obsidian-вид по образцу `2-Контент/_Контент.base`: источник — папка `База хуков`, колонки `тип_хука`, `ниша`, `формат`, `когда_работает`, `кросс_нишевость`, `метрики.просмотры`; сортировка по просмотрам убыв.

- [ ] **Step 4: Проверка**

Run: `ls "/Users/wolkart/Yandex.Disk.localized/Obsidian/AI Automation Knowledge Base/2-Контент/База хуков/" | grep -c "^hook-.*\.md$"`
Expected: 12.

- [ ] **Step 5: Commit (только репо-артефакты, если есть; волт вне git)**

Волт не в git — коммитить нечего. Зафиксировать факт в ответе. Если в репо менялись файлы (нет) — пропустить.

---

### Task 7: Evals + прогон через skill-creator

**Files:**
- Create: `skills/hook-base/evals/evals.json`

**Interfaces:**
- Consumes: весь скилл (Tasks 1–3).
- Produces: проходящий eval-набор (триггер + поведение).

- [ ] **Step 1: Написать `evals/evals.json`**

По образцу `skills/reels-script/evals/evals.json`. Кейсы:
- триггер ПОЛОЖИТЬ: «внеси хук „ИИ не заберёт твою работу…"» → ожидается активация hook-base, режим положить;
- триггер ВЗЯТЬ: «дай хук под рилс про автоматизацию» → активация hook-base, режим взять;
- негатив: «сделай рилс про X» → НЕ hook-base (это reels-script); «разбери конкурента @x» → НЕ hook-base (instagram-analytics);
- поведение: запись имеет все поля схемы; резолв возвращает 2–3 хука с пометкой дефолта.

- [ ] **Step 2: Прогнать evals через skill-creator**

Вызвать скилл `skill-creator` (режим eval/измерение), прогнать набор, зафиксировать результат.

- [ ] **Step 3: Итерация по провалам**

Если триггер/поведение проваливаются — уточнить `description`/тело SKILL.md и схему, перепрогнать. Цель — все кейсы зелёные.

- [ ] **Step 4: Commit**

```bash
git add skills/hook-base/evals/evals.json skills/hook-base/SKILL.md
git commit -m "hook-base: evals (триггер+поведение), проходят"
```

---

### Task 8: Глобальное подключение + финальная проверка

**Files:**
- Run: `skills/install-skills.sh`

- [ ] **Step 1: Подключить скилл глобально**

Run: `bash skills/install-skills.sh`
Expected: создан симлинк `~/.claude/skills/hook-base` (идемпотентно, существующие не трогает).

- [ ] **Step 2: Проверка симлинка**

Run: `ls -la ~/.claude/skills/hook-base`
Expected: симлинк на `skills/hook-base`.

- [ ] **Step 3: Сверка с планом**

Прочитать спек, отметить, что все секции реализованы: схема, ПОЛОЖИТЬ, ВЗЯТЬ, проводка reels+carousel, сид, evals. Зафиксировать в финальном ответе.

- [ ] **Step 4: Финальный commit (если есть незакоммиченное)**

```bash
git add -A skills/
git commit -m "hook-base: подключение глобально + финальная сверка" || echo "нечего коммитить"
```

---

## Self-Review

**Spec coverage:**
- Роль библиотека+резолвер → Task 2 (SKILL.md), Task 1 (схема). ✓
- Доступ вариант Б (вызов скилла) → Task 4/5 (проводка вызовом). ✓
- Хранилище в волте + репо схема/логика/пример → Task 1, 3, 6. ✓
- Молчаливый приём → Task 2 (логика ПОЛОЖИТЬ). ✓
- Только хуки, CTA не трогаем → нигде не правим CTA-логику (явно в Global Constraints). ✓
- Схема с формат+шаблон → Task 1. ✓
- Операция ВЗЯТЬ (фильтр/ранг/подстановка/фоллбэк) → Task 2. ✓
- Проводка reels (удаление patterns) + carousel → Task 4, 5. ✓
- Сид: 2 ИИ + 10 Ника, .base → Task 6. ✓
- Тесты evals → Task 7. ✓
- Витрина + install → Task 3, 8. ✓

**Зависимость-ловушка:** Task 6 берёт 2 ИИ-хука из `reels-script/references/patterns/`, который удаляется в Task 4. → При инлайн-исполнении выполнить копирование исходников ДО Task 4, либо восстановить из git-истории. Помечено в Task 6 Step 1.

**Placeholder scan:** конкретные пути/команды/значения везне; «TBD/TODO» нет.

**Type consistency:** имена операций (ПОЛОЖИТЬ/ВЗЯТЬ), поля схемы (тип_хука/формат/шаблон/когда_работает/кросс_нишевость/источник/метрики), формат имени файла — единообразны во всех задачах и совпадают со спеком.
