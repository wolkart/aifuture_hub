# Post-HQ (Фаза 1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Собрать Фазу 1 штаба `skills/post-hq/` — рабочий многоцелевой штаб постов под Telegram (контент + продажа), на общем `brand-voice`, с дистиллированными фреймворками Хормози/Огилви и слоем review.

**Architecture:** Оркестратор (`SKILL.md`) ведёт идею через голос → цель → площадку → ревью. Контент в `references/`: `platforms/` (как), `purposes/` (зачем), `frameworks/` (дистиллированное знание), `review.md` (роль-ревьюер). Модули — роли-инструкции (стиль «ты — агент…»), исполняются одним Клодом по очереди. Голос НЕ дублируется — читается из `skills/brand-voice/`.

**Tech Stack:** Markdown; Claude Code skills (`SKILL.md` frontmatter `name`/`description`); `meta-prompt`, `skill-creator`, `carousel-script`, `brand-voice` (скиллы хаба); `install-skills.ps1`.

## Global Constraints

- Язык всех артефактов — русский.
- Имя скилла — `post-hq` (штаб постов). В README по-русски — «штаб постов».
- Модули = роли-инструкции в стиле «ты — агент…» (как в ogilvy-content-machine Минина).
- **Голос НЕ дублируется** — оркестратор и модули ссылаются на `skills/brand-voice/references/brand-voice.md` + `writing-principles.md` как на единый источник.
- **Фреймворки — дистилляция, не дамп.** Из 60КБ-наставников извлекается компактный (~1 экран) чек-лист приёмов «к применению». Персона-наставник/диалог-гайд/кейсы/отчёт верификации — отбрасываются.
- **Условная загрузка:** `selling.md` грузит `hormozi.md` + `ogilvy.md`; `informational.md` — только `ogilvy.md` (облегчённо). Хормози к обычным постам не подмешивается.
- **Голос — последним фильтром:** стек brand-voice → writing-principles → фреймворк цели; голос переозвучивает и срезает инфоцыганщину (`brand-voice §9`).
- **Копирайт:** полные наставники (`docs/superpowers/working/*.md`) — ТОЛЬКО локально (gitignore). В скилл едет лишь наш дистиллят (свои директивы, без дословного текста книг).
- **Telegram-вёрстка** и «длинное тире по минимуму» — наследуются из `brand-voice §8`, не переписываются.
- Скилл НЕ постит/не доставляет (рантайм); карточки делегирует `carousel-script`.
- Ветка `post-hq`. Спек: `docs/superpowers/specs/2026-06-23-post-hq-design.md`.
- Фаза 2 (threads-x, linkedin, instagram-caption) — НЕ в этом плане.

---

## File Structure (Фаза 1)

- Create: `skills/post-hq/references/frameworks/hormozi.md` — дистиллят Хормози (приёмы продаж).
- Create: `skills/post-hq/references/frameworks/ogilvy.md` — дистиллят Огилви (большая идея, заголовки, body-copy).
- Create: `skills/post-hq/references/purposes/informational.md` — роль «экспертный пост».
- Create: `skills/post-hq/references/purposes/selling.md` — роль «продающий пост».
- Create: `skills/post-hq/references/platforms/telegram.md` — модуль площадки Telegram.
- Create: `skills/post-hq/references/review.md` — роль-ревьюер.
- Create: `skills/post-hq/SKILL.md` — оркестратор.
- Create: `skills/post-hq/README.md` — что делает / когда / что внутри / что не делает.
- Modify: `skills/README.md` — строка в каталог.
- Source (локально, не коммитим): `docs/superpowers/working/AI-Nastavnik-Hormozi-100M-Offers.md`, `docs/superpowers/working/Инструкция_AI-наставник_Огилви.md`.

---

## Task 1: `frameworks/hormozi.md` — дистиллят Хормози

**Files:**
- Create: `skills/post-hq/references/frameworks/hormozi.md`
- Read (source, локально): `docs/superpowers/working/AI-Nastavnik-Hormozi-100M-Offers.md`

**Interfaces:**
- Produces: компактный чек-лист приёмов, на который ссылается `purposes/selling.md` (Task 4).

- [ ] **Step 1: Критерии приёмки**

Принято, если: (1) ≤ ~1.5 экрана; (2) только приёмы «к применению» для написания продающего поста; (3) покрыты ключевые модели: Value Equation (мечта × вероятность ÷ время ÷ усилия), Grand Slam Offer (5 шагов), усилители оффера, гарантии, scarcity/urgency (этично), MAGIC-нейминг; (4) отброшены персона-наставник/кейсы/диалог-гайд/отчёт верификации; (5) свои формулировки-директивы, без дословного копирования книги; (6) верность источнику (без выдумок).

