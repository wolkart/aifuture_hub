# Carousel-Script Skill — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Собрать скилл `skills/carousel-script/`, который превращает идею в карусель для Instagram/LinkedIn + render-agnostic per-slide спек, по утверждённому спеку.

**Architecture:** Скилл = `SKILL.md` (оркестратор-«штаб») + `references/` (хребет под свайп, IG-бриф, LinkedIn-бриф, схема per-slide спека). Платформа = режим; «обе» → субагент на каждый платформенный бриф. Ядро инструкции — через `meta-prompt`, упаковка/тесты — через `skill-creator`.

**Tech Stack:** Markdown, скиллы `meta-prompt` и `skill-creator`, субагенты для прогонов.

**Verification model:** Артефакт — текст инструкции, тестового фреймворка нет. «Провал теста» = прогон eval-промпта, где вывод не содержит обязательных элементов из чек-листа (Task 7). Проверки — субагентом-грейдером по выводам.

**Спек:** [docs/superpowers/specs/2026-06-18-carousel-script-skill-design.md](../specs/2026-06-18-carousel-script-skill-design.md)

## Global Constraints

- Формат карточки: вытянутый/портретный, дефолт **4:5 (1080×1350)**, параметр.
- Обложка = короткий **заголовок** (часто 2–4 слова), правило **«помещается крупно на карточке»**, НЕ счётчик слов.
- Per-slide спек: `№ · роль · заголовок · текст · подача · лейаут · визуал-направление`.
- Подача (text-treatment): `мега-текст · заголовок+треть · плотный-текст`. Лейаут: `обложка · большая-цифра · цитата · чеклист · текст+визуал · сравнение`.
- Объём: **IG 6–10** слайдов, **LinkedIn 8–12**.
- Рендер **opt-in**: спек выдаётся всегда; авто-рендер (Figma→image-gen) только по явному запросу; **ручной режим — приоритетный override** (даже если Figma подключена).
- Метастрока на карусель: `ниша · платформа · угол · тип хука`. Ниша=ИИ по умолчанию.
- Дисциплина ответа: рассуждения молча; без финального CTA к диалогу.
- Стоп-лист клише; конкретика вместо абстракций; тон-регулятор.

---

## File Structure

```
skills/carousel-script/
├── SKILL.md
├── README.md
├── .env.template                 # переменные под Figma/image-MCP (для рендера)
└── references/
    ├── carousel-backbone.md      # хребет под свайп-механику
    ├── instagram.md              # IG-бриф (подачи текста, тон, объём)
    ├── linkedin.md               # LinkedIn-бриф (плотнее, экспертно)
    └── slide-spec.md             # схема per-slide спека + словари лейаутов/подач
docs/superpowers/specs|plans/2026-06-18-carousel-script-skill*   # есть/этот
skills/carousel-script-workspace/   # эвалы (gitignored через *-workspace/)
```

---

## Task 1: Скаффолд + `slide-spec.md` (контракт)

**Files:**
- Create: `skills/carousel-script/references/slide-spec.md`

**Interfaces:**
- Produces: словарь полей per-slide спека и значений `подача`/`лейаут`, на который ссылаются `SKILL.md`, `instagram.md`, `linkedin.md`.

- [ ] **Step 1: Написать `references/slide-spec.md`** со схемой и словарями:
  - Поля слайда: `№`, `роль` (обложка/ценность/CTA), `заголовок`, `текст`, `подача`, `лейаут`, `визуал-направление`.
  - Словарь **подача**: `мега-текст` (на всю карточку огромными буквами ≈3 слова + бренд-значок), `заголовок+треть` (заголовок + текст ~1/3 карточки), `плотный-текст` (компактно, слов больше — зависит от темы).
  - Словарь **лейаут**: `обложка`, `большая-цифра`, `цитата`, `чеклист`, `текст+визуал`, `сравнение`.
  - Правило: текст слайда **помещается на вытянутой карточке (4:5)** при выбранной подаче.
  - Пример заполненного спека на 2–3 слайда.
  - Пометка: `визуал-направление` = одновременно промпт для image-gen; `лейаут` — стабильный словарь для маппинга на Figma-компоненты.

- [ ] **Step 2: Проверка** — прочитать файл: все поля и оба словаря на месте, есть пример, правило «fits-card» сформулировано.

- [ ] **Step 3: Commit**

```bash
git add skills/carousel-script/references/slide-spec.md
git commit -m "Add схему per-slide спека carousel-script"
```

---

## Task 2: Ядро инструкции через meta-prompt

