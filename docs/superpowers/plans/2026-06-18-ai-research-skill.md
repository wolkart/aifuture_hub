# AI-Research Skill — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Собрать скилл `skills/ai-research/` — мини-штаб ресёрча AI-мира с тремя режимами вывода (ideas / digest / weekly), по утверждённому спеку.

**Architecture:** Скилл = `SKILL.md` (роутер по режимам + source-лесенка) + `references/` (список источников, форматы выхода). Ядро — через `meta-prompt`, упаковка/тесты — через `skill-creator`.

**Tech Stack:** Markdown; тулы ресёрча: Perplexity MCP (предпочтительно) / WebSearch / WebFetch; скиллы `meta-prompt`, `skill-creator`; субагенты.

**Verification model:** Артефакт — текст инструкции, тестового фреймворка нет. «Провал теста» = прогон eval-промпта, где вывод не содержит обязательных элементов из чек-листа (Task 6). Проверки — субагентом-грейдером.

**Спек:** [docs/superpowers/specs/2026-06-18-ai-research-skill-design.md](../specs/2026-06-18-ai-research-skill-design.md)

## Global Constraints

- 3 режима вывода: `ideas` (дефолт) / `digest` / `weekly`. Роутер определяет из запроса; уточняет только если неясно.
- Source-лесенка: **Perplexity MCP → WebSearch/WebFetch → evergreen** (гибрид: живой поиск + вечнозелёные паттерны).
- **Антигаллюцинации:** каждая фактическая новость/идея — со ссылкой на источник; не выдумывать новости/цифры/даты; неуверенность помечать; `digest`/`weekly` — только реальные найденные новости.
- Форматы выхода: `ideas` → `тезис · угол · почему зайдёт · формат(рилс/карусель/обе) · источник`; `digest` → топ-N (заголовок · 1–2 строки · ссылка · почему важно); `weekly` → 7 дней Пн–Вс (день · новость · ссылка), структура под carousel-script.
- Ниша AI по умолчанию; тема — параметр; кросс-перенос.
- Дисциплина ответа: рассуждения молча, без финального CTA к диалогу.
- Ядро — через `meta-prompt`. После сборки — глобальная установка (`skills/install-skills.*`) + витрина `skills/README.md`.

---

## File Structure

```
skills/ai-research/
├── SKILL.md            # роль, режимы-роутер, source-лесенка, антигаллюцинации, дисциплина, ссылки
├── README.md           # где применять + .env.template-пункт
├── .env.template       # PERPLEXITY_API_KEY
└── references/
    ├── sources.md      # авторитетные AI-источники по тирам
    └── output-modes.md # форматы выхода трёх режимов
docs/superpowers/specs|plans/2026-06-18-ai-research-skill*   # есть/этот
skills/ai-research-workspace/   # эвалы + core-draft (gitignored через *-workspace/)
```

---

## Task 1: `references/sources.md` (список источников)

**Files:**
- Create: `skills/ai-research/references/sources.md`

**Interfaces:**
- Produces: курированный список источников, на который ссылаются `SKILL.md` и source-лесенка.

- [ ] **Step 1: Написать `references/sources.md`** — авторитетные AI-источники по тирам (из спека §6), с краткой пометкой, для чего каждый тир полезен:
  - **Tier-1 медиа:** TechCrunch (AI), The Verge (AI), Ars Technica, VentureBeat, MIT Technology Review, Wired.
  - **Блоги лабораторий/компаний:** OpenAI, Anthropic, Google DeepMind, Google AI, Meta AI, Microsoft, AWS ML Blog, Hugging Face, Mistral, NVIDIA.
  - **Агрегаторы/ресёрч:** Hacker News, arXiv (cs.AI/cs.CL), Papers with Code, Reddit (r/MachineLearning, r/LocalLLaMA).
  - **Рассылки:** Import AI, The Batch (Andrew Ng), Ben's Bites, TLDR AI, The Rundown AI, Last Week in AI.
  - **RU:** Habr (AI/ML), «Код» (thecode.media), vc.ru.
  - Пометка: список редактируемый; для живого поиска передавать домены приоритетно (WebSearch `allowed_domains` / Perplexity).

- [ ] **Step 2: Проверка** — все 5 тиров на месте с источниками; есть пометка про редактируемость и приоритет доменов.

- [ ] **Step 3: Commit**

```bash
git add skills/ai-research/references/sources.md
git commit -m "Add список авторитетных AI-источников для ai-research"
```

---

## Task 2: `references/output-modes.md` (форматы режимов)

**Files:**
- Create: `skills/ai-research/references/output-modes.md`

**Interfaces:**
- Produces: форматы выхода трёх режимов, на которые ссылается `SKILL.md`.