- [ ] **Step 2: Прочитать источник и выделить применимое**

Прочитай `docs/superpowers/working/AI-Nastavnik-Hormozi-100M-Offers.md`. Выпиши только то, что нужно при ПИСЬМЕ продающего поста (модели/чек-листы из Step 1). Игнорируй секции про диалог наставника, кейсы, верификацию.

- [ ] **Step 3: Написать `frameworks/hormozi.md`**

Формат: краткая шапка («Дистиллят: приёмы продаж по Хормози для письма постов. Применяется модулем `purposes/selling.md`.») → разделы по моделям, каждый = что это + как применить в посте (1–3 строки + мини-пример). Директивами, не пересказом. Без дословных цитат книги.

- [ ] **Step 4: Самопроверка против критериев**

Проверь объём, отсутствие «мусора наставника», верность, свои формулировки. Исправь инлайн.

- [ ] **Step 5: Commit**

```bash
git add skills/post-hq/references/frameworks/hormozi.md
git commit -m "post-hq: frameworks/hormozi.md — дистиллят приёмов продаж"
```
(в конце сообщения коммита строка: Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>)

---

## Task 2: `frameworks/ogilvy.md` — дистиллят Огилви

**Files:**
- Create: `skills/post-hq/references/frameworks/ogilvy.md`
- Read (source, локально): `docs/superpowers/working/Инструкция_AI-наставник_Огилви.md`

**Interfaces:**
- Produces: компактный чек-лист, на который ссылаются `purposes/selling.md` (Task 4) и `purposes/informational.md` (Task 3).

- [ ] **Step 1: Критерии приёмки**

Принято, если: (1) ≤ ~1.5 экрана; (2) приёмы «к применению» при письме поста; (3) покрыты: тест большой идеи (5 вопросов), правила заголовка (конкретика/выгода/новость/длинные работают/без каламбуров), body-copy (факты, простота, разговорность), ясность > оригинальности; (4) отброшены кейсы/персона/верификация/ТВ-реклама и прочее нерелевантное посту; (5) свои директивы, без дословного копирования; (6) верность источнику.

- [ ] **Step 2: Прочитать источник и выделить применимое**

Прочитай `docs/superpowers/working/Инструкция_AI-наставник_Огилви.md`. Выпиши применимое к письму поста (Step 1). Игнорируй ТВ/иллюстрации/P&G-кейсы и прочее вне текста поста.

- [ ] **Step 3: Написать `frameworks/ogilvy.md`**

Формат как у hormozi.md: шапка («Дистиллят: приёмы Огилви для письма постов. Применяется `purposes/informational.md` и `purposes/selling.md`.») → разделы (большая идея, заголовки, body-copy, ясность) = что + как применить + мини-пример. Директивами.

- [ ] **Step 4: Самопроверка против критериев** — объём, релевантность посту, верность, свои формулировки. Исправь инлайн.

- [ ] **Step 5: Commit**

```bash
git add skills/post-hq/references/frameworks/ogilvy.md
git commit -m "post-hq: frameworks/ogilvy.md — дистиллят приёмов Огилви"
```
(+ Co-Authored-By строка, как в Task 1)

---

## Task 3: `purposes/informational.md` — роль «экспертный пост»

**Files:**
- Create: `skills/post-hq/references/purposes/informational.md`

**Interfaces:**
- Consumes: `frameworks/ogilvy.md` (Task 2), `brand-voice` (голос), `writing-principles`.
- Produces: роль-цель, которую читает `SKILL.md` (Task 7) при informational-постах.

- [ ] **Step 1: Критерии приёмки**

Принято, если: (1) роль-инструкция «ты — агент, пишущий экспертный/контентный пост»; (2) опора: полезное действие, миф → разбор, числа-якоря, личный опыт; (3) грузит `frameworks/ogilvy.md` (заголовки/большая идея/ясность), НЕ грузит hormozi; (4) явно: голос (`brand-voice`) — последний фильтр; (5) НЕ дублирует текст брендвойса/принципов, ссылается.

- [ ] **Step 2: Написать `purposes/informational.md`**