**Files:**
- Create: `skills/carousel-script-workspace/core-draft.md` (gitignored)

- [ ] **Step 1: Прогнать скилл `meta-prompt`** с идеей: «инструкция для ИИ — карусель-продюсера: из тезиса делает карусель (обложка-заголовок → слайды-ценность → CTA) для IG/LinkedIn, с гейтом ширины 5М+, атомизацией, и выдаёт per-slide спек (поля из slide-spec.md)». Передать ключевые пункты спека (§3–§10) и Global Constraints.

- [ ] **Step 2: Сохранить вывод** в `skills/carousel-script-workspace/core-draft.md`.

- [ ] **Step 3: Адаптировать** — отметить, что идёт в `SKILL.md` (флоу, дисциплина, рендер-лесенка, порядок источника хука), а что в `references/` (формулы хуков-заголовков, платформенные подачи). Плейсхолдеры/`<scratchpad>` переписать на язык скилла.

- [ ] **Step 4:** Коммитить нечего (workspace gitignored); зафиксировать прогресс в TODO.

---

## Task 3: `references/carousel-backbone.md` (хребет под свайп)

**Files:**
- Create: `skills/carousel-script/references/carousel-backbone.md`

**Interfaces:**
- Produces: формулы заголовков-обложек и приёмы свайп-удержания, на которые ссылается `SKILL.md`.

- [ ] **Step 1: Написать файл** с блоками (концепции как у reels, но адаптированы под карусель):
  - **Формулы обложки-заголовка** — провокация / неожиданность / интрига / отрицание / обещание, но как **короткий заголовок** (2–4 слова, пример каждой). Требование: останавливает свайп, читается крупно, бьёт в эмоцию; правило «fits-card», НЕ счётчик слов.
  - **Свайп-удержание** — open loop через слайды («дальше — главное»), один слайд = одна мысль, нумерация/прогресс, обещание на обложке закрывается на последних слайдах.
  - **Атомизация (Хормози)** — совет до наблюдаемого действия = один слайд; абстрактное → наблюдаемое.
  - **Расширение темы / уход от жаргона** — узкую тему → к боли/выгоде/любопытству.
  - **CTA-паттерны** — мягкий CTA (сохрани/коммент/подписка) vs лидмагнит с кодовым словом; адаптация под платформу.

- [ ] **Step 2: Проверка** — все блоки на месте, примеры конкретные, формулы обложки даны как короткие заголовки (не предложения).

- [ ] **Step 3: Commit**

```bash
git add skills/carousel-script/references/carousel-backbone.md
git commit -m "Add хребет carousel-backbone (заголовки-обложки, свайп-удержание)"
```

---

## Task 4: Платформенные брифы `instagram.md` + `linkedin.md`

**Files:**
- Create: `skills/carousel-script/references/instagram.md`
- Create: `skills/carousel-script/references/linkedin.md`

**Interfaces:**
- Consumes: словари из `slide-spec.md`.
- Produces: платформенные роли-субагенты, на которые ссылается `SKILL.md` («обе» → субагент на каждый).

- [ ] **Step 1: Написать `instagram.md`** — IG-бриф:
  - Аудитория широкая, визуально-цепляющая подача, эмоция.
  - **Стандарты подачи текста** (ключевое): когда `мега-текст` (бренд-значок + огромные 3 слова), когда `заголовок+треть`, когда `плотный-текст` — зависит от темы.
  - Объём **6–10** слайдов. Тон — энергичный, на «ты».
  - CTA: кодовое слово / «сохрани».

- [ ] **Step 2: Написать `linkedin.md`** — LinkedIn-бриф:
  - Аудитория B2B/экспертная; подача плотнее, thought-leadership, доказательность.
  - Объём **8–12** слайдов; больше текста на слайд допустимо (`плотный-текст` чаще).
  - Тон — профессиональный, без инфоцыганщины.
  - CTA: коммент/отклик/connect.

- [ ] **Step 3: Проверка** — оба файла используют словари из slide-spec.md; объёмы и тон различаются по спеку.

- [ ] **Step 4: Commit**

```bash
git add skills/carousel-script/references/instagram.md skills/carousel-script/references/linkedin.md
git commit -m "Add платформенные брифы instagram/linkedin для carousel-script"
```

---

## Task 5: Собрать `SKILL.md`

**Files:**
- Create: `skills/carousel-script/SKILL.md`

**Interfaces:**
- Consumes: `slide-spec.md`, `carousel-backbone.md`, `instagram.md`, `linkedin.md`.

