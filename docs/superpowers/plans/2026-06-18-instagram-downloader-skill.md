# instagram-downloader Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Собрать тул-скилл `instagram-downloader`, который по ссылке на Instagram вытаскивает медиа + подпись (RapidAPI с yt-dlp-фоллбэком) и обязательно передаёт референс на переупаковку в `reels-script` / `carousel-script`.

**Architecture:** Процедурный (тул) скилл по образцу `ai-research`: одна папка `skills/instagram-downloader/` с `SKILL.md` (роль + флоу + метод + обязательный хэндофф), `README.md` (применение + настройка `.env`), `.env.template` (`RAPIDAPI_KEY`, `RAPIDAPI_HOST`) и `evals/evals.json` (триггер- и поведенческие кейсы). Загрузка — инлайн через `curl`/`yt-dlp` в SKILL.md, без отдельного скрипта. Скилл НЕ контентный — meta-prompt не используется.

**Tech Stack:** Markdown (SKILL.md/README.md), JSON (evals), `.env` (RapidAPI), инлайн `curl` + `yt-dlp` фоллбэк. Глобальное подключение — `skills/install-skills.ps1`.

## Global Constraints

- Спек-источник (verbatim требования): `docs/superpowers/specs/2026-06-18-instagram-downloader-skill-design.md`.
- **Обязательная переупаковка вшита в суть:** скилл — инструмент извлечения референса для СВОЕГО контента, НЕ качалка для дословного репоста. Дословный репост не предлагается и не выполняется. Финал — переупакованный оригинал через `reels-script`/`carousel-script`.
- **Файлы скилла (ровно эти):** `SKILL.md`, `README.md`, `.env.template`, плюс `evals/evals.json` по паттерну хаба.
- **`.env`:** `RAPIDAPI_KEY`, `RAPIDAPI_HOST`. Без отдельного скрипта — загрузка инлайн `curl` (RapidAPI) / `yt-dlp` (фоллбэк).
- **Non-goals (YAGNI):** не репостить дословно; не доставлять в Telegram (рантайм/Hermes); не делать аналитику профиля/метрики (отдельный `instagram-analytics`, Apify); не использовать meta-prompt; не делать OCR слайдов / транскрипт рилса.
- **Язык** — русский, как у всех скиллов хаба. **Дисциплина ответа** — как у `reels-script`/`ai-research`: без «думания вслух», без финального CTA к диалогу.
- **Каталог-витрина:** каждый новый скилл добавляется в `skills/README.md` (таблица).
- **Глобальное подключение:** после создания запустить `skills/install-skills.ps1` (идемпотентно создаёт junction в `~/.claude/skills/`).
- **Имена скиллов-приёмников хэндоффа** (verbatim): `reels-script` (для рилс/видео), `carousel-script` (для пост/карусель).

---

## File Structure

- `skills/instagram-downloader/.env.template` — переменные RapidAPI (`RAPIDAPI_KEY`, `RAPIDAPI_HOST`).
- `skills/instagram-downloader/SKILL.md` — ядро: frontmatter с триггер-описанием, роль, главное правило (референс ≠ репост), дисциплина ответа, флоу (6 шагов), метод (RapidAPI + yt-dlp фоллбэк), выход (repackage-ready), обязательный хэндофф, ограничения/этика.
- `skills/instagram-downloader/README.md` — где применять, метод, настройка `.env`, хэндофф, пример вызова.
- `skills/instagram-downloader/evals/evals.json` — триггер- и поведенческие кейсы + ассершены.
- `skills/README.md` — **Modify:** добавить строку в таблицу каталога.
- `MEMORY.md` + `aifuture-hub-project.md` (в memory-папке) — **Modify:** обновить статус (скилл готов, очередь).

Каждый файл — один deliverable, один коммит. Задачи независимо ревьюятся: можно принять `.env.template`, но отклонить формулировки в `SKILL.md`.

> **Замечание про «тесты»:** скилл — прозаический артефакт, исполняемых unit-тестов нет. Аналог TDD здесь — **acceptance-проверка против спека**: каждый шаг проверки формулирует конкретный критерий и подтверждается чтением/`grep` по файлу. Eval-кейсы (`evals/evals.json`) — это «тест-сьют» триггеринга и поведения, прогоняемый через `skill-creator` при желании.