Структура: Роль · Когда применяется · Что усиливает (полезное действие, миф→разбор, числа-якоря, личный опыт — со ссылкой на `../frameworks/ogilvy.md`) · Чего избегать (продающее давление — это не сюда) · Порядок: сначала каркас по цели, затем прогон через `writing-principles` и голос последним.

- [ ] **Step 3: Самопроверка** — против критериев; нет дублирования references; ссылки на пути корректны. Исправь инлайн.

- [ ] **Step 4: Commit**

```bash
git add skills/post-hq/references/purposes/informational.md
git commit -m "post-hq: purposes/informational.md — роль экспертного поста"
```
(+ Co-Authored-By)

---

## Task 4: `purposes/selling.md` — роль «продающий пост»

**Files:**
- Create: `skills/post-hq/references/purposes/selling.md`

**Interfaces:**
- Consumes: `frameworks/hormozi.md` (Task 1), `frameworks/ogilvy.md` (Task 2), `brand-voice`, `writing-principles`.
- Produces: роль-цель, которую читает `SKILL.md` (Task 7) при selling-постах.

- [ ] **Step 1: Критерии приёмки**

Принято, если: (1) роль «ты — агент, пишущий продающий/прогревочный пост»; (2) опора: оффер, боль→решение, ценность/усилители/гарантии/дедлайн (ссылка на `../frameworks/hormozi.md`) + заголовок/ясность (ссылка на `../frameworks/ogilvy.md`); (3) **страховка против инфоцыганщины**: голос (`brand-voice §9`) — последний фильтр, запрет на пустой хайп и ложные обещания; (4) честность оффера (не обещать лишнего); (5) НЕ дублирует references.

- [ ] **Step 2: Написать `purposes/selling.md`**

Структура: Роль · Когда применяется · Скелет убеждения (Хормози: Value Equation, Grand Slam, усилители, гарантии, scarcity/urgency — со ссылкой на `../frameworks/hormozi.md`; Огилви: заголовок/ясность — ссылка) · 🛑 Страховка: голос последним фильтром, без инфоцыганщины и ложных обещаний (явная отсылка к `brand-voice §9` и честности) · Порядок: каркас оффера → `writing-principles` → голос последним.

- [ ] **Step 3: Самопроверка** — против критериев; страховка §9 на месте; ссылки корректны. Исправь инлайн.

- [ ] **Step 4: Commit**

```bash
git add skills/post-hq/references/purposes/selling.md
git commit -m "post-hq: purposes/selling.md — роль продающего поста (со страховкой §9)"
```
(+ Co-Authored-By)

---

## Task 5: `platforms/telegram.md` — модуль площадки

**Files:**
- Create: `skills/post-hq/references/platforms/telegram.md`

**Interfaces:**
- Consumes: `brand-voice §8` (вёрстка/тире).
- Produces: модуль площадки, который читает `SKILL.md` (Task 7); задаёт КОНТРАКТ платформы для Фазы 2.

- [ ] **Step 1: Критерии приёмки**

Принято, если контракт-шаблон: (1) Роль (копирайтер Telegram-лонгрида); (2) Лимиты/длина (ориентир 300–600 слов, гибко); (3) Структура (заголовок-первая-строка → хук → тело с подзаголовками → концовка/CTA); (4) Вёрстка — ссылка на `brand-voice §8` (2-строчный ритм + исключения + длинное тире по минимуму), НЕ переписывать; (5) Типы CTA (комментарий/реакция/сохранение/переход/опрос); (6) Чек-лист; (7) Антипаттерны. Работает и для контента, и для продажи (цель приходит из purpose-модуля).

- [ ] **Step 2: Написать `platforms/telegram.md`**

По образцу формата ogilvy-content-machine `telegram.md`, но: вёрстку НЕ дублировать (ссылка на `brand-voice §8`), тон/словарь НЕ задавать (это голос). Только специфику площадки Telegram. Стиль роли-инструкции.

- [ ] **Step 3: Самопроверка** — 7 пунктов; вёрстка ссылкой, не копией; не лезет в голос/цель. Исправь инлайн.

- [ ] **Step 4: Commit**

```bash
git add skills/post-hq/references/platforms/telegram.md
git commit -m "post-hq: platforms/telegram.md — модуль площадки (контракт)"
```
(+ Co-Authored-By)

---

## Task 6: `review.md` — роль-ревьюер

**Files:**
- Create: `skills/post-hq/references/review.md`

**Interfaces:**
- Consumes: `brand-voice §4/§6/§8`, активный `platforms/*` и `purposes/*`.
- Produces: роль-ревьюер, которую `SKILL.md` (Task 7) запускает в review-цикле.

