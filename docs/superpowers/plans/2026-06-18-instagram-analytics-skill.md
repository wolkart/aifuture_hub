# instagram-analytics Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Собрать тул-скилл `instagram-analytics` — разведчик ниши/конкурентов на Apify: по профилю/ссылкам собирает посты/рилс с метриками, ранжирует и выгружает в структурированную базу (Markdown index + карточки + CSV), с выборочным Tier-2 обогащением (транскрипт + разбор сценария).

**Architecture:** Процедурный (тул) скилл по образцу `instagram-downloader`/`ai-research`, но с `references/`. Папка `skills/instagram-analytics/` с `SKILL.md` (2 режима scout/enrich), `README.md`, `.env.template`, четырьмя `references/*.md` (apify, schema, asr, scenario-breakdown) и `evals/evals.json`. Вызовы инлайн (`curl` к Apify run-sync, `yt-dlp`/ASR), вариативность — в references. Единая DB-ingestible-схема записи рендерится в Markdown и CSV.

**Tech Stack:** Markdown (SKILL.md/README/references), JSON (evals), `.env` (Apify + ASR), инлайн `curl` (Apify API), `yt-dlp`/`ffmpeg` + конфигурируемый ASR. Глобальное подключение — `skills/install-skills.ps1`.

## Global Constraints

- Спек-источник (verbatim требования): `docs/superpowers/specs/2026-06-18-instagram-analytics-skill-design.md`.
- **Разведка для СВОЕГО контента, НЕ репост** (вшито, симметрично downloader): загруженное — референс; финал — переупаковка через `reels-script`/`carousel-script`.
- **Двухуровневость вшита:** `scout` (Tier-1, дёшево, массово, метрики+ранжирование, всегда работает) → `enrich` (Tier-2, выборочно: аудио→ASR→разбор сценария). Не обогащать всё подряд.
- **Файлы скилла:** `SKILL.md`, `README.md`, `.env.template`, `references/{apify,schema,asr,scenario-breakdown}.md`, `evals/evals.json`.
- **.env:** `APIFY_TOKEN`, `APIFY_ACTOR`, `ASR_PROVIDER`, `OPENAI_API_KEY`, `APIFY_ASR_ACTOR`, `OUTPUT_DIR`. Загрузка инлайн, без отдельного скрипта.
- **Конфигурируемость + грациозная деградация:** Apify-актор и ASR-движок настраиваются; ASR недоступен → транскрипт пуст, разбор по подписи, Tier-1 не ломается.
- **Выход:** `<OUTPUT_DIR>/index.md` + `cards/<id>.md` + `export.csv` по единой схеме. `OUTPUT_DIR` дефолт `./instagram-analytics-output`, override через `.env` (мостик к Obsidian-волту). Идемпотентность по `id`.
- **Схема записи (фикс.):** `id · author · url · type(reel/post/carousel) · date · caption · views · likes · comments · engagement_rate · video_url · hashtags · tier2_status(skeleton|enriched) · transcript · scenario{hook, body_beats, cta} · notes`. `engagement_rate = (likes + comments) / max(views, 1)`.
- **Хэндофф (мягкий):** рилс → `reels-script`; пост/карусель → `carousel-script`; база Markdown — самостоятельный артефакт.
- **Non-goals (YAGNI):** живой Sheets/БД-писатель; аналитика своего аккаунта/time-series; поиск по хештегу/нише; авто-обогащение всего; персистентная «база сценариев»+Гермес; дословный репост; meta-prompt.
- **Язык** — русский. **Дисциплина ответа** — как у всех скиллов хаба (без «думания вслух», без финального CTA к диалогу).
- **Каталог-витрина** `skills/README.md` + глобальное подключение через `skills/install-skills.ps1`.

---

## File Structure

- `skills/instagram-analytics/.env.template` — Apify + ASR + OUTPUT_DIR.
- `skills/instagram-analytics/references/schema.md` — **фундамент:** схема записи + шаблоны `index.md`/`card.md` + колонки CSV. На него ссылаются apify.md и SKILL.md.
- `skills/instagram-analytics/references/apify.md` — вызов Apify run-sync, input, парсинг датасета, маппинг в схему, идемпотентность.
- `skills/instagram-analytics/references/asr.md` — извлечение аудио + провайдеры ASR + грациозная деградация.
- `skills/instagram-analytics/references/scenario-breakdown.md` — разбор транскрипта на хук/тело/CTA.
- `skills/instagram-analytics/SKILL.md` — ядро: роль, главное правило, дисциплина, 2 режима, метод, выход, хэндофф, ограничения, ссылки на references.
- `skills/instagram-analytics/README.md` — применение + настройка `.env` + примеры.
- `skills/instagram-analytics/evals/evals.json` — кейсы.
- `skills/README.md` — **Modify:** строка каталога.
- Память (вне репозитория) — обновляет контроллер.