---

## Task 1: `.env.template` (переменные RapidAPI)

**Files:**
- Create: `skills/instagram-downloader/.env.template`

**Interfaces:**
- Produces: имена переменных `RAPIDAPI_KEY`, `RAPIDAPI_HOST` — на них ссылаются `SKILL.md` (§ Метод) и `README.md` (настройка). Должны совпадать буквально во всех трёх файлах.

- [ ] **Step 1: Создать `.env.template`**

Записать файл `skills/instagram-downloader/.env.template`:

```
# RapidAPI Instagram-скрейпер (основной путь загрузки)
# Выбери на RapidAPI IG-эндпоинт (желательно тот, что возвращает и caption) и подставь его хост.
RAPIDAPI_KEY=
RAPIDAPI_HOST=
```

- [ ] **Step 2: Проверить содержимое (acceptance)**

Run: `grep -E "RAPIDAPI_KEY|RAPIDAPI_HOST" skills/instagram-downloader/.env.template`
Expected: обе переменные присутствуют, обе пустые (без значений после `=`), есть комментарий-подсказка про эндпоинт с `caption`.

- [ ] **Step 3: Commit**

```bash
git add skills/instagram-downloader/.env.template
git commit -m "Add .env.template для instagram-downloader (RAPIDAPI_KEY, RAPIDAPI_HOST)"
```

---

## Task 2: `SKILL.md` (ядро скилла)

**Files:**
- Create: `skills/instagram-downloader/SKILL.md`

**Interfaces:**
- Consumes: имена `RAPIDAPI_KEY`, `RAPIDAPI_HOST` из Task 1.
- Produces: триггер-`description` (используется роутером скиллов); контракт хэндоффа — рилс/видео → `reels-script`, пост/карусель → `carousel-script`.

- [ ] **Step 1: Записать SKILL.md**

Записать файл `skills/instagram-downloader/SKILL.md` целиком:

````markdown
---
name: instagram-downloader
description: >-
  По ссылке на Instagram-пост/рилс/карусель вытаскивает медиа и подпись (RapidAPI,
  с фоллбэком на yt-dlp) и ОБЯЗАТЕЛЬНО передаёт их на переупаковку в reels-script
  или carousel-script под нишу пользователя. Используй этот скилл всегда, когда
  пользователь кидает ссылку на Instagram (instagram.com/p/…, /reel/…, /reels/…) и
  хочет «скачать рилс», «вытащить это видео/карусель», «забрать референс»,
  «переупаковать этот пост под свою нишу». Это инструмент извлечения референса для
  создания СВОЕГО контента, а НЕ качалка для дословного репоста — переупаковка
  обязательна. НЕ для аналитики профиля/метрик (instagram-analytics) и не для
  доставки в Telegram.
---

# Instagram-downloader — извлечение референса под переупаковку

Ты — **инструмент извлечения референса**. По ссылке на Instagram-пост/рилс/карусель ты вытаскиваешь **медиа + подпись** и передаёшь их на **обязательную переупаковку** в `reels-script` (видео) или `carousel-script` (слайды/пост). Конечный артефакт — **переупакованный под нишу пользователя оригинал**, а не скачанный чужой файл.

## Главное правило (вшито в суть)

Это **инструмент извлечения референса для создания СВОЕГО контента**, а НЕ качалка для репоста чужого.

- Загруженное **всегда** трактуется как **референс для переупаковки**, не как готовый контент к публикации.
- Ты **никогда** не предлагаешь и не выполняешь дословный репост («вот файл, выложи как есть»).
- Финал — **переупакованный оригинал** через `reels-script` / `carousel-script` (у них есть режим «переупаковка чужого вирусного под свою нишу», кросс-перенос).
- Соблюдение ToS Instagram — на стороне пользователя; качается публичный / свой контент как референс.

## Дисциплина ответа (что видит пользователь)

Пользователю нужен **результат (референс + переупаковка), а не отчёт о ходе твоих мыслей**. Парсинг ответа, выбор движка и скачивание делай молча.

