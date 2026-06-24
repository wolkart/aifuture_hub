# Post-HQ (Фаза 2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в штаб `skills/post-hq/` три модуля площадок по контракту платформы — Threads/X, LinkedIn, Instagram-подписи — каждый со своей длиной/плотностью под формат.

**Architecture:** Аддитивная фаза: голос (`brand-voice`), цели (`purposes/`), фреймворки (`frameworks/`) и ревьюер (`review.md`) уже готовы и платформо-независимы. Добавляем только модули `platforms/<X>.md` по тому же контракту, что и `telegram.md`, и расширяем роутинг в `SKILL.md`.

**Tech Stack:** Markdown; Claude Code skills; образец-контракт — `skills/post-hq/references/platforms/telegram.md`; формат-референс для Threads/X — `ogilvy-content-machine/modules/threads.md` (изучен ранее).

## Global Constraints

- Язык — русский. Модули = роли-инструкции в стиле «ты — …».
- **Контракт платформы (как у `telegram.md`):** роль · длина и плотность (ПОД ФОРМАТ) · структура (хук → тело → концовка/CTA) · вёрстка · типы CTA · чек-лист · антипаттерны.
- **Длина/плотность — под формат** (принцип «тип поста + плотность, не число абзацев»; критерий «можно убрать предложение без потери — убери»). Threads/X — заведомо короткий формат; LinkedIn — профессиональный регистр; IG-подпись — текст ПОД визуал.
- **Голос и цели НЕ дублируются** — модуль площадки задаёт только специфику площадки. Тон/словарь — из `brand-voice`; зачем (контент/продажа) — из `purposes/`. Вёрстка/тире — ссылка на `brand-voice §8`; эмодзи — `§7`.
- Пути из `references/platforms/<X>.md`: до brand-voice — `../../../../skills/brand-voice/references/brand-voice.md`; внутри скилла — `../...`.
- Модуль работает И для informational, И для selling (цель приходит из purpose-модуля).
- Ветка `post-hq-phase2`. Спек: `docs/superpowers/specs/2026-06-23-post-hq-design.md` (контракт платформы + раздел «Фазы»).
- НЕ постит/не доставляет; визуал — делегирование `carousel-script`.

---

## File Structure (Фаза 2)

- Create: `skills/post-hq/references/platforms/threads-x.md` — Threads и X/Twitter (короткий микроконтент + нити).
- Create: `skills/post-hq/references/platforms/linkedin.md` — LinkedIn (профессиональный регистр).
- Create: `skills/post-hq/references/platforms/instagram-caption.md` — подпись к визуалу (пост/карусель/рилс).
- Modify: `skills/post-hq/SKILL.md` — роутинг: добавить три площадки в список доступных + ссылки на модули.
- Modify: `skills/post-hq/README.md` — отметить Фазу 2 как сделанную (площадки активны).
- Modify: `docs/superpowers/specs/2026-06-23-post-hq-design.md` — раздел «Фазы»: Фаза 2 готова.

(`review.md` НЕ меняем — он уже площадко-независим: «при добавлении новой платформы — подключить соответствующий `platforms/<X>.md`».)

---

## Task 1: `platforms/threads-x.md` — Threads и X/Twitter

**Files:**
- Create: `skills/post-hq/references/platforms/threads-x.md`
- Read (контракт-образец): `skills/post-hq/references/platforms/telegram.md`; формат-референс `/d/YandexDisk/#Блогинг/AI Future Club/Скиллы незаменимых/irreplaceable_hub-main/skills/ogilvy-content-machine/modules/threads.md` (если недоступен — ориентируйся на контракт telegram.md).

**Interfaces:**
- Produces: модуль площадки по контракту; читается `SKILL.md` (Task 4).

- [ ] **Step 1: Критерии приёмки**

Принято, если контракт-шаблон под формат: (1) Роль (копирайтер коротких постов Threads/X); (2) **Длина под формат:** заведомо короткий — X ≤ 280 символов, Threads ≤ 500; весь пост = по сути заголовок; (3) Два формата: одиночный пост и **нить (тред)** 3–7 постов (когда идея требует раскрытия); (4) Структура одиночного: зацеп → мясо (факт/цифра) → якорь; структура нити (пост 1 хук+обещание, тело по одному факту на пост, финал+CTA); (5) Вёрстка — ссылка на `brand-voice §8`, эмодзи `§7` (в коротком формате — особенно скупо); (6) Типы CTA (комментарий/репост/подписка/«нить 🧵»); (7) Чек-лист; (8) Антипаттерны. Цель — из `purposes/`, тон — из `brand-voice`.

- [ ] **Step 2: Написать `threads-x.md`** по контракту (как telegram.md), специфика: короткий формат, лимиты символов, нити, «весь пост = заголовок». Вёрстка/эмодзи — ссылками, не копией. Не задаёт тон/цель.

- [ ] **Step 3: Самопроверка** — 8 пунктов; длина именно под короткий формат (НЕ лонгрид); вёрстка/эмодзи ссылками; не лезет в голос/цель; пути резолвятся. Исправь инлайн.