- [ ] **Step 1: Написать `references/output-modes.md`** — детальные форматы (из спека §7) + по 1 короткому примеру на режим:
  - **`ideas`** — ранжированный список; каждый кандидат: `тезис · угол · почему зайдёт (боль/тренд) · формат (рилс/карусель/обе) · источник (ссылка)`. Пример на 2 идеи.
  - **`digest`** — топ-N новостей: `заголовок · 1–2 строки сути · ссылка · почему важно`. Пример на 2 новости.
  - **`weekly`** — 7 строк (Пн–Вс): `день · главная новость дня · 1 строка · ссылка`. Явно: это хэндофф-структура для `carousel-script` (день = слайд). Пример на 2 дня.

- [ ] **Step 2: Проверка** — три режима описаны с полями и примерами; для `weekly` указан хэндофф в carousel-script.

- [ ] **Step 3: Commit**

```bash
git add skills/ai-research/references/output-modes.md
git commit -m "Add форматы выхода режимов ai-research (ideas/digest/weekly)"
```

---

## Task 3: Ядро через meta-prompt

**Files:**
- Create: `skills/ai-research-workspace/core-draft.md` (gitignored)

- [ ] **Step 1: Прогнать скилл `meta-prompt`** с идеей: «инструкция для ИИ — ресёрчера AI-мира с 3 режимами вывода (ideas/digest/weekly), source-лесенкой Perplexity MCP → WebSearch → evergreen, жёсткими антигаллюцинациями (ссылки на источники, не выдумывать новости)». Передать ключевые пункты спека (§3–§8) и Global Constraints.

- [ ] **Step 2: Сохранить вывод** в `skills/ai-research-workspace/core-draft.md`.

- [ ] **Step 3: Адаптировать** — отметить, что идёт в `SKILL.md` (роутер, лесенка, антигаллюцинации, дисциплина), а что в `references/`. Плейсхолдеры `{{}}`/`<scratchpad>` переписать на язык скилла.

- [ ] **Step 4:** Коммитить нечего (workspace gitignored); зафиксировать прогресс в TODO.

---

## Task 4: Собрать `SKILL.md`

**Files:**
- Create: `skills/ai-research/SKILL.md`

**Interfaces:**
- Consumes: `references/sources.md`, `references/output-modes.md`.

- [ ] **Step 1: Frontmatter с pushy-описанием:**

```yaml
---
name: ai-research
description: >-
  Ресёрчит AI-мир из авторитетных источников и выдаёт результат в одном из режимов:
  идеи для контента, новостной дайджест или недельная подборка главных новостей.
  Используй этот скилл всегда, когда пользователь хочет найти идеи для постов/рилсов/
  каруселей про ИИ, собрать дайджест AI-новостей, сделать подборку новостей за неделю,
  узнать «что happening в ИИ», «о чём снять», «собери новости для клуба». Источники:
  Perplexity MCP / веб-поиск, с опорой на авторитетные AI-медиа и блоги лабораторий.
  Выдаёт текст (идеи / дайджест / подборку) со ссылками на источники.
---
```

- [ ] **Step 2: Тело SKILL.md** (спек §3–§9):
  - **Роль** ресёрчера-мини-штаба: собирает и курирует AI-новости/тренды; результат — артефакт (идеи/дайджест/подборка), а не выполнение задачи.
  - **Дисциплина ответа** (как у reels/carousel) — рассуждения молча; без финального CTA к диалогу.
  - **Режимы-роутер:** `ideas` (дефолт) / `digest` / `weekly`; как определять из запроса; уточнять только если неясно. Форматы выхода — ссылка на `references/output-modes.md`.
  - **Source-лесенка:** (1) Perplexity MCP если подключён → (2) WebSearch/WebFetch → (3) evergreen-генерация. Гибрид: живой поиск + вечнозелёные паттерны. Источники — `references/sources.md` (приоритет доменов).
  - **Антигаллюцинации:** каждая фактическая новость/идея со ссылкой; не выдумывать новости/цифры/даты; неуверенность помечать; `digest`/`weekly` — только реальные найденные новости; опираться на текущую дату, за свежим идти в живой поиск.
  - **Хэндофф:** `weekly` выдаёт структуру, готовую для `carousel-script` (день = слайд); `ideas` — тезисы для `reels-script`/`carousel-script`.
  - **Ограничения:** ниша AI по умолчанию + кросс-перенос; тон-нейтральный/информативный.
  - **Ссылки на references**.

- [ ] **Step 3: Проверка** — пройтись по спеку §3–§9 + Global Constraints: каждый пункт отражён. Ссылки на references корректны. Файл < 300 строк.

- [ ] **Step 4: Commit**

```bash
git add skills/ai-research/SKILL.md
git commit -m "Add SKILL.md скилла ai-research"
```

---

## Task 5: `README.md` + `.env.template`

**Files:**
- Create: `skills/ai-research/README.md`
- Create: `skills/ai-research/.env.template`

- [ ] **Step 1: Написать `.env.template`:**

```
# Perplexity MCP (опционально, предпочтительный движок ресёрча)
PERPLEXITY_API_KEY=
```

- [ ] **Step 2: Написать `README.md`** — что делает, 3 режима (ideas/digest/weekly) одной строкой со ссылкой на `references/output-modes.md`, source-лесенка (Perplexity MCP → WebSearch → evergreen) и как подключить Perplexity (`.env.template` → `.env`), ссылка на `references/sources.md`, хэндофф weekly → carousel, пример вызова на каждый режим. Сжато, по образцу `skills/reels-script/README.md`.