- **Не печатай рассуждения** вроде «Извлекаю ссылку…», «Парсю data[]…». Никакого «думания вслух».
- Видимый ответ состоит только из: (1) структурированного результата (§ Выход); (2) хэндофф-блока с переупаковкой; (3) короткого блока «Допущения» (ниша, формат), если что-то вывел сам.
- **Не заканчивай призывом к диалогу** — заканчивай переупаковкой или блоком допущений.

## Флоу (6 шагов)

1. **Извлечь ссылку** из сообщения: `instagram.com/p/…` (пост), `instagram.com/reel/…` или `instagram.com/reels/…` (рилс). Тип определяется по сегменту URL; карусель распознаётся по ответу (несколько элементов в `data[]`).
2. **Запросить медиа** через RapidAPI (основной путь) или `yt-dlp` (фоллбэк, если RapidAPI не настроен). См. § Метод.
3. **Распарсить `data[]`**: для каждого элемента скачать `media` в рабочую папку. Несколько элементов = карусель (несколько файлов). Расширение — по `isVideo` (`.mp4` / `.jpg`).
4. **Извлечь подпись** — если RapidAPI-эндпоинт её отдаёт (поле `caption`). Если нет — пометить «подпись не пришла: добери вручную или через `instagram-analytics`».
5. **Выдать структурированный результат** (§ Выход).
6. **ОБЯЗАТЕЛЬНО — переупаковать.** Передать референс (подпись + тип + суть) в `reels-script` (видео) или `carousel-script` (пост/карусель) с указанием ниши пользователя для кросс-переноса. Это финальная цель, не опция.

## Метод

### Основной путь — RapidAPI IG-скрейпер

Требует `.env` (см. `.env.template`): `RAPIDAPI_KEY`, `RAPIDAPI_HOST`.

```bash
curl --silent --request GET \
  --url "https://$RAPIDAPI_HOST/scraper?url=$INSTAGRAM_URL" \
  --header "x-rapidapi-host: $RAPIDAPI_HOST" \
  --header "x-rapidapi-key: $RAPIDAPI_KEY"
```

Форма ответа:

```json
{"data":[{"media":"<CDN_URL>","isVideo":true},{"media":"<CDN_URL>","isVideo":false}]}
```

- `data[]` — массив; **несколько элементов = карусель**.
- `media` — прямая CDN-ссылка на файл.
- `isVideo` — тип (`true` → `.mp4`, `false` → `.jpg`).

Скачать каждый файл:

```bash
curl -L "<CDN_URL>" -o "ref-1.mp4"   # или ref-1.jpg, ref-2.jpg … для карусели
```

💡 Предпочитай RapidAPI-эндпоинт, который **возвращает и `caption`** — тогда подпись приходит в том же вызове (нужна для переупаковки). Конкретное имя эндпоинта/поля зависит от подписки пользователя; адаптируй парсинг под фактическую форму ответа.

### Фоллбэк — yt-dlp (без ключа, публичный контент)

Если RapidAPI не настроен (`.env` пуст) — используй `yt-dlp`:

```bash
yt-dlp "$INSTAGRAM_URL" -o "ref-%(autonumber)s.%(ext)s" --write-info-json
```

Подпись/описание — из info-json (поле `description`) или добери вручную. Парсинг адаптируй под фактическую форму.

## Выход (repackage-ready)

```
URL · тип (пост / рилс / карусель) · файлы (пути к скачанным медиа) · подпись · метрики (если есть)
```

Затем — **хэндофф-блок**:

> Референс извлечён. Переупаковываю через `reels-script` / `carousel-script` под нишу <ниша>.

(А не «вот медиа для репоста».)

## Обязательная переупаковка (хэндофф)

- **Рилс / видео** → `reels-script`: передай суть + подпись как тезис, укажи нишу пользователя → получишь свой сценарий.
- **Пост / карусель** → `carousel-script`: передай суть + подпись как тему, укажи нишу → получишь свою карусель.
- Если ниша не указана — спроси одним вопросом **или** возьми дефолт (AI) и зафиксируй в «Допущениях».

## Ограничения

