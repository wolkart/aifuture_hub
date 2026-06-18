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