- [ ] **Step 4: Commit**

```bash
git add skills/post-hq/references/platforms/threads-x.md
git commit -m "post-hq: platforms/threads-x.md — модуль Threads/X (короткий формат + нити)"
```
(+ строка: Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>)

---

## Task 2: `platforms/linkedin.md` — LinkedIn

**Files:**
- Create: `skills/post-hq/references/platforms/linkedin.md`
- Read (контракт-образец): `skills/post-hq/references/platforms/telegram.md`.

**Interfaces:**
- Produces: модуль площадки по контракту; читается `SKILL.md` (Task 4).

- [ ] **Step 1: Критерии приёмки**

Принято, если: (1) Роль (копирайтер LinkedIn); (2) **Длина под формат:** средняя, ориентир до ~1300 знаков основного текста (лимит площадки ~3000, но «see more» обрезает ~на 2-3 строках — первые строки решают); по типу+плотности; (3) **Профессиональный регистр БЕЗ потери голоса:** тот же автор, но аудитория профессиональная — меньше сленга, больше экспертной конкретики; голос (`brand-voice`) всё равно последним, не превращаемся в корпоративный канцелярит; (4) Структура: сильные первые 2-3 строки (до «see more») → тело с ценностью → вывод/вопрос; (5) Вёрстка — короткие абзацы, воздух (ссылка `§8`); эмодзи скупо-уместно (`§7`), LinkedIn терпит ещё меньше; (6) CTA (комментарий/мнение/connect); (7) хэштеги — 3-5 профессиональных в конце; (8) Чек-лист; (9) Антипаттерны (корп-булшит, канцелярит, хвастовство). Цель — из `purposes/`.

- [ ] **Step 2: Написать `linkedin.md`** по контракту. Подчеркни: профессиональный регистр — это про аудиторию и меньше сленга, НЕ про канцелярит; голос остаётся. Вёрстка/эмодзи ссылками.

- [ ] **Step 3: Самопроверка** — критерии; «профессионально ≠ канцелярит»; голос последним; пути. Исправь инлайн.

- [ ] **Step 4: Commit**

```bash
git add skills/post-hq/references/platforms/linkedin.md
git commit -m "post-hq: platforms/linkedin.md — модуль LinkedIn (проф. регистр, голос сохранён)"
```
(+ Co-Authored-By)

---

## Task 3: `platforms/instagram-caption.md` — подпись Instagram

**Files:**
- Create: `skills/post-hq/references/platforms/instagram-caption.md`
- Read (контракт-образец): `skills/post-hq/references/platforms/telegram.md`.

**Interfaces:**
- Produces: модуль площадки по контракту; читается `SKILL.md` (Task 4).

- [ ] **Step 1: Критерии приёмки**

Принято, если: (1) Роль (копирайтер подписи Instagram к визуалу — посту/карусели/рилс); (2) **Текст ПОД визуал:** подпись дополняет картинку/карусель/видео, не дублирует; (3) **Длина под формат:** первая строка-хук критична (обрезка ~125 символов до «ещё»); дальше — по типу/плотности; (4) Структура: хук (до обрезки) → раскрытие → CTA; (5) CTA (сохранить/комментарий/«ссылка в шапке»/смотри карусель); (6) **хэштеги** — блок в конце, ~5-15 релевантных (не спам); (7) Вёрстка — воздух (IG ужимает переносы, но абзацы нужны); эмодзи `§7` (в IG уместны чуть щедрее, но без спама); (8) **Связка с carousel-script:** подпись идёт В ПАРЕ с визуалом, который делает carousel-script — отметить, что это текст-компаньон, не дубль слайдов; (9) Чек-лист; (10) Антипаттерны. Цель — из `purposes/`.

- [ ] **Step 2: Написать `instagram-caption.md`** по контракту. Подчеркни: подпись = компаньон визуала; первая строка до обрезки решает; хэштеги-блок. Вёрстка/эмодзи ссылками.

- [ ] **Step 3: Самопроверка** — критерии; текст-компаньон (не дубль визуала); хук до обрезки; хэштеги; пути. Исправь инлайн.

- [ ] **Step 4: Commit**

```bash
git add skills/post-hq/references/platforms/instagram-caption.md
git commit -m "post-hq: platforms/instagram-caption.md — модуль подписи IG (компаньон визуала)"
```
(+ Co-Authored-By)

---

## Task 4: Роутинг `SKILL.md` + статус фаз (README/спек)

**Files:**
- Modify: `skills/post-hq/SKILL.md` (секция «Роутинг»)
- Modify: `skills/post-hq/README.md` (раздел «Фазы»)
- Modify: `docs/superpowers/specs/2026-06-23-post-hq-design.md` (раздел «Фазы»)

**Interfaces:**
- Consumes: `platforms/threads-x.md`, `linkedin.md`, `instagram-caption.md` (Tasks 1–3).

- [ ] **Step 1: Критерии приёмки**