- **.env:** `RAPIDAPI_KEY`, `RAPIDAPI_HOST` (шаблон — `.env.template`). Без них работает только yt-dlp-фоллбэк для публичного контента.
- **Без отдельного скрипта** — загрузка инлайн через `curl` / `yt-dlp`.
- **Только переупаковка** — дословный репост запрещён дизайном.
- **Не входит:** доставка в Telegram (рантайм/Hermes), аналитика профиля/метрики (`instagram-analytics`), OCR слайдов / транскрипт рилса.
- **ToS** — ответственность пользователя; качается публичный / свой контент как референс.
````

- [ ] **Step 2: Проверить frontmatter и триггеры (acceptance)**

Run: `grep -nE "^name:|instagram.com|reels-script|carousel-script|instagram-analytics" skills/instagram-downloader/SKILL.md`
Expected: `name: instagram-downloader`; в `description` есть паттерны ссылок (`instagram.com/p/…`, `/reel/…`, `/reels/…`), оба приёмника хэндоффа (`reels-script`, `carousel-script`) и исключение `instagram-analytics`.

- [ ] **Step 3: Проверить вшитую переупаковку и анти-репост (acceptance)**

Run: `grep -niE "репост|референс|переупак|ОБЯЗАТЕЛЬНО" skills/instagram-downloader/SKILL.md`
Expected: явно сказано, что дословный репост не предлагается/не выполняется; загруженное трактуется как референс; шаг 6 флоу помечен «ОБЯЗАТЕЛЬНО». Прочитать § «Главное правило» и подтвердить формулировку «НЕ качалка для репоста».

- [ ] **Step 4: Проверить метод и фоллбэк (acceptance)**

Run: `grep -nE "x-rapidapi-key|x-rapidapi-host|data\[\]|isVideo|yt-dlp" skills/instagram-downloader/SKILL.md`
Expected: curl с обоими заголовками; описан парсинг `data[]` (`media` + `isVideo`); присутствует yt-dlp-фоллбэк. Переменные совпадают с Task 1 (`RAPIDAPI_KEY`, `RAPIDAPI_HOST`).

- [ ] **Step 5: Commit**

```bash
git add skills/instagram-downloader/SKILL.md
git commit -m "Add SKILL.md instagram-downloader (RapidAPI + yt-dlp, обязательный хэндофф)"
```

---

## Task 3: `README.md` (применение + настройка)

**Files:**
- Create: `skills/instagram-downloader/README.md`

**Interfaces:**
- Consumes: переменные `.env` из Task 1; контракт хэндоффа из Task 2 (`reels-script`/`carousel-script`).

- [ ] **Step 1: Записать README.md**

Записать файл `skills/instagram-downloader/README.md` целиком:

````markdown
# instagram-downloader — где применять

Скилл по ссылке на Instagram-пост/рилс/карусель вытаскивает медиа + подпись и **обязательно** передаёт их на переупаковку в `reels-script` или `carousel-script` под нишу пользователя. Это инструмент извлечения **референса для своего контента**, а не качалка для дословного репоста.

## Когда срабатывает

- Пользователь кидает ссылку `instagram.com/p/…`, `/reel/…`, `/reels/…` и хочет «вытащить», «скачать рилс», «забрать референс».
- «Переупакуй этот пост/рилс под мою нишу» со ссылкой на Instagram.

НЕ для аналитики профиля/метрик (это `instagram-analytics`), не для доставки в Telegram (рантайм), не для дословного репоста.

## Метод

1. **RapidAPI IG-скрейпер** (основной) — нужен ключ и хост в `.env`.
2. **yt-dlp** (фоллбэк) — без ключа, для публичного контента.

### Подключить RapidAPI

```
cp .env.template .env
# открой .env и заполни:
# RAPIDAPI_KEY=<твой ключ>
# RAPIDAPI_HOST=<хост выбранного IG-эндпоинта>
```

Предпочитай эндпоинт, который возвращает и `caption` — подпись нужна для переупаковки.

## Хэндофф (обязательно)

- **рилс / видео** → `reels-script` (суть + подпись как тезис).
- **пост / карусель** → `carousel-script` (суть + подпись как тема).

С указанием ниши пользователя для кросс-переноса.

## Пример вызова

```
вот рилс https://instagram.com/reel/XXXX — забери и переупакуй под мою нишу (маркетинг)
```

В ответ — структурированный результат (файлы + подпись) и переупакованный сценарий/карусель.
````