- [ ] **Step 3: Commit**

```bash
git add skills/ai-research/README.md skills/ai-research/.env.template
git commit -m "Add README применения и .env.template для ai-research"
```

---

## Task 6: Eval-кейсы

**Files:**
- Create: `skills/ai-research/evals/evals.json`

- [ ] **Step 1: Записать тест-промпты** (`evals/evals.json`):
  1. **ideas:** «найди мне идеи для рилсов про ИИ-агентов»
  2. **digest:** «собери дайджест лучших AI-новостей за последние дни для моего клуба»
  3. **weekly:** «сделай подборку главной новости каждого дня за неделю про ИИ — заверну в карусель»
  4. **evergreen-фоллбэк:** «без интернета накидай вечнозелёные идеи для каруселей про промптинг»

- [ ] **Step 2: Зафиксировать чек-лист (assertions):**
  - Режим определён верно под запрос (1→ideas, 2→digest, 3→weekly, 4→evergreen-ветка ideas).
  - `ideas`: список кандидатов с полями (тезис·угол·почему·формат·источник).
  - `digest`: топ-N с сутью + ссылка + «почему важно».
  - `weekly`: 7 дней (Пн–Вс), главная новость дня + ссылка; структура пригодна для carousel.
  - Source-лесенка: при живом поиске — ссылки на источники; кейс 4 (evergreen) — явно помечено, что без live-источников, новости не выдуманы.
  - Антигаллюцинации: фактические новости со ссылками; нет выдуманных цифр/дат; неуверенность помечена.
  - Дисциплина ответа: без «думания вслух».
  - Ниша AI по умолчанию.

- [ ] **Step 3: Commit**

```bash
git add skills/ai-research/evals/evals.json
git commit -m "Add eval-кейсы для ai-research"
```

---

## Task 7: Прогнать эвалы и итерации (skill-creator)

**Files:**
- Workspace: `skills/ai-research-workspace/iteration-1/` (gitignored)

- [ ] **Step 1: Прогнать 4 кейса со скиллом** — субагент на кейс: читает `skills/ai-research/SKILL.md` + references, отрабатывает промпт (может реально дёрнуть WebSearch), сохраняет вывод.

- [ ] **Step 2: Грейдинг по чек-листу** (Task 6 Step 2) — субагент-грейдер.

- [ ] **Step 3: Показать выводы пользователю** (инлайн) и собрать фидбек.

- [ ] **Step 4: Доработать** SKILL.md/references по проваленным проверкам/фидбеку; перепрогнать. Повторять до зелёного чек-листа и согласия пользователя.

- [ ] **Step 5: Commit** правок после каждой итерации:

```bash
git add skills/ai-research/
git commit -m "Доработка ai-research по итогам эвалов (iteration-N)"
```

---

## Task 8: Витрина, глобальная установка, публикация

**Files:**
- Modify: `skills/README.md`

- [ ] **Step 1: Добавить строку в каталог** `skills/README.md`:

```markdown
| [ai-research/](ai-research/) | Ресёрч AI-мира из авторитетных источников: идеи для контента, новостной дайджест или подборка недели |
```

- [ ] **Step 2: Подключить скилл глобально:**

```bash
powershell -ExecutionPolicy Bypass -File ./skills/install-skills.ps1
```
Expected: строка `+ подключён: ai-research`.

- [ ] **Step 3: Commit, push, merge** (ветка реализации → `main` через `superpowers:finishing-a-development-branch`):

```bash
git add skills/README.md
git commit -m "Add ai-research в каталог скиллов"
```

---

## Task 9 (опционально): Оптимизация description

- [ ] **Step 1:** Сгенерировать ~20 trigger-eval запросов (should/should-not; ловушки: ai-research vs reels/carousel vs meta-prompt), согласовать.
- [ ] **Step 2:** Прогнать классификаторами (ручной прогон субагентами, как для reels/carousel).
- [ ] **Step 3:** При необходимости обновить `description`, показать before/after, commit.

---

## Self-Review (выполнено при написании плана)

- **Покрытие спека:** §2 границы → Task 4/5/8 (без постинга/MCP-кода); §3 мини-штаб → Task 4; §4 режимы → Task 2/4; §5 source-лесенка → Task 4; §6 источники → Task 1; §7 форматы → Task 2 (+ Task 4 вывод); §8 антигаллюцинации → Task 4/6; §9 переиспользование/сборка → Task 3/8. Пробелов нет.
- **Плейсхолдеры:** контент-файлы пишутся по чётким блокам спека; «тесты» = объективный чек-лист Task 6. Нет «TBD».
- **Консистентность имён:** `ai-research`, `sources.md`, `output-modes.md`; режимы `ideas/digest/weekly`; поля `ideas` (тезис·угол·почему·формат·источник); source-лесенка Perplexity→WebSearch→evergreen — едины во всех тасках.