> **Про «тесты»:** скилл — прозаический артефакт. Аналог TDD — acceptance-проверка против спека (grep/чтение) и валидность JSON. Eval-кейсы — «тест-сьют» триггеринга/поведения.

---

## Task 1: `.env.template`

**Files:**
- Create: `skills/instagram-analytics/.env.template`

**Interfaces:**
- Produces: имена переменных `APIFY_TOKEN`, `APIFY_ACTOR`, `ASR_PROVIDER`, `OPENAI_API_KEY`, `APIFY_ASR_ACTOR`, `OUTPUT_DIR` — на них ссылаются references и SKILL.md. Должны совпадать буквально.

- [ ] **Step 1: Создать файл**

Записать `skills/instagram-analytics/.env.template`:

```
# Apify — разведка Instagram через actor
APIFY_TOKEN=
# id/slug актора IG-скрейпера (дефолт — публичный instagram-scraper); подставь свой при необходимости
APIFY_ACTOR=apify~instagram-scraper

# Транскрибация рилс для Tier-2 (enrich): openai | local | apify | none
ASR_PROVIDER=none
# Ключ OpenAI, если ASR_PROVIDER=openai (Whisper API)
OPENAI_API_KEY=
# id/slug ASR-актора, если ASR_PROVIDER=apify
APIFY_ASR_ACTOR=

# Куда писать базу выгрузки (Markdown index+карточки + CSV). Дефолт — папка в проекте.
# Укажи путь к своему Obsidian-волту, когда будешь готов — скилл переписывать не нужно.
OUTPUT_DIR=./instagram-analytics-output
```

- [ ] **Step 2: Acceptance**

Run: `grep -E "APIFY_TOKEN|APIFY_ACTOR|ASR_PROVIDER|OPENAI_API_KEY|APIFY_ASR_ACTOR|OUTPUT_DIR" skills/instagram-analytics/.env.template`
Expected: все 6 переменных присутствуют; `APIFY_ACTOR`, `ASR_PROVIDER=none`, `OUTPUT_DIR` имеют дефолты, ключи/токены пустые.

- [ ] **Step 3: Commit**

```bash
git add skills/instagram-analytics/.env.template
git commit -m "Add .env.template для instagram-analytics (Apify + ASR + OUTPUT_DIR)"
```

---

## Task 2: `references/schema.md` (фундамент: схема + шаблоны)

**Files:**
- Create: `skills/instagram-analytics/references/schema.md`

**Interfaces:**
- Produces: имена полей схемы и шаблоны `index.md`/`cards/<id>.md`/`export.csv` — используются в apify.md (маппинг), asr/scenario-breakdown (заполнение Tier-2), SKILL.md (выход).

- [ ] **Step 1: Создать файл**

Записать `skills/instagram-analytics/references/schema.md` (в файл идёт содержимое БЕЗ внешней 4-бэктиковой обёртки):

````markdown
# Схема записи и шаблоны выгрузки

Единый контракт: из этих полей рендерятся `index.md`, карточки `cards/<id>.md` и `export.csv`. Та же схема — будущий контракт для Sheets/БД-писателя и веб-интерфейса пользователя.

## Поля записи

| Поле | Тип | Источник | Описание |
|---|---|---|---|
| `id` | string | Apify (`shortCode`/`id`) | Уникальный id элемента, стабильный ключ идемпотентности |
| `author` | string | Apify | @handle автора |
| `url` | string | Apify | Прямая ссылка на пост/рилс |
| `type` | enum | Apify | `reel` \| `post` \| `carousel` |
| `date` | ISO date | Apify | Дата публикации |
| `caption` | string | Apify | Подпись |
| `views` | int | Apify | Просмотры (рилс; пусто/0 если нет) |
| `likes` | int | Apify | Лайки |
| `comments` | int | Apify | Комментарии |
| `engagement_rate` | float | вычисляется | `(likes + comments) / max(views, 1)`, округл. до 4 знаков |
| `video_url` | string | Apify | Прямая ссылка на видео (для Tier-2 ASR) |
| `hashtags` | list | Apify / из caption | Хештеги |
| `tier2_status` | enum | скилл | `skeleton` (только Tier-1) \| `enriched` (Tier-2 отработал) |
| `transcript` | string | Tier-2 ASR | Расшифровка речи (пусто, если не обогащён / ASR недоступен) |
| `scenario.hook` | string | Tier-2 LLM | Хук (текст + тип) |
| `scenario.body_beats` | list | Tier-2 LLM | Биты тела по порядку |
| `scenario.cta` | string | Tier-2 LLM | Призыв / лидмагнит |
| `notes` | string | пользователь/скилл | Свободные заметки |