- [ ] **Step 2: Проверить содержимое (acceptance)**

Run: `grep -nE "cp .env.template|RAPIDAPI_KEY|reels-script|carousel-script|референс" skills/instagram-downloader/README.md`
Expected: есть инструкция `cp .env.template .env` с обеими переменными, оба приёмника хэндоффа, явная формулировка «референс, а не репост».

- [ ] **Step 3: Commit**

```bash
git add skills/instagram-downloader/README.md
git commit -m "Add README применения instagram-downloader (.env + хэндофф)"
```

---

## Task 4: `evals/evals.json` (кейсы триггеринга и поведения)

**Files:**
- Create: `skills/instagram-downloader/evals/evals.json`

**Interfaces:**
- Consumes: поведенческие требования из Task 2 (флоу, метод, обязательный хэндофф, анти-репост).

- [ ] **Step 1: Записать evals.json**

Записать файл `skills/instagram-downloader/evals/evals.json` целиком:

```json
{
  "skill_name": "instagram-downloader",
  "evals": [
    {
      "id": 1,
      "prompt": "вот рилс https://instagram.com/reel/ABC123 — забери и переупакуй под мою нишу (маркетинг)",
      "expected_output": "Извлечена ссылка (рилс), вызов RapidAPI, скачан media, repackage-ready результат + ОБЯЗАТЕЛЬНЫЙ хэндофф в reels-script под нишу маркетинг",
      "files": []
    },
    {
      "id": 2,
      "prompt": "скачай эту карусель https://instagram.com/p/XYZ789 хочу такую же про финансы",
      "expected_output": "Тип = карусель (несколько файлов в data[]), repackage-ready результат, хэндофф в carousel-script под нишу финансы",
      "files": []
    },
    {
      "id": 3,
      "prompt": "просто скачай мне это видео и дай файл https://instagram.com/reel/QWE — выложу как есть",
      "expected_output": "Скилл НЕ выдаёт «вот файл для репоста»; трактует загруженное как референс и ведёт к обязательной переупаковке",
      "files": []
    },
    {
      "id": 4,
      "prompt": "у меня нет RapidAPI-ключа, вытащи публичный рилс https://instagram.com/reel/RST",
      "expected_output": "Используется yt-dlp-фоллбэк (без ключа), затем repackage-ready результат + хэндофф",
      "files": []
    }
  ],
  "assertions": [
    "Ссылка извлечена и тип определён: /reel/ или /reels/ → рилс; /p/ → пост; карусель — по нескольким элементам data[]",
    "Основной путь — RapidAPI (curl с x-rapidapi-host/x-rapidapi-key), парсинг data[] (media + isVideo)",
    "Карусель = несколько файлов скачано (по числу элементов data[])",
    "Подпись извлекается, если эндпоинт её отдаёт; иначе явно помечено добрать вручную",
    "Выход repackage-ready: URL · тип · файлы · подпись · метрики (если есть)",
    "ОБЯЗАТЕЛЬНЫЙ хэндофф: рилс → reels-script, пост/карусель → carousel-script, с нишей пользователя",
    "Дословный репост не предлагается и не выполняется (кейс 3): загруженное = референс",
    "Без RapidAPI-ключа используется yt-dlp-фоллбэк для публичного контента (кейс 4)",
    "Дисциплина ответа: без «думания вслух», без финального CTA к диалогу"
  ]
}
```

- [ ] **Step 2: Проверить валидность JSON (acceptance)**

Run: `python -c "import json,sys; json.load(open('skills/instagram-downloader/evals/evals.json', encoding='utf-8')); print('ok')"`
Expected: вывод `ok` (валидный JSON, 4 eval-кейса, блок `assertions` покрывает: тип/парсинг, карусель, подпись, хэндофф, анти-репост, фоллбэк, дисциплину).

- [ ] **Step 3: Commit**

```bash
git add skills/instagram-downloader/evals/evals.json
git commit -m "Add eval-кейсы для instagram-downloader"
```

---

## Task 5: Каталог + глобальное подключение + память

**Files:**
- Modify: `skills/README.md` (таблица каталога)
- Modify: `C:\Users\LENOVO\.claude\projects\d--Development-aifuture-hub\memory\MEMORY.md`
- Modify: `C:\Users\LENOVO\.claude\projects\d--Development-aifuture-hub\memory\aifuture-hub-project.md`
- Run: `skills/install-skills.ps1`