- [ ] **Step 1: Frontmatter с pushy-описанием:**

```yaml
---
name: carousel-script
description: >-
  Превращает идею или тезис в готовую карусель (пост-карусель) для Instagram и/или
  LinkedIn: цепляющая обложка-заголовок, одна мысль, раскладка по слайдам с атомизацией,
  плюс per-slide спек для рендера. Используй этот скилл всегда, когда пользователь хочет
  карусель / пост-карусель / слайды / контент-план каруселей для Instagram или LinkedIn,
  или кидает идею со словами «сделай карусель», «карусель для инсты/линкедина»,
  «пост в слайдах», «придумай карусель». НЕ для коротких видео (это reels-script),
  длинных видео или обычных текстовых постов. Выдаёт текст карусели + per-slide спек.
---
```

- [ ] **Step 2: Тело SKILL.md** (спек §3–§10):
  - **Роль** карусель-продюсера + **дисциплина ответа** (рассуждения молча; без финального CTA к диалогу).
  - **Штаб**: платформа=режим; IG/LinkedIn/обе; «обе» → спавн субагента на каждый платформенный бриф; ссылки на `references/instagram.md`, `references/linkedin.md`.
  - **Флоу 6 шагов**: гейт ширины → одна мысль → платформа+угол → обложка → раскладка по слайдам (атомизация) → тесты.
  - **Структура слайдов**: обложка-заголовок (короткий, fits-card) → ценность (1 мысль/слайд) → CTA. Объёмы IG 6–10 / LinkedIn 8–12.
  - **Порядок источника обложки-хука**: (1) пользователь → (2) внешняя база (пока не подключена, отметить и идти дальше) → (3) `references/carousel-backbone.md`.
  - **Per-slide спек** (поля из `references/slide-spec.md`) + **метастрока** `ниша · платформа · угол · тип хука`.
  - **Рендер-лесенка (opt-in)**: спек всегда; авто-рендер (Figma-MCP → image-gen) только по явному запросу; **ручной режим — приоритетный override** (даже если Figma подключена); дефолт — руками.
  - **Тесты перед выдачей** (§8 спека).
  - **Ограничения**: формат 4:5, стоп-лист клише, конкретика, тон-регулятор, ниша=ИИ + кросс-перенос.
  - **Ссылки на references**.

- [ ] **Step 3: Проверка** — пройтись по спеку §3–§10 + Global Constraints: каждый пункт отражён в SKILL.md или reference. Файл < 300 строк.

- [ ] **Step 4: Commit**

```bash
git add skills/carousel-script/SKILL.md
git commit -m "Add SKILL.md скилла carousel-script"
```

---

## Task 6: `README.md` + `.env.template`

**Files:**
- Create: `skills/carousel-script/README.md`
- Create: `skills/carousel-script/.env.template`

- [ ] **Step 1: Написать `.env.template`** — переменные под рендер (с комментариями), напр.:

```
# Figma MCP (опционально, для авто-рендера слайдов)
FIGMA_API_TOKEN=
FIGMA_FILE_KEY=
# Image-gen (опционально, фоллбэк-рендер)
IMAGE_API_KEY=
```

- [ ] **Step 2: Написать `README.md`** — что делает, две платформы (IG/LinkedIn), per-slide спек, рендер-лесенка (Figma → image-gen → вручную, opt-in, ручной override), как подключить рендер (скопировать `.env.template` → `.env`, заполнить), пример вызова. Сжато, по образцу `skills/reels-script/README.md`.

- [ ] **Step 3: Commit**

```bash
git add skills/carousel-script/README.md skills/carousel-script/.env.template
git commit -m "Add README применения и .env.template для carousel-script"
```

---

## Task 7: Eval-кейсы

**Files:**
- Create: `skills/carousel-script/evals/evals.json`

- [ ] **Step 1: Записать тест-промпты** (`evals/evals.json`):
  1. **Расплывчатая IG:** «сделай карусель для инстаграма про то как нейросети помогают вести соцсети»
  2. **LinkedIn-эксперт:** «карусель для linkedin: почему большинство компаний внедряют ИИ неправильно»
  3. **Обе платформы:** «тема: 5 ИИ-инструментов которые экономят час в день. нужна карусель и под инстаграм и под линкедин»
  4. **Ручной override:** «карусель про ИИ-агентов, фигма у меня подключена, но я сам потом нарисую»