## Шаблон `index.md`

```markdown
# Разведка: <author(ы)> — scout <дата>

Источник: Apify · Ранжировано по engagement_rate (убыв.)

| # | id | type | date | views | likes | comments | ER | tier2 | карточка |
|---|----|------|------|-------|-------|----------|----|-------|----------|
| 1 | <id> | reel | 2026-06-10 | 1200000 | 80000 | 1200 | 0.0676 | skeleton | [[cards/<id>]] |
```

## Шаблон карточки `cards/<id>.md`

```markdown
---
id: <id>
author: <author>
url: <url>
type: reel
date: 2026-06-10
views: 1200000
likes: 80000
comments: 1200
engagement_rate: 0.0676
video_url: <video_url>
hashtags: [tag1, tag2]
tier2_status: skeleton
---

# <author> — <type> от <date>

## Подпись
<caption>

## Транскрипт
(пусто до enrich)

## Разбор сценария
- **Хук:** (пусто до enrich)
- **Тело:** (пусто до enrich)
- **CTA:** (пусто до enrich)

## Заметки
<notes>
```

После `enrich`: `tier2_status: enriched`, заполнены Транскрипт и Разбор.

## Колонки `export.csv`

`id,author,url,type,date,caption,views,likes,comments,engagement_rate,video_url,hashtags,tier2_status,transcript,hook,body_beats,cta,notes`

Списки (`hashtags`, `body_beats`) — через `;`. Многострочный/запятый текст — в двойных кавычках по RFC 4180.
````

- [ ] **Step 2: Acceptance**

Run: `grep -nE "engagement_rate|tier2_status|cards/<id>|export.csv|body_beats" skills/instagram-analytics/references/schema.md`
Expected: формула `(likes + comments) / max(views, 1)` присутствует; перечислены все поля схемы; есть шаблоны index/card и строка колонок CSV. Файл начинается с `# Схема записи` (без внешней 4-бэктиковой обёртки).

- [ ] **Step 3: Commit**

```bash
git add skills/instagram-analytics/references/schema.md
git commit -m "Add references/schema.md instagram-analytics (схема записи + шаблоны выгрузки)"
```

---

## Task 3: `references/apify.md`

**Files:**
- Create: `skills/instagram-analytics/references/apify.md`

**Interfaces:**
- Consumes: `APIFY_TOKEN`, `APIFY_ACTOR` (Task 1); схему полей (Task 2).
- Produces: способ вызова Apify и маппинг ответа в схему — используется в SKILL.md (режим scout).

- [ ] **Step 1: Создать файл**

Записать `skills/instagram-analytics/references/apify.md` (без внешней 4-бэктиковой обёртки):

````markdown
# Apify — вызов и парсинг

## Конфиг (.env)
- `APIFY_TOKEN` — обязателен.
- `APIFY_ACTOR` — id/slug актора IG-скрейпера (дефолт `apify~instagram-scraper`). Конфигурируемо под подписку пользователя.

## Вызов (run-sync: один запрос → сразу элементы датасета)

```bash
curl --silent --request POST \
  "https://api.apify.com/v2/acts/$APIFY_ACTOR/run-sync-get-dataset-items?token=$APIFY_TOKEN" \
  --header "Content-Type: application/json" \
  --data '{"directUrls":["https://www.instagram.com/<handle>/"],"resultsType":"posts","resultsLimit":30}'
```

- **Профиль:** `directUrls` = ссылка на профиль; `resultsLimit` = сколько последних элементов (дефолт 30).
- **Конкретные ролики:** `directUrls` = массив ссылок на посты/рилс.
- Точные ключи input зависят от актора — адаптируй под фактический `APIFY_ACTOR`.

## Ответ
JSON-массив элементов датасета. Поля зависят от актора; типичные: `shortCode`/`id`, `ownerUsername`, `url`, `type`/`productType`, `timestamp`, `caption`, `videoViewCount`/`videoPlayCount`, `likesCount`, `commentsCount`, `videoUrl`, `hashtags`.

## Маппинг в схему (см. references/schema.md)
- `id` ← `shortCode` (или `id`)
- `author` ← `ownerUsername`
- `url` ← `url`
- `type` ← `reel`/`post`/`carousel` по `type`/`productType` (несколько медиа → carousel; есть `videoUrl` → reel)
- `date` ← `timestamp`
- `caption` ← `caption`
- `views` ← `videoViewCount`/`videoPlayCount` (пусто для не-видео)
- `likes` ← `likesCount`; `comments` ← `commentsCount`
- `engagement_rate` ← вычислить `(likes + comments) / max(views, 1)`, округлить до 4 знаков
- `video_url` ← `videoUrl`; `hashtags` ← `hashtags` (или распарсить из caption)