- [ ] **Step 1: Критерии приёмки**

Принято, если ревьюер проверяет: (а) светофор `brand-voice §6` (🟢/🟡/🔴, в 🔴 — прямо); (б) анти-шаблон `§4`; (в) вёрстка/длинное тире `§8`; (г) чек-лист активной платформы; (д) для selling — честность оффера (не обещать лишнего, без инфоцыганщины); и при браке возвращает КОНКРЕТНЫЕ замечания писателю (цикл).

- [ ] **Step 2: Написать `review.md`**

Роль-инструкция «ты — агент-ревьюер». Вход: текст писателя + какая платформа/цель. Чек-лист (а–д со ссылками на секции brand-voice и на активные модули). Выход: вердикт 🟢 пропустить / правки с конкретикой → назад писателю.

- [ ] **Step 3: Самопроверка** — все 5 проверок; цикл возврата описан; ссылки корректны. Исправь инлайн.

- [ ] **Step 4: Commit**

```bash
git add skills/post-hq/references/review.md
git commit -m "post-hq: review.md — роль-ревьюер (светофор + чек-листы)"
```
(+ Co-Authored-By)

---

## Task 7: `SKILL.md` — оркестратор штаба

**Files:**
- Create: `skills/post-hq/SKILL.md`

**Interfaces:**
- Consumes: все `references/*` (Tasks 1–6), `skills/brand-voice/references/*`, скилл `carousel-script`.
- Produces: точку входа `name: post-hq` + триггерный `description`.

- [ ] **Step 1: Критерии приёмки**

Принято, если: (1) frontmatter `name: post-hq` + `description` с триггерами; (2) Шаг 0 — читать `brand-voice` + `writing-principles`; (3) Роутинг платформа × цель: берёт выбор пользователя или РЕКОМЕНДУЕТ; (4) Генерация (роль писателя): читает `platforms/<X>.md` + `purposes/<Y>.md` (+ `frameworks/*` если selling); (5) Review-цикл через `review.md` (брак → назад); (6) Карточки → делегирование `carousel-script`; (7) Границы: не постит/не доставляет, не переписывает замысел; (8) условная загрузка фреймворков (selling — оба, informational — ogilvy).

- [ ] **Step 2: Прогнать судительное ядро через `meta-prompt`**

Вызови скилл `meta-prompt` для ядра «роутинг + рекомендация платформы/цели + порядок наложения слоёв (голос последним)» — чтобы логика была грамотной и без галлюцинаций. Вывод — сырьё, адаптируй.

- [ ] **Step 3: Написать `SKILL.md`**

По образцу ogilvy-content-machine (оркестратор), но тоньше: роль-штаб → Шаг 0 → лестница входов (наследуется из brand-voice) → роутинг (платформа × цель, рекомендация) → генерация (writer-роль читает модули) → review-цикл → делегирование carousel → границы. Условная загрузка фреймворков прописана явно. Триггеры в description: «напиши пост», «продающий пост», «прогрев», «пост в телегу», «оформи в моём голосе/стиле».

- [ ] **Step 4: Самопроверка** — 8 пунктов; description триггерится; references не продублированы; пути корректны. Исправь инлайн.

- [ ] **Step 5: Commit**

```bash
git add skills/post-hq/SKILL.md
git commit -m "post-hq: SKILL.md — оркестратор штаба (роутинг платформа×цель + review)"
```
(+ Co-Authored-By)

---

## Task 8: Упаковка — README, каталог, подключение

**Files:**
- Create: `skills/post-hq/README.md`
- Modify: `skills/README.md`

- [ ] **Step 1: Написать `README.md`** — кратко в стиле хаба: что делает (штаб постов: платформа × цель, голос brand-voice, review, делегирует carousel-script), когда срабатывает (триггеры), что внутри (`SKILL.md` + `references/{platforms,purposes,frameworks,review}`), что НЕ делает (не постит). Упомянуть фазы (сейчас Telegram; далее остальные площадки).

- [ ] **Step 2: Строка в каталог `skills/README.md`** (в таблицу, в конец):

```
| [post-hq/](post-hq/) | Штаб постов: ведёт идею через голос (brand-voice) → цель (контент/продажа по Огилви/Хормози) → площадку (Telegram) → ревью; делегирует визуал carousel-script |
```

