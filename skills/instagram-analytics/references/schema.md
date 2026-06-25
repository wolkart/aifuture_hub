# Схема записи и шаблоны выгрузки

Единый контракт: из этих полей рендерятся `index.md`, карточки `cards/<id>.md` и `export.csv`. Та же схема — будущий контракт для Sheets/БД-писателя и веб-интерфейса пользователя.

## Структура выгрузки (per-blogger)

Выгрузка **разбивается по авторам** — каждый блогер в своей подпапке, чтобы база на 30+ конкурентов оставалась навигабельной:

```
<OUTPUT_DIR>/
  _Разведка.base            ← Obsidian Base: ВСЕ карточки разведки в одном фильтруемом срезе
  <author>/                 ← подпапка на блогера (по @handle)
    index.md                ← ранжированная таблица этого блогера
    cards/<id>.md           ← карточки этого блогера
    export.csv              ← CSV этого блогера
  <author2>/ …
```

- Папка автора = `<OUTPUT_DIR>/<author>` (имя = `@handle` без `@`). Идемпотентность — по `id` внутри папки автора.
- При разведке нескольких профилей сразу — у каждого своя подпапка; `_Разведка.base` (см. ниже) даёт сводный кросс-блогерный вид.
- **Видео не хранятся:** mp4 качается во временную папку только под ASR (Tier-2) и стирается; в волт кладётся `video_url`, не файл (волт остаётся лёгким).

## Поля записи

| Поле | Тип | Источник | Описание |
|---|---|---|---|
| `id` | string | Apify (`shortCode`/`id`) | Уникальный id элемента, стабильный ключ идемпотентности |
| `title` | string | скилл (из caption) | Короткий человекочитаемый ярлык темы — для навигации (alias карточки, колонка-ссылка в index) |
| `author` | string | Apify | @handle автора |
| `url` | string | Apify | Прямая ссылка на пост/рилс |
| `type` | enum | Apify | `reel` \| `post` \| `carousel` |
| `date` | ISO date | Apify | Дата публикации |
| `caption` | string | Apify | Подпись |
| `views` | int | Apify | Просмотры (рилс; пусто/0 если нет) |
| `likes` | int | Apify | Лайки |
| `comments` | int | Apify | Комментарии |
| `engagement_rate` | float | вычисляется | `(likes + comments) / max(views, 1)`, округл. до 4 знаков. Считается только при `views > 0` (видео); у не-видео — пусто, такие идут ниже видео при ранжировании |
| `video_url` | string | Apify | Прямая ссылка на видео (для Tier-2 ASR; в волте не хранится файл) |
| `hashtags` | list | Apify / из caption | Хештеги |
| `tier2_status` | enum | скилл | `skeleton` (только Tier-1) \| `enriched` (Tier-2 отработал) |
| `transcript` | string | Tier-2 ASR | Расшифровка речи на языке оригинала (пусто, если не обогащён / ASR недоступен) |
| `transcript_ru` | string | Tier-2 LLM | **Дословный** перевод транскрипта на русский (пусто, если оригинал уже RU или нет транскрипта) |
| `scenario.hook` | string | Tier-2 LLM | Хук (текст + тип) |
| `scenario.body_beats` | list | Tier-2 LLM | Биты тела по порядку |
| `scenario.cta` | string | Tier-2 LLM | Призыв / лидмагнит |
| `notes` | string | пользователь/скилл | Свободные заметки |

### `title` — как получать
Короткий ярлык (≈3–7 слов) из `caption`: для коммент-бейт подписей («Comment "WORD" to get …») — суть оффера + ключевое слово в скобках, напр. `AI-аватар, open-source (AVATAR)`; иначе — первое осмысленное словосочетание подписи. Обрезать по границе слова, без `|`, `[`, `]`. Назначение — навигация: `title` идёт в `aliases` карточки, в её H1 и как **текст ссылки** в `index.md`.

## Шаблон `index.md`

Колонка «Тема» — это **читаемая кликабельная ссылка** в карточку (внутри таблицы `|` алиаса экранируется как `\|`):

```markdown
# Разведка: @<author> — scout <дата>

Источник: Apify · Ранжировано по engagement_rate (убыв.). ER = (лайки+комменты)/просмотры.
Видео — по ER; не-видео — ниже, по вовлечённости. Клик по теме → карточка.

| # | Тема | type | date | views | likes | comments | ER | tier2 |
|---|------|------|------|-------|-------|----------|----|-------|
| 1 | [[cards/<id>\|<title>]] | reel | 2026-06-10 | 1200000 | 80000 | 1200 | 0.0676 | skeleton |
```

## Шаблон карточки `cards/<id>.md`

```markdown
---
aliases: ["<title>"]
id: <id>
title: <title>
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

# <title>

*[[<author>]] · <type> · <date>*

## Подпись
<caption>

## Транскрипт
(пусто до enrich)

## Транскрипт (RU)
(пусто до enrich)

## Разбор сценария
- **Хук:** (пусто до enrich)
- **Тело:** (пусто до enrich)
- **CTA:** (пусто до enrich)

## Заметки
<notes>
```

- `[[<author>]]` — бэклинк на хаб-заметку блогера (создаётся пустой, если её нет): связывает все карточки одного автора в графе.

После `enrich`: `tier2_status: enriched`, заполнены Транскрипт, **Транскрипт (RU)** и Разбор.

После enrich карточка `cards/<id>.md` несёт полную схему во frontmatter:

```markdown
---
aliases: ["<title>"]
id: <id>
title: <title>
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
tier2_status: enriched
transcript: |
  <полная расшифровка речи рилса на языке оригинала>
transcript_ru: |
  <дословный перевод на русский>
scenario:
  hook: "<текст хука> (<тип>)"
  body_beats:
    - "<бит 1>"
    - "<бит 2>"
  cta: "<призыв / лидмагнит>"
notes: <notes>
---

(тело карточки — те же поля в читаемом виде: ## Подпись, ## Транскрипт, ## Транскрипт (RU), ## Разбор сценария, ## Заметки)
```

Так frontmatter = полная схема записи (для frontmatter-парсера БД), тело — читаемое зеркало, а `export.csv` — плоский full-schema артефакт для импорта в Sheets/БД.

## Шаблон `_Разведка.base` (Obsidian Base)

Один Base в корне `<OUTPUT_DIR>` агрегирует карточки **всех** блогеров — кросс-блогерный срез без ручной поддержки:

```yaml
filters:
  and:
    - file.hasProperty("engagement_rate")
    - file.folder.contains("cards")
views:
  - type: table
    name: Все по ER
    order: [title, author, type, engagement_rate, views, tier2_status]
    sort:
      - property: engagement_rate
        direction: DESC
  - type: table
    name: По блогерам
    order: [author, title, engagement_rate, views, date]
    sort:
      - property: author
        direction: ASC
      - property: engagement_rate
        direction: DESC
```

Синтаксис Bases капризен к версии — если вид пуст/ошибка, упростить фильтр (`file.hasProperty("engagement_rate")`) и сортировку.

## Колонки `export.csv`

`id,title,author,url,type,date,caption,views,likes,comments,engagement_rate,video_url,hashtags,tier2_status,transcript,transcript_ru,hook,body_beats,cta,notes`

Списки (`hashtags`, `body_beats`) — через `;`. Многострочный/запятый текст — в двойных кавычках по RFC 4180.