## Ранжирование
По `engagement_rate` (убыв.) при записи в `index.md`.

## Идемпотентность
Ключ — `id`. Повторный `scout`: обновлять существующие записи по `id`, не плодить дубли.

## Ошибки
Пустой/ошибочный ответ Apify (неверный токен, актор, приватный профиль) — сообщи честно, не выдумывай элементы.
````

- [ ] **Step 2: Acceptance**

Run: `grep -nE "run-sync-get-dataset-items|APIFY_TOKEN|engagement_rate|идемпотент|directUrls" skills/instagram-analytics/references/apify.md`
Expected: эндпоинт run-sync, curl с токеном, маппинг с формулой ER, раздел идемпотентности. Файл начинается с `# Apify`.

- [ ] **Step 3: Commit**

```bash
git add skills/instagram-analytics/references/apify.md
git commit -m "Add references/apify.md instagram-analytics (run-sync вызов + маппинг в схему)"
```

---

## Task 4: `references/asr.md` + `references/scenario-breakdown.md` (Tier-2)

**Files:**
- Create: `skills/instagram-analytics/references/asr.md`
- Create: `skills/instagram-analytics/references/scenario-breakdown.md`

**Interfaces:**
- Consumes: `ASR_PROVIDER`, `OPENAI_API_KEY`, `APIFY_ASR_ACTOR` (Task 1); поля `transcript`, `scenario.*`, `tier2_status` (Task 2).
- Produces: процедуру Tier-2 (транскрипт + разбор) — используется в SKILL.md (режим enrich).

- [ ] **Step 1: Создать `references/asr.md`**

Записать `skills/instagram-analytics/references/asr.md` (без внешней 4-бэктиковой обёртки):

````markdown
# ASR (Tier-2) — транскрибация рилса

Конфигурируемо через `ASR_PROVIDER` (.env): `openai` | `local` | `apify` | `none`. **Грациозная деградация:** `none` или ошибка → транскрипт пуст, разбор делается по подписи; Tier-1-данные не трогаются.

## Шаг 0 — извлечь аудио из видео
```bash
yt-dlp -x --audio-format mp3 "<video_url>" -o "audio-<id>.mp3"
# либо, если video_url прямой:
# curl -L "<video_url>" -o "v-<id>.mp4" && ffmpeg -i "v-<id>.mp4" -vn -acodec libmp3lame "audio-<id>.mp3"
```

## openai (Whisper API) — нужен `OPENAI_API_KEY`
```bash
curl --silent https://api.openai.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F file="@audio-<id>.mp3" -F model="whisper-1"
# ответ: {"text":"..."} → transcript
```

## local (whisper/faster-whisper установлен)
```bash
whisper "audio-<id>.mp3" --model small --output_format txt
# текст из audio-<id>.txt → transcript
```

## apify (ASR-актор) — нужен `APIFY_ASR_ACTOR`
Вызов как в references/apify.md (run-sync), вход — ссылка/файл аудио; из ответа взять текстовое поле → transcript.

## none / ошибка
Транскрипт = пусто. В карточке пометь: «транскрипт недоступен (ASR не настроен)». Переходи к разбору по подписи (см. scenario-breakdown.md).
````

- [ ] **Step 2: Создать `references/scenario-breakdown.md`**

Записать `skills/instagram-analytics/references/scenario-breakdown.md` (без внешней 4-бэктиковой обёртки):

````markdown
# Разбор сценария (Tier-2)

Из `transcript` (или, при деградации, из `caption`) разложи рилс на структуру виральности — общий вокабуляр с `reels-script`:

- **Хук** (1–3 сек): первая фраза/приём, что останавливает скролл. Тип: провокация / неожиданность / интрига / отрицание / обещание.
- **Тело-биты:** последовательность смысловых шагов (атомов), каждый — наблюдаемое действие/мысль.
- **CTA / лидмагнит:** чем заканчивается, какой призыв.

## Заполнение карточки (поля схемы)
- `scenario.hook` — одна строка: текст хука + (тип).
- `scenario.body_beats` — список битов по порядку.
- `scenario.cta` — одна строка.
- `tier2_status` → `enriched` (enrich отработал, даже если данных мало).

## Правила
- Только то, что реально есть в транскрипте/подписи; недостающее не выдумывать — помечать «не явно».
- Транскрипт пуст и подпись неинформативна → поля разбора помечай «недостаточно данных»; `tier2_status` всё равно `enriched` (Tier-2 был запущен).
````

- [ ] **Step 3: Acceptance**