- [ ] **Step 2: Зафиксировать чек-лист (assertions)** для грейдинга:
  - Есть обложка-заголовок: короткая, по правилу fits-card (НЕ 10-словный хук).
  - Слайды-ценность: одна мысль на слайд, атомизировано.
  - Есть CTA-слайд.
  - Per-slide спек присутствует со всеми полями (роль/заголовок/текст/подача/лейаут/визуал-направление).
  - `подача` из словаря (мега-текст/заголовок+треть/плотный-текст); `лейаут` из словаря.
  - Метастрока `ниша · платформа · угол · тип хука`.
  - Объём в рамках: IG 6–10 / LinkedIn 8–12.
  - Кейс 3 («обе») → две версии (IG и LinkedIn).
  - Кейс 4 (ручной override) → спек выдан, авто-рендер НЕ инициирован, несмотря на «фигма подключена».
  - Нет клише из стоп-листа.

- [ ] **Step 3: Commit**

```bash
git add skills/carousel-script/evals/evals.json
git commit -m "Add eval-кейсы для carousel-script"
```

---

## Task 8: Прогнать эвалы и итерации (skill-creator)

**Files:**
- Workspace: `skills/carousel-script-workspace/iteration-1/` (gitignored)

- [ ] **Step 1: Прогнать 4 кейса со скиллом** — субагент на кейс: читает `skills/carousel-script/SKILL.md` + references, отрабатывает промпт, сохраняет вывод. Кейсы с уточнениями — автономно с дефолтами.

- [ ] **Step 2: Грейдинг по чек-листу** (Task 7 Step 2) — субагент-грейдер; результат по каждому кейсу: что прошло/провалилось.

- [ ] **Step 3: Показать выводы пользователю** (инлайн, как с reels) и собрать фидбек.

- [ ] **Step 4: Доработать** SKILL.md/references по проваленным проверкам и фидбеку; перепрогнать (iteration-2). Повторять, пока чек-лист зелёный и пользователь доволен.

- [ ] **Step 5: Commit** правок после каждой итерации:

```bash
git add skills/carousel-script/
git commit -m "Доработка carousel-script по итогам эвалов (iteration-N)"
```

---

## Task 9: Витрина, глобальная установка, публикация

**Files:**
- Modify: `skills/README.md`

- [ ] **Step 1: Добавить строку в каталог** `skills/README.md`:

```markdown
| [carousel-script/](carousel-script/) | Превращает идею в карусель для Instagram/LinkedIn: обложка-хук, одна мысль, слайды + per-slide спек под рендер |
```

- [ ] **Step 2: Подключить скилл глобально** (правило из CLAUDE.md):

```bash
powershell -ExecutionPolicy Bypass -File ./skills/install-skills.ps1
```
Expected: строка `+ подключён: carousel-script` (или `= уже подключён`).

- [ ] **Step 3: Commit и push**

```bash
git add skills/README.md
git commit -m "Add carousel-script в каталог скиллов"
git push origin main
```

(Слияние ветки реализации в `main` — через `superpowers:finishing-a-development-branch`, как с reels.)

---

## Task 10 (опционально): Оптимизация description

- [ ] **Step 1:** Сгенерировать ~20 trigger-eval запросов (should/should-not, включая ловушки: карусель vs reels vs обычный пост vs meta-prompt), согласовать с пользователем.
- [ ] **Step 2:** Прогнать классификаторами (Python `run_loop` недоступен — ручной прогон субагентами, как делали для reels), найти промахи.
- [ ] **Step 3:** При необходимости обновить `description`, показать before/after, commit + push.

---

## Self-Review (выполнено при написании плана)

- **Покрытие спека:** §2 границы → Task 1/5/6 (контракт, без рендер-кода); §3 штаб → Task 4/5; §4 флоу → Task 5; §5 структура слайдов → Task 3/5; §6 формат карточки → Task 1/5 (Global Constraints); §7 per-slide спек → Task 1 (+ Task 5 вывод); §8 тесты → Task 5/7; §9 рендер-лесенка → Task 5 (+ Task 6 .env); §10 формат вывода → Task 5; §11 файлы → File Structure; §12 переиспользование/сборка → Task 2/9; §13 non-goals → не реализуем. Пробелов нет.
- **Плейсхолдеры:** контент-файлы пишутся по чётким блокам спека; «тесты» = объективный чек-лист Task 7. Нет «TBD».
- **Консистентность имён:** `carousel-script`, `slide-spec.md`, `carousel-backbone.md`, `instagram.md`, `linkedin.md`; поля спека `№·роль·заголовок·текст·подача·лейаут·визуал-направление`; словари `подача`/`лейаут`; метастрока `ниша·платформа·угол·тип хука` — едины во всех тасках.
