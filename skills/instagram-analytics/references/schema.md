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