**Interfaces:**
- Consumes: готовая папка `skills/instagram-downloader/` (Tasks 1–4).

- [ ] **Step 1: Добавить скилл в каталог-витрину**

В `skills/README.md`, в таблицу «Каталог», после строки `ai-research` добавить:

```markdown
| [instagram-downloader/](instagram-downloader/) | По ссылке на Instagram вытаскивает медиа + подпись (RapidAPI / yt-dlp) и обязательно передаёт референс на переупаковку в reels-script / carousel-script |
```

- [ ] **Step 2: Проверить каталог (acceptance)**

Run: `grep -n "instagram-downloader" skills/README.md`
Expected: строка таблицы со ссылкой `[instagram-downloader/](instagram-downloader/)` присутствует.

- [ ] **Step 3: Подключить скилл глобально**

Run: `powershell -ExecutionPolicy Bypass -File skills/install-skills.ps1`
Expected: junction для `instagram-downloader` создан в `~/.claude/skills/` (или сообщение, что уже существует). Существующие ссылки не тронуты.

- [ ] **Step 4: Проверить junction (acceptance)**

Run: `ls "$HOME/.claude/skills/" | grep instagram-downloader`
Expected: `instagram-downloader` присутствует в списке.

- [ ] **Step 5: Обновить память**

В `MEMORY.md` (memory-папка): убрать из «ПРОДОЛЖАЕМ»-блока задачу про сборку instagram-downloader (она выполнена); в строке проекта обновить число готовых скиллов до 5 и перечислить `instagram-downloader`. В `aifuture-hub-project.md`: отметить `instagram-downloader` как готовый (в main, подключён глобально), обновить «текущее место» и очередь следующих скиллов (напр. `instagram-analytics`).

Конкретно — заменить «ПРОДОЛЖАЕМ»-блок в `MEMORY.md` на актуальный (следующий скилл из очереди или «очередь пуста — спросить пользователя»), и в строке-указателе проекта заменить «Готовы 4 скилла: meta-prompt, reels-script, carousel-script, ai-research» на «Готовы 5 скиллов: …, instagram-downloader».

- [ ] **Step 6: Финальный commit (каталог)**

```bash
git add skills/README.md
git commit -m "Add instagram-downloader в каталог скиллов"
```

(Файлы памяти лежат вне репозитория — в git не коммитятся, обновляются на месте.)

---

## Self-Review

**1. Spec coverage:**
- §1 Цель → Task 2 (роль + флоу + обязательный хэндофф).
- §2 Границы/scope → Task 2 § Ограничения + description (исключения instagram-analytics/Telegram).
- §3 Метод (RapidAPI + caption-рекомендация + yt-dlp фоллбэк) → Task 2 § Метод.
- §4 Флоу (6 шагов) → Task 2 § Флоу.
- §5 Выход (repackage-ready + хэндофф-блок) → Task 2 § Выход.
- §6 Обязательная переупаковка/этика → Task 2 § Главное правило + § Обязательная переупаковка.
- §7 Ограничения (.env, без скрипта, ToS, дисциплина) → Task 1 (.env.template) + Task 2 § Ограничения + § Дисциплина.
- §8 Файлы → Tasks 1–3 (+ evals по паттерну хаба, Task 4).
- §9 Non-goals → Task 2 § Ограничения «Не входит» + отсутствие meta-prompt/OCR.
- Правило CLAUDE.md (каталог + глобальная установка) → Task 5.

**2. Placeholder scan:** Полные тексты файлов даны целиком в Tasks 1–4; в SKILL.md `<CDN_URL>`/`<ниша>`/`<хост>` — это намеренные плейсхолдеры внутри инструкции скилла (примеры для рантайма), не пропуски плана.

**3. Type consistency:** `RAPIDAPI_KEY`/`RAPIDAPI_HOST` совпадают в Task 1, 2, 3. Приёмники хэндоффа `reels-script`/`carousel-script` совпадают в Task 2, 3, 4. Поля ответа `data[]`/`media`/`isVideo`/`caption` совпадают между § Метод и § Флоу.