(1) В `SKILL.md` секция «Роутинг» перечисляет ВСЕ доступные площадки (telegram, threads-x, linkedin, instagram-caption) со ссылками на их модули `references/platforms/<X>.md`; (2) README раздел «Фазы»: Фаза 2 отмечена как сделанная (площадки активны); (3) спек раздел «Фазы»: Фаза 2 — готова. Триггеры в `description` дополнить площадками (threads/linkedin/инстаграм), если их там нет.

- [ ] **Step 2: Обновить `SKILL.md` роутинг.** Текущая строка «Сейчас доступна: `telegram`» → список из 4 площадок, каждая со ссылкой на свой модуль. При желании дополнить `description` триггерами «пост в threads/x», «пост в linkedin», «подпись для инсты».

- [ ] **Step 3: Обновить `README.md`** — в разделе «Фазы» отметить Фазу 2 сделанной (Threads/X, LinkedIn, Instagram-подписи активны).

- [ ] **Step 4: Обновить спек** — раздел «Фазы»: Фаза 2 ✅ (модули добавлены).

- [ ] **Step 5: Commit**

```bash
git add skills/post-hq/SKILL.md skills/post-hq/README.md docs/superpowers/specs/2026-06-23-post-hq-design.md
git commit -m "post-hq: роутинг на 4 площадки + статус Фазы 2 (README, спек)"
```
(+ Co-Authored-By)

---

## Task 5: Поведенческий eval-прогон (Фаза 2) + гейт автора

**Files:**
- Working (не коммитим): `docs/superpowers/working/post-hq-phase2-evals.md`

- [ ] **Step 1: Кейсы** (записать ожидания):
  1. **Threads/X одиночный** — «короткий пост для X про то, что AI усиливает» → ≤280 символов, по сути заголовок, голос сохранён.
  2. **Threads нить** — «сделай нить в threads про 3 ошибки в промптинге» → нить 3-5 постов, по одному факту на пост, финал+CTA.
  3. **LinkedIn** — «пост в linkedin про переход в AI-разработку» → проф. регистр БЕЗ канцелярита, сильные первые строки, голос на месте, хэштеги.
  4. **Instagram-подпись + связка** — «подпись для карусели про вайб-кодинг» → хук до обрезки, CTA, хэштеги, отмечено что визуал делегируется carousel-script.
  5. **Роутинг по площадкам** — «напиши пост в linkedin …» → штаб берёт linkedin-модуль (не telegram).
  6. **Длина под формат** — один и тот же тезис в Telegram vs Threads → Telegram длиннее/развёрнутее, Threads сжат до заголовка (доказать, что длина адаптируется).

- [ ] **Step 2: Прогнать** через Skill `post-hq` в свежем контексте, зафиксировать в `post-hq-phase2-evals.md`.

- [ ] **Step 3: Сверить и исправить** артефакты, где разошлось (чаще — длина/регистр конкретной площадки). Перепрогнать упавшие.

- [ ] **Step 4: Гейт автора** — показать результаты (особенно LinkedIn-регистр и Threads-сжатие). Правки по фидбеку.

- [ ] **Step 5: Commit правок**

```bash
git add skills/post-hq/
git commit -m "post-hq: правки по результатам eval Фазы 2"
```
(+ Co-Authored-By)

---

## Task 6: Финал ветки

- [ ] **Step 1: Обновить память** — post-hq Фаза 2 готова (4 площадки активны); следующее — интеграция content-machine → post-hq + ai-research (роадмап).
- [ ] **Step 2: Финальное ревью всей ветки** свежим ревьюером (контракт платформы выдержан в 3 модулях; длина под формат; голос/цель не продублированы; пути; роутинг обновлён; согласованность).
- [ ] **Step 3: Завершить ветку** через `superpowers:finishing-a-development-branch` (merge `post-hq-phase2` → `main` + push по слову автора).

---

## Self-Review (план против спека)

**Покрытие (Фаза 2 из спека «Фазы» + контракт платформы):**
- `threads-x.md`, `linkedin.md`, `instagram-caption.md` по контракту → Tasks 1–3. ✓
- Длина/плотность ПОД ФОРМАТ (Threads короче и т.д.) → критерии приёмки Tasks 1–3. ✓
- Голос/цели не дублируются, вёрстка/эмодзи ссылками → Global Constraints + Tasks 1–3. ✓
- Роутинг на все площадки → Task 4. ✓
- Связка IG-подписи с carousel-script → Task 3. ✓
- Статус фаз (README/спек) → Task 4. ✓
- eval + гейт → Task 5. ✓
- `review.md` площадко-независим (не меняем) → отмечено в File Structure. ✓

**Плейсхолдеры:** содержимое модулей не приведено дословно намеренно — генерируется по контракту + гейтится eval/вычиткой (контентный артефакт). Структуры/лимиты заданы критериями приёмки.

**Согласованность путей/имён:** `references/platforms/{threads-x,linkedin,instagram-caption}.md` единообразны; пути к brand-voice из `platforms/` = `../../../../skills/brand-voice/...` (как в telegram.md); роутинг в SKILL.md ссылается на эти же пути.
