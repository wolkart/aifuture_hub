# Apify — вызов и парсинг

## Конфиг (.env)
- `APIFY_TOKEN` — обязателен (основной аккаунт).
- `APIFY_TOKEN_2`, `APIFY_TOKEN_3`, … — опциональные запасные аккаунты для авто-переключения (см. «Несколько ключей»).
- `APIFY_ACTOR` — id/slug актора IG-скрейпера (дефолт `apify~instagram-scraper`). Конфигурируемо под подписку пользователя.

## Несколько ключей (авто-переключение при исчерпании)
Начинай с `APIFY_TOKEN`. Если вызов вернул ошибку исчерпания лимита/средств (HTTP `402`, либо тело с `monthly-usage-hard-limit-exceeded` / упоминанием лимита или нехватки кредитов) — **переключись на следующий заполненный токен** (`APIFY_TOKEN_2`, затем `APIFY_TOKEN_3`, …) и повтори тот же запрос. Перебирай по порядку, пока запрос не пройдёт или не кончатся ключи. Полезно на free-тарифе ($5/мес на аккаунт): кончился один — берём следующий без остановки. Если все ключи исчерпаны — сообщи честно, не выдумывай данные.

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
Пустой/ошибочный ответ Apify (неверный токен, актор, приватный профиль) — сообщи честно, не выдумывай элементы. Ошибку исчерпания лимита/средств обрабатывай через авто-переключение ключей (см. «Несколько ключей»).