- [ ] **Step 3: Подключить глобально** (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File .\skills\install-skills.ps1
```

- [ ] **Step 4: Проверить junction** (Bash):

```bash
ls -la ~/.claude/skills/post-hq
```
Ожидаемо: junction → `skills/post-hq` в репо. Если нет — отчитайся BLOCKED с выводом.

- [ ] **Step 5: Commit** (только README + каталог; junction не коммитим):

```bash
git add skills/post-hq/README.md skills/README.md
git commit -m "post-hq: README + строка в каталог-витрину"
```
(+ Co-Authored-By)

---

## Task 9: Поведенческий eval-прогон

**Files:**
- Working (не коммитим): `docs/superpowers/working/post-hq-evals.md`

- [ ] **Step 1: Кейсы** (записать ожидания):
  1. **Триггер** — «напиши пост в телегу про X» → активируется post-hq, читает brand-voice.
  2. **Informational/Telegram** — «опиши новость: …» → экспертный пост, голос + вёрстка, hormozi НЕ подмешан.
  3. **Selling/Telegram** — «сделай продающий пост про мой клуб, оффер …» → продающий по Хормози/Огилви, НО через голос, без инфоцыганщины (§9), оффер честный.
  4. **Роутинг-рекомендация** — вход без указания цели/площадки → штаб рекомендует платформу×цель.
  5. **Review-цикл** — заведомо слабый каркас → ревьюер ловит (🔴), возвращает конкретные правки.
  6. **Голос последним** — в продающем посте сохранён голос автора, не звучит как чужой инфобизнес.
  7. **Карточки** — запрос «пост + карточки для Threads» → делегирование `carousel-script` (без дублирования визуала).

- [ ] **Step 2: Прогнать** каждый кейс в свежем контексте (через Skill post-hq), зафиксировать факт в `post-hq-evals.md`.

- [ ] **Step 3: Сверить и исправить** артефакты, где поведение разошлось (чаще — `purposes/selling.md` §9-страховка, роутинг в SKILL.md, условная загрузка). Перепрогнать упавшие.

- [ ] **Step 4: Гейт автора** — показать результаты (особенно кейсы 3, 5, 6 — продажа-через-голос и ревью). Правки по фидбеку.

- [ ] **Step 5: Commit правок**

```bash
git add skills/post-hq/
git commit -m "post-hq: правки по результатам eval-прогона"
```
(+ Co-Authored-By)

---

## Task 10: Финал ветки

- [ ] **Step 1: Обновить память проекта** — `post-hq` Фаза 1 готова; Фаза 2 (threads-x, linkedin, instagram-caption) — следующий цикл.

- [ ] **Step 2: Финальное ревью всей ветки** свежим ревьюером (спек-покрытие Фазы 1, согласованность ссылок между модулями, условная загрузка, голос-последним, копирайт-дистиллят).

- [ ] **Step 3: Завершить ветку** через `superpowers:finishing-a-development-branch` (merge `post-hq` → `main` + push по слову автора).

---

## Self-Review (план против спека)

**Покрытие спека (Фаза 1):**
- Архитектура (платформа × цель, модули-роли) → Tasks 3–7. ✓
- frameworks дистилляция + условная загрузка → Tasks 1,2 + ссылки в 3,4 + Task 7 Step 1.8. ✓
- Голос последним фильтром → Tasks 3,4 + SKILL.md (Task 7). ✓
- Оркестратор (роутинг/рекомендация/review/делегирование/границы) → Task 7. ✓
- Review-слой → Task 6. ✓
- Telegram-модуль (контракт) → Task 5. ✓
- Композиция (brand-voice не дублируется, carousel делегируется) → Global Constraints + Tasks 3–8. ✓
- Копирайт (наставники локально, дистиллят в скилл) → Global Constraints + Tasks 1,2. ✓
- Упаковка/подключение → Task 8. ✓
- meta-prompt для ядра → Task 7 Step 2. ✓
- Вне области (Фаза 2, постинг, воронка-автоматизация) → Global Constraints + Task 10. ✓

**Плейсхолдеры:** содержимое модулей не приведено дословно намеренно — оно дистиллируется из приватных наставников + гейтится вычиткой/eval (контентный, не кодовый артефакт). Объёмы/структуры заданы критериями приёмки.

**Согласованность имён/путей:** `references/frameworks/{hormozi,ogilvy}.md`, `references/purposes/{informational,selling}.md`, `references/platforms/telegram.md`, `references/review.md`, `SKILL.md` — используются одинаково в Tasks 1–9; `name: post-hq` consistent; ссылки на `brand-voice §4/§6/§8/§9` единообразны.