Run: `grep -nE "ASR_PROVIDER|whisper-1|грациозн|деградац" skills/instagram-analytics/references/asr.md && grep -nE "Хук|body_beats|enriched|не выдумыв" skills/instagram-analytics/references/scenario-breakdown.md`
Expected: asr.md — 4 провайдера + деградация + извлечение аудио; scenario-breakdown.md — структура хук/тело/CTA, заполнение полей, правило «не выдумывать». Оба файла начинаются с `#` заголовка (без внешней обёртки).

- [ ] **Step 4: Commit**

```bash
git add skills/instagram-analytics/references/asr.md skills/instagram-analytics/references/scenario-breakdown.md
git commit -m "Add references asr.md + scenario-breakdown.md instagram-analytics (Tier-2)"
```

---

## Task 5: `SKILL.md` (ядро)

**Files:**
- Create: `skills/instagram-analytics/SKILL.md`

**Interfaces:**
- Consumes: `.env` (Task 1), все references (Tasks 2–4).
- Produces: триггер-`description`; контракт режимов scout/enrich; хэндофф рилс→reels-script, пост/карусель→carousel-script.

- [ ] **Step 1: Создать файл**

Записать `skills/instagram-analytics/SKILL.md` (в файл идёт содержимое БЕЗ внешней 4-бэктиковой обёртки — начинается с `---` frontmatter, заканчивается разделом «## Где что брать»; внутренние тройные бэктики сохранить):

`````markdown
---
name: instagram-analytics
description: >-
  Разведчик ниши/конкурентов в Instagram через Apify: по профилю(ям) @handle/URL
  или ссылкам на ролики собирает посты/рилс с метриками, ранжирует «что залетело»
  и выгружает в структурированную базу (Markdown-индекс + карточки + CSV).
  Двухуровнево: scout (массово, дёшево, метрики+ранжирование) → enrich (выборочно:
  аудио→транскрипт→разбор сценария хук/тело/CTA). Используй всегда, когда пользователь
  хочет «разобрать конкурента», «что залетает в нише», «выгрузить посты/рилс конкурента
  в таблицу/базу», «собрать референсы рилс», «проанализировать профиль конкурента». Это
  разведка для СВОЕГО контента (референс → переупаковка в reels-script/carousel-script),
  не репост. НЕ для аналитики своего аккаунта/дашбордов, не для поиска по хештегу, не для
  скачивания одного поста (это instagram-downloader).
---

# Instagram-analytics — разведчик ниши/конкурентов

Ты — **разведчик контента**. По профилю(ям) конкурента или ссылкам на ролики через Apify собираешь посты/рилс с метриками, ранжируешь «что залетело» и выгружаешь в **структурированную базу** (Markdown + CSV). Цель — найти, что заходит в нише, разобрать сценарии и дать пользователю основу для СВОЕГО контента.

## Главное правило (вшито в суть)

Это **разведка для создания СВОЕГО контента**, а НЕ качалка для репоста чужого.

- Собранное **всегда** трактуется как **референс**; финал — переупаковка через `reels-script` / `carousel-script`.
- Ты **никогда** не предлагаешь дословный репост.
- Качаются публичные данные конкурента; соблюдение ToS — на стороне пользователя.

## Дисциплина ответа (что видит пользователь)

Пользователю нужен **результат (база + сводка), а не отчёт о ходе мыслей**. Вызов Apify, парсинг, запись файлов делай молча.

- **Не печатай рассуждения** вроде «Зову Apify…», «Парсю датасет…». Никакого «думания вслух».
- Видимый ответ: (1) сводка выгрузки (сколько собрано, топ по ER, пути к файлам); (2) при `enrich` — краткий разбор обогащённых; (3) блок «Допущения», если что-то вывел сам (ниша, OUTPUT_DIR, выбор для enrich).
- **Не заканчивай призывом к диалогу.**

## Два режима

Определи режим по запросу. Дефолт — `scout`.

### `scout` (Tier-1 — дёшево, массово)

1. Извлеки вход: профиль(и) `@handle`/URL и/или ссылки на посты/рилс.
2. Вызови Apify (см. [references/apify.md](references/apify.md)).
3. Распарси датасет и **смаппь в схему** (см. [references/schema.md](references/schema.md)); вычисли `engagement_rate`.
4. Ранжируй по `engagement_rate` (убыв.).
5. Запиши/обнови в `<OUTPUT_DIR>`: `index.md` (ранжированная таблица), карточки-скелеты `cards/<id>.md` (`tier2_status: skeleton`), `export.csv`. Идемпотентно по `id`.
6. Без ASR/LLM-разбора — токены почти не тратятся.

### `enrich` (Tier-2 — дорого, выборочно)

1. Вход: выборка — `top-N`, список `#id`, или конкретные URL (из уже собранной базы).
2. По каждому выбранному рилсу: извлеки аудио → транскрибируй (см. [references/asr.md](references/asr.md)) → разложи сценарий (см. [references/scenario-breakdown.md](references/scenario-breakdown.md)).
3. **Допиши** транскрипт и разбор в существующую карточку и строку CSV; обнови `tier2_status` → `enriched`.
4. Грациозная деградация: ASR не настроен/ошибка → транскрипт пуст, разбор по подписи; `tier2_status` всё равно `enriched`.

## Метод

- **Apify:** `APIFY_TOKEN` + конфигурируемый `APIFY_ACTOR` в `.env`; вызов инлайн через `run-sync-get-dataset-items`. Детали — [references/apify.md](references/apify.md).
- **Выход:** `<OUTPUT_DIR>` (дефолт `./instagram-analytics-output`, override в `.env` — мостик к Obsidian-волту). Структура и схема — [references/schema.md](references/schema.md).
- **ASR (Tier-2):** конфигурируемый `ASR_PROVIDER` + деградация — [references/asr.md](references/asr.md).
- **Разбор сценария:** [references/scenario-breakdown.md](references/scenario-breakdown.md).
- **Без отдельного скрипта** — вызовы инлайн (`curl`, `yt-dlp`/ASR-команда).

## Выход (сводка пользователю)

После `scout` — сводка: сколько элементов собрано, топ-3 по ER, пути к `index.md`/`export.csv`. После `enrich` — какие id обогащены + краткий разбор (хук/тело/CTA). Не вываливай всю таблицу в чат — она в файлах.

## Хэндофф (мягкий)

- **Рилс** (особенно залетевший/обогащённый) → `reels-script`: суть + транскрипт/подпись как тезис, ниша пользователя → свой сценарий.
- **Пост/карусель** → `carousel-script`: суть + подпись как тема, ниша → своя карусель.
- **База Markdown — самостоятельный артефакт** и сид для будущей «базы вирусных сценариев».

## Ограничения

- **.env:** `APIFY_TOKEN`, `APIFY_ACTOR`, `ASR_PROVIDER`, `OPENAI_API_KEY`, `APIFY_ASR_ACTOR`, `OUTPUT_DIR` (шаблон — `.env.template`).
- **Только переупаковка** — дословный репост запрещён дизайном.
- **Не входит:** живой Sheets/БД-писатель; аналитика своего аккаунта/дашборды; поиск по хештегу/нише; авто-обогащение всего подряд; персистентная «база сценариев» + Гермес; OCR.
- **Конкретика, без выдумок:** только реальные данные Apify; нет данных → поле пусто/помечено.

## Где что брать (references)

- **Схема и шаблоны выгрузки** — [references/schema.md](references/schema.md).
- **Apify (вызов + маппинг)** — [references/apify.md](references/apify.md).
- **ASR (Tier-2)** — [references/asr.md](references/asr.md).
- **Разбор сценария** — [references/scenario-breakdown.md](references/scenario-breakdown.md).
`````

- [ ] **Step 2: Acceptance — frontmatter и триггеры**

Run: `grep -nE "^name:|scout|enrich|reels-script|carousel-script|instagram-downloader" skills/instagram-analytics/SKILL.md`
Expected: `name: instagram-analytics`; в description — режимы scout/enrich, оба приёмника хэндоффа, исключение instagram-downloader. Файл начинается с `---`.

- [ ] **Step 3: Acceptance — режимы, метод, ссылки на references**

Run: `grep -nE "references/(apify|schema|asr|scenario-breakdown).md|engagement_rate|tier2_status|OUTPUT_DIR|run-sync" skills/instagram-analytics/SKILL.md`
Expected: все 4 references слинкованы; упомянуты ER, tier2_status, OUTPUT_DIR, run-sync. Главное правило «референс, не репост» присутствует (прочитать § Главное правило).

- [ ] **Step 4: Commit**

```bash
git add skills/instagram-analytics/SKILL.md
git commit -m "Add SKILL.md instagram-analytics (scout/enrich, Apify, выгрузка в базу, хэндофф)"
```

---

## Task 6: `README.md`

**Files:**
- Create: `skills/instagram-analytics/README.md`

**Interfaces:**
- Consumes: `.env` (Task 1), режимы/хэндофф (Task 5).

- [ ] **Step 1: Создать файл**

Записать `skills/instagram-analytics/README.md` (без внешней 4-бэктиковой обёртки):

````markdown
# instagram-analytics — где применять

Скилл разведывает нишу/конкурентов в Instagram через Apify: по профилю или ссылкам собирает посты/рилс с метриками, ранжирует «что залетело» и выгружает в **структурированную базу** (Markdown-индекс + карточки + CSV). Это разведка для **своего контента** (референс → переупаковка), а не репост.

## Когда срабатывает

- «Разбери конкурента / нишу», «что залетает у X», «выгрузи рилс/посты конкурента в таблицу/базу», «собери референсы рилс», «проанализируй профиль».

НЕ для аналитики своего аккаунта/дашбордов, не для поиска по хештегу, не для скачивания одного поста (это `instagram-downloader`), не для дословного репоста.

## Два режима

- **`scout`** (дефолт) — массово и дёшево: метрики + ранжирование + выгрузка базы.
- **`enrich`** — выборочно по отмеченным рилс: аудио → транскрипт → разбор сценария (хук/тело/CTA), дописывается в карточку.

## Настройка `.env`

```
cp .env.template .env
# APIFY_TOKEN=<твой токен Apify>
# APIFY_ACTOR=<актор IG-скрейпера; дефолт apify~instagram-scraper>
# ASR_PROVIDER=openai|local|apify|none   (для enrich; none = без транскрипта)
# OPENAI_API_KEY=<если ASR_PROVIDER=openai>
# OUTPUT_DIR=<куда писать базу; дефолт ./instagram-analytics-output, можно путь к Obsidian-волту>
```

## Выгрузка

`<OUTPUT_DIR>/index.md` (ранжированная таблица) + `cards/<id>.md` (карточка на элемент) + `export.csv` (для Sheets). Единая схема — мостик к будущей БД/веб-интерфейсу.

## Хэндофф

- рилс → `reels-script`; пост/карусель → `carousel-script` (с нишей пользователя).

## Примеры вызова

```
разбери конкурента @nik.travel — выгрузи последние рилс с метриками
```

```
enrich: обработай по полной топ-3 из последней разведки
```

В ответ — сводка выгрузки и пути к файлам базы (при enrich — краткий разбор сценариев).
````

- [ ] **Step 2: Acceptance**

Run: `grep -nE "cp .env.template|APIFY_TOKEN|scout|enrich|reels-script|carousel-script|OUTPUT_DIR" skills/instagram-analytics/README.md`
Expected: инструкция `.env` со всеми ключевыми переменными, оба режима, оба приёмника хэндоффа.

- [ ] **Step 3: Commit**

```bash
git add skills/instagram-analytics/README.md
git commit -m "Add README применения instagram-analytics (.env + режимы + хэндофф)"
```

---

## Task 7: `evals/evals.json`

**Files:**
- Create: `skills/instagram-analytics/evals/evals.json`

**Interfaces:**
- Consumes: поведение из Tasks 2–5 (режимы, схема, деградация, хэндофф, анти-репост).

- [ ] **Step 1: Создать файл**

Записать `skills/instagram-analytics/evals/evals.json` (чистый JSON, начинается с `{`):

```json
{
  "skill_name": "instagram-analytics",
  "evals": [
    {
      "id": 1,
      "prompt": "разбери конкурента @nik.travel — выгрузи последние рилс с метриками",
      "expected_output": "Режим scout: Apify-вызов, ранжированный index.md + карточки-скелеты + export.csv в OUTPUT_DIR, сводка с топом по ER",
      "files": []
    },
    {
      "id": 2,
      "prompt": "enrich: обработай по полной топ-3 из последней разведки",
      "expected_output": "Режим enrich: по 3 рилс аудио→транскрипт→разбор сценария (хук/тело/CTA), дописано в карточки, tier2_status=enriched",
      "files": []
    },
    {
      "id": 3,
      "prompt": "у меня не настроен ASR, всё равно разбери сценарий вот этого рилса https://instagram.com/reel/ABC",
      "expected_output": "Грациозная деградация: транскрипт пуст, разбор по подписи, tier2_status=enriched, честно помечено что ASR недоступен",
      "files": []
    },
    {
      "id": 4,
      "prompt": "скачай мне этот рилс конкурента чтобы выложить как есть https://instagram.com/reel/XYZ",
      "expected_output": "Скилл трактует как референс, не репост; ведёт к переупаковке через reels-script (а одиночная выгрузка медиа — это instagram-downloader)",
      "files": []
    }
  ],
  "assertions": [
    "Режим определён верно: 1→scout, 2→enrich, 3→enrich(деградация), 4→анти-репост/референс",
    "scout: Apify run-sync, маппинг в схему, engagement_rate вычислен, ранжирование по убыв.",
    "scout пишет index.md + cards/<id>.md (skeleton) + export.csv в OUTPUT_DIR, идемпотентно по id",
    "enrich выборочно (top-N/#id/URL): транскрипт + разбор хук/тело/CTA, дописывает в карточку, tier2_status=enriched",
    "Грациозная деградация ASR: нет движка → транскрипт пуст, разбор по подписи, помечено честно",
    "Хэндофф: рилс→reels-script, пост/карусель→carousel-script с нишей пользователя",
    "Анти-репост: собранное = референс, дословный репост не предлагается",
    "Дисциплина ответа: без «думания вслух», без финального CTA; таблица в файлах, не в чате",
    "Конкретика: только реальные данные Apify, нет данных → поле пусто/помечено, без выдумок"
  ]
}
```

- [ ] **Step 2: Acceptance — валидность JSON**

Run: `node -e "JSON.parse(require('fs').readFileSync('skills/instagram-analytics/evals/evals.json','utf8'));console.log('ok')"`
(если node нет — `python -c "import json;json.load(open('skills/instagram-analytics/evals/evals.json',encoding='utf-8'));print('ok')"`)
Expected: `ok`. 4 кейса + assertions покрывают scout/enrich/деградацию/анти-репост/хэндофф/дисциплину.

- [ ] **Step 3: Commit**

```bash
git add skills/instagram-analytics/evals/evals.json
git commit -m "Add eval-кейсы для instagram-analytics"
```

---

## Task 8: Каталог + глобальное подключение + память

**Files:**
- Modify: `skills/README.md`
- Run: `skills/install-skills.ps1`
- Память (вне репозитория) — контроллер.

- [ ] **Step 1: Добавить в каталог**

В `skills/README.md`, в таблицу «Каталог», после строки `instagram-downloader` добавить:

```markdown
| [instagram-analytics/](instagram-analytics/) | Разведка ниши/конкурентов через Apify: scout (метрики+ранжирование) → enrich (транскрипт+разбор сценария), выгрузка в Markdown-базу + CSV; хэндофф в reels-script/carousel-script |
```

- [ ] **Step 2: Acceptance**

Run: `grep -n "instagram-analytics" skills/README.md`
Expected: строка таблицы со ссылкой `[instagram-analytics/](instagram-analytics/)`.

- [ ] **Step 3: Подключить глобально**

Run: `powershell -ExecutionPolicy Bypass -File skills/install-skills.ps1`
Expected: junction для `instagram-analytics` создан в `~/.claude/skills/` (или уже существует). Существующие не тронуты.

- [ ] **Step 4: Acceptance junction**

Run: `ls "$HOME/.claude/skills/" | grep instagram-analytics`
Expected: `instagram-analytics` присутствует.

- [ ] **Step 5: Commit (только каталог)**

```bash
git add skills/README.md
git commit -m "Add instagram-analytics в каталог скиллов"
```

(Память лежит вне репозитория — обновляет контроллер.)

---

## Self-Review

**1. Spec coverage:**
- §1 Цель / двухуровневость → Task 5 (scout/enrich) + Tasks 2–4 (references).
- §2 Границы / §9 Non-goals → Task 5 § Ограничения + description.
- §3 Режимы scout/enrich → Task 5.
- §4 Метод (Apify run-sync, ER, ASR, разбор) → Tasks 3, 4 + Task 5 § Метод.
- §5 Выход (схема, index/card/csv, OUTPUT_DIR, идемпотентность) → Task 2 + Task 1 (OUTPUT_DIR) + Task 5.
- §6 Хэндофф (рилс→reels-script, пост/карусель→carousel-script, мягкий) → Task 5.
- §7 Ограничения (.env, дисциплина, без выдумок) → Task 1 + Task 5.
- §8 Файлы → Tasks 1–7.
- Правило CLAUDE.md (каталог + глобальная установка) → Task 8.

**2. Placeholder scan:** Полные тексты файлов даны целиком. `<id>`, `<handle>`, `<OUTPUT_DIR>`, `<video_url>`, `<ниша>` — намеренные плейсхолдеры внутри инструкций скилла (рантайм), не пропуски плана.

**3. Type consistency:** имена `.env` (`APIFY_TOKEN`/`APIFY_ACTOR`/`ASR_PROVIDER`/`OPENAI_API_KEY`/`APIFY_ASR_ACTOR`/`OUTPUT_DIR`) совпадают в Tasks 1, 3, 4, 5, 6. Поля схемы (`engagement_rate`, `tier2_status`, `scenario.{hook,body_beats,cta}`, `transcript`) совпадают в Tasks 2, 3, 4, 5, 7. Файлы references слинкованы из SKILL.md ровно теми путями, что созданы в Tasks 2–4. Приёмники хэндоффа `reels-script`/`carousel-script` совпадают в Tasks 5, 6, 7. Формула ER `(likes + comments) / max(views, 1)` идентична в Tasks 2, 3.
