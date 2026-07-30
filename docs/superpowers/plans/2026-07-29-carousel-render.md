# carousel-render Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Скилл, который превращает `slides.json` + тему в папку готовых PNG-карточек карусели 1080×1350 в фирменном стиле автора.

**Architecture:** Три слоя. Тема (`theme.json` вне репозитория) — все переменные: цвета, шрифты с весами, ассеты, обвязка под площадку, ступени кегля. Лейауты (HTML+CSS в репозитории) — четыре фиксированных шаблона, композиция зашита в код. Скрипты — детерминированный конвейер: собрать самодостаточный HTML → измерить переполнение через Chrome `--dump-dom` → выбрать ступень кегля → снять скриншот → ужать до 1080×1350.

**Tech Stack:** Python 3 (только stdlib), HTML + CSS, headless Google Chrome, `sips` (macOS). Тесты — pytest. Новых зависимостей не добавляем.

**Спека:** [docs/superpowers/specs/2026-07-29-carousel-render-skill-design.md](../specs/2026-07-29-carousel-render-skill-design.md)

## Global Constraints

- **Формат карточки:** 1080 × 1350 px (4:5). Рендер в 2× (2160 × 2700), затем `sips -z 1350 1080`.
- **Только stdlib.** Никаких pip-зависимостей в рантайме скилла. pytest — только для тестов.
- **Прогон тестов.** В системном `python3` pytest не установлен. Фактическая команда — `uv run --quiet --with pytest python -m pytest …` из папки скилла. Там, где в шагах написано `python3 -m pytest`, читать как эту команду (сами скрипты скилла запускаются обычным `python3`, им pytest не нужен).
- **Chrome:** `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.
- **Самодостаточный HTML.** Шрифты, картинки и CSS встраиваются в один файл как `data:` URI. Ноль внешних запросов, ноль обращений к `file://` из документа. Это снимает и блокировку шрифтов на `file://`, и недетерминизм порядка загрузки.
- **`--virtual-time-budget=2000`** обязателен в обоих проходах Chrome — без него скриншот успевает сняться до применения `@font-face`, и всё уезжает в засечный фолбэк.
- **Обезличенность.** В репозитории только `themes/example.json` с нейтральными цветами и системными шрифтами. Тема автора — вне репозитория, путь в `.env` (`THEME_PATH`).
- **Язык кода:** имена функций и переменных латиницей, докстринги и комментарии по-русски — как в `skills/rough-cut/scripts/`.
- **Бренд-константы** (в тему автора, не в репозиторий): фон тёмный radial `#222147` → `#020105`; фон светлый radial `#FFFFFF` → `#E0E9FF`; заголовок обложки `#6695F1`; акцент `#D97757`; текст тела `#33336F`; должность `#ADADAD`; бейдж на тёмном `#E8E7EB`; бейдж на светлом — кружок `#33336F`, текст `#F7F6FF`.
- **Шрифты:** Oswald (обложка целиком), Montserrat (всё остальное). Оба — вариативные TTF с Google Fonts, кириллица включена.
- **Лейауты — закрытый словарь:** `обложка`, `тело`, `тело-список`, `CTA`. Расширять нельзя.

---

## File Structure

```
skills/carousel-render/
├── SKILL.md                    # оркестрация (Task 11)
├── README.md                   # что делает / когда срабатывает (Task 11)
├── .env.template               # THEME_PATH, OUTPUT_DIR (Task 1)
├── evals/evals.json            # триггер-тесты (Task 11)
├── references/
│   ├── theme-schema.md         # что можно менять в теме (Task 11)
│   └── layouts.md              # словарь лейаутов и поля слайдов (Task 11)
├── themes/
│   └── example.json            # нейтральная тема (Task 2)
├── layouts/
│   ├── base.css                # сброс, карточка, фоны, обвязка (Task 4, 6)
│   ├── cover.css               # обложка + виды декор/фото (Task 4, 8)
│   ├── body.css                # тело (Task 7)
│   ├── body-list.css           # тело-список (Task 7)
│   └── cta.css                 # CTA (Task 8)
├── scripts/
│   ├── check_env.py            # доктор окружения (Task 1)
│   ├── fonts.py                # скачать шрифты в папку темы (Task 1)
│   ├── theme.py                # загрузка/валидация темы, обвязка (Task 2)
│   ├── markup.py               # инлайн-разметка → HTML (Task 3)
│   ├── build_html.py           # слайд + тема → самодостаточный HTML (Task 4)
│   ├── render.py               # Chrome: скриншот и замер; sips (Task 5)
│   ├── fit.py                  # выбор ступени кегля, недобор в символах (Task 9)
│   ├── contact_sheet.py        # простыня всех слайдов (Task 10)
│   └── carousel_render.py      # оркестратор CLI (Task 10)
└── tests/
    ├── conftest.py             # sys.path + фикстуры (Task 1)
    ├── test_check_env.py       ├── test_fit.py
    ├── test_theme.py           ├── test_contact_sheet.py
    ├── test_markup.py          └── test_carousel_render.py
    ├── test_build_html.py
    ├── test_render.py
```

Границы: `theme.py` ничего не знает про HTML; `markup.py` — чистые строковые преобразования; `build_html.py` собирает разметку и не запускает процессов; `render.py` — единственный, кто вызывает Chrome и `sips`; `fit.py` — чистая арифметика подбора плюс тонкий цикл поверх `build_html`+`render`.

---

## Task 1: Каркас скилла и доктор окружения

**Files:**
- Create: `skills/carousel-render/scripts/check_env.py`
- Create: `skills/carousel-render/scripts/fonts.py`
- Create: `skills/carousel-render/tests/conftest.py`
- Create: `skills/carousel-render/tests/test_check_env.py`
- Create: `skills/carousel-render/.env.template`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: ничего
- Produces:
  - `check_env.check_chrome() -> tuple[bool, str]`
  - `check_env.check_sips() -> tuple[bool, str]`
  - `check_env.check_theme(theme_path: str | None) -> tuple[bool, str]`
  - `check_env.check_fonts(theme_dir: Path) -> tuple[bool, str]`
  - `check_env.report(checks: list[tuple[str, bool, str]]) -> str`
  - `fonts.FONT_URLS: dict[str, str]`
  - `fonts.ensure_fonts(theme_dir: Path, download: bool = True) -> list[str]`

- [ ] **Step 1: Написать conftest**

```python
# skills/carousel-render/tests/conftest.py
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

CARD_W, CARD_H = 1080, 1350


@pytest.fixture
def theme_dir(tmp_path):
    """Папка темы с минимальным набором файлов."""
    d = tmp_path / "theme"
    (d / "fonts").mkdir(parents=True)
    (d / "assets").mkdir()
    (d / "fonts" / "Oswald.ttf").write_bytes(b"fake-oswald")
    (d / "fonts" / "Montserrat.ttf").write_bytes(b"fake-montserrat")
    (d / "assets" / "avatar-ig.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (d / "assets" / "avatar-li.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (d / "assets" / "spark.svg").write_text('<svg viewBox="0 0 10 10"/>')
    return d


@pytest.fixture
def theme_file(theme_dir):
    """theme.json рядом с ассетами. Значения нейтральные, не бренд автора."""
    data = {
        "формат": {"ширина": 1080, "высота": 1350, "масштаб_рендера": 2},
        "фоны": {
            "тёмный": {"тип": "radial", "стопы": ["#222147", "#020105"]},
            "светлый": {"тип": "radial", "стопы": ["#FFFFFF", "#E0E9FF"]},
        },
        "цвета": {
            "заголовок_обложки": "#6695F1",
            "акцент": "#D97757",
            "текст_тела": "#33336F",
            "текст_на_тёмном": "#FFFFFF",
            "должность": "#ADADAD",
            "бейдж_на_тёмном": "#E8E7EB",
            "бейдж_кружок_на_светлом": "#33336F",
            "бейдж_текст_на_светлом": "#F7F6FF",
        },
        "шрифты": {
            "файлы": {"oswald": "fonts/Oswald.ttf", "montserrat": "fonts/Montserrat.ttf"},
            "роли": {
                "заголовок_обложки": {"семейство": "Oswald", "вес": 700},
                "подзаголовок_обложки": {"семейство": "Oswald", "вес": 700},
                "текст_тела": {"семейство": "Montserrat", "вес": 500},
                "выделение_тела": {"семейство": "Montserrat", "вес": 700},
                "заголовок_списка": {"семейство": "Montserrat", "вес": 800},
                "подпись_имя": {"семейство": "Montserrat", "вес": 600},
                "подпись_должность": {"семейство": "Montserrat", "вес": 400},
                "бейдж": {"семейство": "Montserrat", "вес": 300},
            },
        },
        "ступени": {
            "обложка_заголовок": [200, 150, 110],
            "обложка_подзаголовок": [56, 48, 40],
            "тело": [60, 52, 44],
            "тело_список": [42, 37, 32],
            "cta": [50, 44, 38],
        },
        "ассеты": {"спарк": "assets/spark.svg"},
        "обвязка": {
            "IG": {
                "аватар": "assets/avatar-ig.png",
                "подпись": ["@ai_rtem"],
                "позиции": {
                    "обложка": {"бейдж": "верх-центр", "подпись": "низ-лево"},
                    "тело": {"бейдж": "низ-право", "подпись": "низ-лево"},
                    "тело-список": {"бейдж": "низ-право", "подпись": "низ-лево"},
                    "CTA": {"бейдж": "нет", "подпись": "верх-центр"},
                },
            },
            "LI": {
                "аватар": "assets/avatar-li.png",
                "подпись": ["Artem Volkov", "AI-Developer & Content Creator"],
                "позиции": {
                    "обложка": {"бейдж": "верх-центр", "подпись": "низ-центр"},
                    "тело": {"бейдж": "верх-центр", "подпись": "низ-центр"},
                    "тело-список": {"бейдж": "верх-центр", "подпись": "низ-центр"},
                    "CTA": {"бейдж": "нет", "подпись": "верх-центр"},
                },
            },
        },
    }
    p = theme_dir / "theme.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p
```

- [ ] **Step 2: Написать падающий тест доктора**

```python
# skills/carousel-render/tests/test_check_env.py
from pathlib import Path

import check_env


def test_check_theme_missing_env():
    ok, msg = check_env.check_theme(None)
    assert ok is False
    assert "THEME_PATH" in msg


def test_check_theme_missing_file(tmp_path):
    ok, msg = check_env.check_theme(str(tmp_path / "нет.json"))
    assert ok is False
    assert "не найден" in msg


def test_check_theme_ok(theme_file):
    ok, msg = check_env.check_theme(str(theme_file))
    assert ok is True


def test_check_fonts_ok(theme_dir):
    ok, msg = check_env.check_fonts(theme_dir)
    assert ok is True


def test_check_fonts_missing(tmp_path):
    (tmp_path / "fonts").mkdir()
    ok, msg = check_env.check_fonts(tmp_path)
    assert ok is False
    assert "Oswald" in msg


def test_report_marks_failures():
    text = check_env.report([("Chrome", True, "есть"), ("Шрифты", False, "нет Oswald")])
    assert "✓ Chrome" in text
    assert "✗ Шрифты" in text
    assert "нет Oswald" in text
```

- [ ] **Step 3: Запустить, убедиться что падает**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_check_env.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'check_env'`

- [ ] **Step 4: Написать check_env.py**

```python
#!/usr/bin/env python3
"""Доктор окружения carousel-render. Только stdlib.

Проверяет то, без чего рендер молча выдаст брак: Chrome, sips, читаемую тему
и наличие файлов шрифтов. Отсутствие шрифтов — самый коварный случай: Chrome
не падает, а рисует засечным фолбэком.
"""
import argparse
import os
import shutil
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
REQUIRED_FONTS = ("Oswald", "Montserrat")


def check_chrome():
    """Chrome на штатном месте?"""
    if Path(CHROME).exists():
        return True, CHROME
    return False, f"не найден по пути {CHROME}"


def check_sips():
    """sips есть в PATH? Нужен для ужатия 2× → 1×."""
    path = shutil.which("sips")
    return (True, path) if path else (False, "не найден в PATH (нужен macOS)")


def check_theme(theme_path):
    """THEME_PATH задан и файл существует?"""
    if not theme_path:
        return False, "THEME_PATH не задан в .env — скилл не знает, где твоя тема"
    p = Path(theme_path)
    if not p.exists():
        return False, f"файл темы не найден: {p}"
    return True, str(p)


def check_fonts(theme_dir):
    """Файлы шрифтов лежат в папке темы?

    В системе автора Oswald и Montserrat не установлены — они живут только
    в Figma. Поэтому единственный надёжный источник это файлы рядом с темой.
    """
    fonts_dir = Path(theme_dir) / "fonts"
    missing = [n for n in REQUIRED_FONTS
               if not list(fonts_dir.glob(f"{n}*.ttf")) + list(fonts_dir.glob(f"{n}*.otf"))]
    if missing:
        return False, ("нет файлов: " + ", ".join(missing)
                       + " — запусти scripts/fonts.py, он скачает их с Google Fonts")
    return True, str(fonts_dir)


def report(checks):
    """checks: [(название, ок, сообщение)] → человекочитаемый отчёт."""
    lines = []
    for name, ok, msg in checks:
        lines.append(f"{'✓' if ok else '✗'} {name}: {msg}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--theme", default=os.environ.get("THEME_PATH"))
    args = ap.parse_args()

    theme_ok, theme_msg = check_theme(args.theme)
    checks = [("Chrome", *check_chrome()), ("sips", *check_sips()),
              ("Тема", theme_ok, theme_msg)]
    if theme_ok:
        checks.append(("Шрифты", *check_fonts(Path(args.theme).parent)))

    print(report(checks))
    raise SystemExit(0 if all(ok for _, ok, _ in checks) else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Запустить тесты доктора**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_check_env.py -v`
Expected: PASS, 6 тестов

- [ ] **Step 6: Написать падающий тест загрузчика шрифтов**

```python
# добавить в skills/carousel-render/tests/test_check_env.py
import fonts


def test_font_urls_cover_required():
    assert set(fonts.FONT_URLS) == {"Oswald", "Montserrat"}
    for url in fonts.FONT_URLS.values():
        assert url.startswith("https://")
        assert url.endswith(".ttf")


def test_ensure_fonts_skips_existing(theme_dir):
    # шрифты уже лежат — скачивать нечего
    assert fonts.ensure_fonts(theme_dir, download=False) == []


def test_ensure_fonts_reports_missing(tmp_path):
    got = fonts.ensure_fonts(tmp_path, download=False)
    assert sorted(got) == ["Montserrat", "Oswald"]
```

- [ ] **Step 7: Запустить, убедиться что падает**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_check_env.py -k font -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fonts'`

- [ ] **Step 8: Написать fonts.py**

```python
#!/usr/bin/env python3
"""Кладёт вариативные Oswald и Montserrat в папку темы. Только stdlib.

Оба под OFL, кириллица включена, вариативность закрывает все веса разом —
поэтому в теме вес задаётся числом, а не отдельным файлом на начертание.
"""
import argparse
import urllib.request
from pathlib import Path

FONT_URLS = {
    "Oswald": "https://github.com/google/fonts/raw/main/ofl/oswald/Oswald%5Bwght%5D.ttf",
    "Montserrat": "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf",
}


def missing_fonts(theme_dir):
    """Каких семейств нет в <тема>/fonts."""
    fonts_dir = Path(theme_dir) / "fonts"
    return [name for name in FONT_URLS
            if not list(fonts_dir.glob(f"{name}*.ttf"))]


def ensure_fonts(theme_dir, download=True):
    """Докачивает недостающие. Возвращает список тех, что были недостающими."""
    missing = missing_fonts(theme_dir)
    if not download:
        return missing
    fonts_dir = Path(theme_dir) / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    for name in missing:
        dest = fonts_dir / f"{name}.ttf"
        urllib.request.urlretrieve(FONT_URLS[name], dest)
    return missing


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("theme_dir")
    args = ap.parse_args()
    got = ensure_fonts(Path(args.theme_dir))
    print("скачано: " + ", ".join(got) if got else "все шрифты уже на месте")


if __name__ == "__main__":
    main()
```

- [ ] **Step 9: Запустить все тесты задачи**

Run: `cd skills/carousel-render && python3 -m pytest tests/ -v`
Expected: PASS, 9 тестов

- [ ] **Step 10: Создать .env.template и дополнить .gitignore**

```bash
# skills/carousel-render/.env.template
cat > skills/carousel-render/.env.template <<'EOF'
# Путь к theme.json со стилем автора (вне репозитория).
# Рядом с ним ожидаются папки fonts/ и assets/.
THEME_PATH=

# Куда складывать готовые карусели. Пусто — рядом со slides.json.
OUTPUT_DIR=
EOF
```

В корневой `.gitignore` дописать после блока `.env`:

```
# Локальные темы carousel-render (личный стиль не уходит в паблик)
skills/carousel-render/themes/local*
```

- [ ] **Step 11: Коммит**

```bash
git add skills/carousel-render/ .gitignore
git commit -m "carousel-render: каркас, доктор окружения, загрузчик шрифтов"
```

---

## Task 2: Тема — загрузка, валидация, обвязка

**Files:**
- Create: `skills/carousel-render/scripts/theme.py`
- Create: `skills/carousel-render/themes/example.json`
- Create: `skills/carousel-render/tests/test_theme.py`

**Interfaces:**
- Consumes: фикстуры `theme_dir`, `theme_file` из `conftest.py` (Task 1)
- Produces:
  - `theme.load(path: str | Path) -> dict` — тема с абсолютными путями ассетов и добавленным ключом `_dir: Path`
  - `theme.validate(data: dict) -> list[str]` — список проблем, пустой = ок
  - `theme.binding(data: dict, platform: str, layout: str) -> dict` с ключами `аватар` (Path), `подпись` (list[str]), `бейдж` (str), `подпись_позиция` (str)
  - `theme.steps(data: dict, key: str) -> list[int]`
  - `theme.LAYOUTS: tuple[str, ...]` = `("обложка", "тело", "тело-список", "CTA")`

- [ ] **Step 1: Написать падающий тест**

```python
# skills/carousel-render/tests/test_theme.py
import json
from pathlib import Path

import pytest

import theme


def test_load_resolves_asset_paths(theme_file):
    data = theme.load(theme_file)
    avatar = data["обвязка"]["IG"]["аватар"]
    assert isinstance(avatar, Path)
    assert avatar.is_absolute()
    assert avatar.exists()


def test_load_records_theme_dir(theme_file):
    data = theme.load(theme_file)
    assert data["_dir"] == theme_file.parent


def test_validate_accepts_good_theme(theme_file):
    assert theme.validate(theme.load(theme_file)) == []


def test_validate_reports_missing_color(theme_file):
    data = theme.load(theme_file)
    del data["цвета"]["акцент"]
    problems = theme.validate(data)
    assert any("акцент" in p for p in problems)


def test_validate_reports_missing_asset(theme_file):
    data = theme.load(theme_file)
    data["обвязка"]["IG"]["аватар"] = theme_file.parent / "нет.png"
    problems = theme.validate(data)
    assert any("нет.png" in p for p in problems)


def test_validate_requires_three_steps(theme_file):
    data = theme.load(theme_file)
    data["ступени"]["тело"] = [60]
    problems = theme.validate(data)
    assert any("тело" in p and "ступен" in p for p in problems)


def test_binding_ig_cover(theme_file):
    b = theme.binding(theme.load(theme_file), "IG", "обложка")
    assert b["подпись"] == ["@ai_rtem"]
    assert b["бейдж"] == "верх-центр"
    assert b["подпись_позиция"] == "низ-лево"


def test_binding_li_body_has_two_lines(theme_file):
    b = theme.binding(theme.load(theme_file), "LI", "тело")
    assert b["подпись"] == ["Artem Volkov", "AI-Developer & Content Creator"]
    assert b["подпись_позиция"] == "низ-центр"


def test_binding_unknown_platform_raises(theme_file):
    with pytest.raises(KeyError):
        theme.binding(theme.load(theme_file), "TikTok", "тело")


def test_steps_returns_descending(theme_file):
    got = theme.steps(theme.load(theme_file), "тело")
    assert got == sorted(got, reverse=True)


def test_example_theme_is_valid():
    """Пример темы в репозитории должен грузиться и проходить валидацию."""
    p = Path(__file__).parent.parent / "themes" / "example.json"
    data = theme.load(p)
    problems = [x for x in theme.validate(data) if "не найден" not in x]
    assert problems == []
```

- [ ] **Step 2: Запустить, убедиться что падает**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_theme.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'theme'`

- [ ] **Step 3: Написать theme.py**

```python
#!/usr/bin/env python3
"""Загрузка и проверка темы карусели. Только stdlib.

Тема — единственное место, где живут переменные внешнего вида. Композиция
лейаутов в коде, поэтому сюда нельзя добавить «ещё один шаблон»: сюда
добавляют значения.
"""
import argparse
import json
from pathlib import Path

LAYOUTS = ("обложка", "тело", "тело-список", "CTA")
PLATFORMS = ("IG", "LI")

REQUIRED_COLORS = ("заголовок_обложки", "акцент", "текст_тела",
                   "текст_на_тёмном", "должность", "бейдж_на_тёмном",
                   "бейдж_кружок_на_светлом", "бейдж_текст_на_светлом")
REQUIRED_ROLES = ("заголовок_обложки", "подзаголовок_обложки", "текст_тела",
                  "выделение_тела", "заголовок_списка", "подпись_имя",
                  "подпись_должность", "бейдж")
REQUIRED_STEPS = ("обложка_заголовок", "обложка_подзаголовок", "тело",
                  "тело_список", "cta")
STEP_COUNT = 3


def load(path):
    """Читает theme.json и делает пути ассетов абсолютными."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    data["_dir"] = base

    for key, rel in data.get("шрифты", {}).get("файлы", {}).items():
        data["шрифты"]["файлы"][key] = base / rel
    for key, rel in data.get("ассеты", {}).items():
        data["ассеты"][key] = base / rel
    for platform in data.get("обвязка", {}).values():
        if "аватар" in platform:
            platform["аватар"] = base / platform["аватар"]
    return data


def validate(data):
    """Список человекочитаемых проблем. Пустой список = тема годна."""
    problems = []

    for name in REQUIRED_COLORS:
        if name not in data.get("цвета", {}):
            problems.append(f"цвета: не хватает «{name}»")

    roles = data.get("шрифты", {}).get("роли", {})
    for name in REQUIRED_ROLES:
        if name not in roles:
            problems.append(f"шрифты.роли: не хватает «{name}»")

    steps = data.get("ступени", {})
    for name in REQUIRED_STEPS:
        values = steps.get(name)
        if not values:
            problems.append(f"ступени: не хватает «{name}»")
        elif len(values) != STEP_COUNT:
            problems.append(f"ступени.{name}: нужно ровно {STEP_COUNT} ступени, "
                            f"а задано {len(values)}")
        elif list(values) != sorted(values, reverse=True):
            problems.append(f"ступени.{name}: должны идти по убыванию")

    for key, path in data.get("шрифты", {}).get("файлы", {}).items():
        if not Path(path).exists():
            problems.append(f"шрифт «{key}» не найден: {path}")
    for key, path in data.get("ассеты", {}).items():
        if not Path(path).exists():
            problems.append(f"ассет «{key}» не найден: {path}")

    for name, platform in data.get("обвязка", {}).items():
        avatar = platform.get("аватар")
        if avatar and not Path(avatar).exists():
            problems.append(f"обвязка.{name}: аватар не найден: {avatar}")
        if not platform.get("подпись"):
            problems.append(f"обвязка.{name}: пустая подпись")

    return problems


def binding(data, platform, layout):
    """Блок обвязки под связку «площадка × лейаут».

    Обвязка — единственное, что зависит от площадки: у IG хэндл одной строкой,
    у LinkedIn имя с должностью в две, и аватарки разные.
    """
    block = data["обвязка"][platform]
    positions = block["позиции"].get(layout, {})
    return {
        "аватар": block["аватар"],
        "подпись": list(block["подпись"]),
        "бейдж": positions.get("бейдж", "верх-центр"),
        "подпись_позиция": positions.get("подпись", "низ-центр"),
    }


def steps(data, key):
    """Ступени кегля под роль, от крупной к мелкой."""
    return list(data["ступени"][key])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("theme_json")
    args = ap.parse_args()
    problems = validate(load(args.theme_json))
    if problems:
        print("\n".join("✗ " + p for p in problems))
        raise SystemExit(1)
    print("✓ тема годна")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Создать themes/example.json**

Нейтральная тема: системные шрифты, серо-синяя гамма, безличные подписи. Личный стиль автора сюда не попадает.

```json
{
  "формат": { "ширина": 1080, "высота": 1350, "масштаб_рендера": 2 },
  "фоны": {
    "тёмный":  { "тип": "radial", "стопы": ["#2A2A33", "#0B0B0F"] },
    "светлый": { "тип": "radial", "стопы": ["#FFFFFF", "#E8E8EE"] }
  },
  "цвета": {
    "заголовок_обложки": "#7A9CD6",
    "акцент": "#D08A5C",
    "текст_тела": "#333355",
    "текст_на_тёмном": "#FFFFFF",
    "должность": "#ADADAD",
    "бейдж_на_тёмном": "#E8E7EB",
    "бейдж_кружок_на_светлом": "#333355",
    "бейдж_текст_на_светлом": "#F7F6FF"
  },
  "шрифты": {
    "файлы": { "oswald": "fonts/Oswald.ttf", "montserrat": "fonts/Montserrat.ttf" },
    "роли": {
      "заголовок_обложки":    { "семейство": "Oswald", "вес": 700 },
      "подзаголовок_обложки": { "семейство": "Oswald", "вес": 700 },
      "текст_тела":           { "семейство": "Montserrat", "вес": 500 },
      "выделение_тела":       { "семейство": "Montserrat", "вес": 700 },
      "заголовок_списка":     { "семейство": "Montserrat", "вес": 800 },
      "подпись_имя":          { "семейство": "Montserrat", "вес": 600 },
      "подпись_должность":    { "семейство": "Montserrat", "вес": 400 },
      "бейдж":                { "семейство": "Montserrat", "вес": 300 }
    }
  },
  "ступени": {
    "обложка_заголовок": [200, 150, 110],
    "обложка_подзаголовок": [56, 48, 40],
    "тело": [60, 52, 44],
    "тело_список": [42, 37, 32],
    "cta": [50, 44, 38]
  },
  "ассеты": { "спарк": "assets/spark.svg" },
  "обвязка": {
    "IG": {
      "аватар": "assets/avatar.png",
      "подпись": ["@your_handle"],
      "позиции": {
        "обложка":     { "бейдж": "верх-центр", "подпись": "низ-лево" },
        "тело":        { "бейдж": "низ-право",  "подпись": "низ-лево" },
        "тело-список": { "бейдж": "низ-право",  "подпись": "низ-лево" },
        "CTA":         { "бейдж": "нет",        "подпись": "верх-центр" }
      }
    },
    "LI": {
      "аватар": "assets/avatar.png",
      "подпись": ["Your Name", "Your Title"],
      "позиции": {
        "обложка":     { "бейдж": "верх-центр", "подпись": "низ-центр" },
        "тело":        { "бейдж": "верх-центр", "подпись": "низ-центр" },
        "тело-список": { "бейдж": "верх-центр", "подпись": "низ-центр" },
        "CTA":         { "бейдж": "нет",        "подпись": "верх-центр" }
      }
    }
  }
}
```

- [ ] **Step 5: Запустить тесты**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_theme.py -v`
Expected: PASS, 11 тестов

- [ ] **Step 6: Коммит**

```bash
git add skills/carousel-render/scripts/theme.py skills/carousel-render/themes/ skills/carousel-render/tests/test_theme.py
git commit -m "carousel-render: тема — загрузка, валидация, платформенная обвязка"
```

---

## Task 3: Инлайн-разметка текста

**Files:**
- Create: `skills/carousel-render/scripts/markup.py`
- Create: `skills/carousel-render/tests/test_markup.py`

**Interfaces:**
- Consumes: ничего
- Produces:
  - `markup.escape(text: str) -> str`
  - `markup.inline(text: str) -> str` — экранирование + `**…**` → `<b class="акцент">…</b>` + `\n` → `<br>`
  - `markup.ARROW: str` = `'<span class="нить">⇢</span>'`
  - `markup.with_thread(html: str) -> str`

- [ ] **Step 1: Написать падающий тест**

```python
# skills/carousel-render/tests/test_markup.py
import markup


def test_escape_kills_tags():
    assert markup.escape("<script>x</script>") == "&lt;script&gt;x&lt;/script&gt;"


def test_escape_handles_ampersand():
    assert markup.escape("Тим & Ко") == "Тим &amp; Ко"


def test_inline_wraps_accent():
    assert markup.inline("код и **замолчит**.") == 'код и <b class="акцент">замолчит</b>.'


def test_inline_handles_several_accents():
    got = markup.inline("У **Claude** есть **ADHD**")
    assert got == 'У <b class="акцент">Claude</b> есть <b class="акцент">ADHD</b>'


def test_inline_is_non_greedy():
    """Два отдельных выделения, а не одно на всю строку."""
    got = markup.inline("**раз** между **два**")
    assert got.count("<b") == 2
    assert "между" not in got.split("<b")[1]


def test_inline_newline_becomes_br():
    assert markup.inline("Агент.\nХарнес.") == "Агент.<br>Харнес."


def test_inline_escapes_before_markup():
    """Текст пользователя не должен протаскивать разметку."""
    got = markup.inline("**<b>злой</b>**")
    assert got == '<b class="акцент">&lt;b&gt;злой&lt;/b&gt;</b>'


def test_inline_leaves_lone_asterisks():
    assert markup.inline("5 * 3 = 15") == "5 * 3 = 15"


def test_inline_leaves_unclosed_marker():
    assert markup.inline("**не закрыл") == "**не закрыл"


def test_with_thread_appends_arrow():
    got = markup.with_thread("Первая её часть")
    assert got.endswith(markup.ARROW)
    assert "Первая её часть" in got


def test_arrow_is_element_not_character():
    """Стрелка — элемент со своим классом, иначе её не стилизовать."""
    assert 'class="нить"' in markup.ARROW
```

- [ ] **Step 2: Запустить, убедиться что падает**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_markup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'markup'`

- [ ] **Step 3: Написать markup.py**

```python
#!/usr/bin/env python3
"""Инлайн-разметка текста слайда → HTML. Только stdlib.

Маркер один — `**…**`, а смысл ему подставляет лейаут: в теле это жирное
начертание, на обложке акцентный цвет. Автору не надо помнить, где какой
цвет: он пишет «выделить».
"""
import html
import re

ACCENT_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
ARROW = '<span class="нить">⇢</span>'


def escape(text):
    """HTML-экранирование. Текст автора не должен протаскивать разметку."""
    return html.escape(text, quote=False)


def inline(text):
    """Экранирует, затем разворачивает `**…**` и переводы строк.

    Порядок важен: сначала экранирование, потом наша разметка — иначе
    экранирование съело бы теги, которые мы сами же и поставили.
    """
    safe = escape(text)
    marked = ACCENT_RE.sub(r'<b class="акцент">\1</b>', safe)
    return marked.replace("\n", "<br>")


def with_thread(html_text):
    """Вешает стрелку-нить в конец. Приём «разрез фразы через свайп»."""
    return f"{html_text} {ARROW}"
```

- [ ] **Step 4: Запустить тесты**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_markup.py -v`
Expected: PASS, 11 тестов

- [ ] **Step 5: Коммит**

```bash
git add skills/carousel-render/scripts/markup.py skills/carousel-render/tests/test_markup.py
git commit -m "carousel-render: инлайн-разметка — акцент, переносы, нить"
```

---

## Task 4: Сборка HTML и лейаут обложки

**Files:**
- Create: `skills/carousel-render/scripts/build_html.py`
- Create: `skills/carousel-render/layouts/base.css`
- Create: `skills/carousel-render/layouts/cover.css`
- Create: `skills/carousel-render/tests/test_build_html.py`

**Interfaces:**
- Consumes: `theme.load`, `theme.binding`, `theme.steps` (Task 2); `markup.inline`, `markup.with_thread` (Task 3)
- Produces:
  - `build_html.data_uri(path: Path) -> str`
  - `build_html.font_css(data: dict) -> str`
  - `build_html.css_vars(data: dict, sizes: dict) -> str`
  - `build_html.layout_css(layout: str) -> str`
  - `build_html.build(slide: dict, data: dict, platform: str, sizes: dict, base_dir: Path) -> str`
  - `build_html.MEASURE_JS: str`

`sizes` — словарь выбранных кеглей, например `{"заголовок": 200, "подзаголовок": 56}`. Его считает `fit.py` (Task 9); до тех пор передаётся первая ступень.

- [ ] **Step 1: Написать падающий тест**

```python
# skills/carousel-render/tests/test_build_html.py
import base64
from pathlib import Path

import pytest

import build_html
import theme


@pytest.fixture
def data(theme_file):
    return theme.load(theme_file)


def test_data_uri_encodes_png(theme_dir):
    uri = build_html.data_uri(theme_dir / "assets" / "avatar-ig.png")
    assert uri.startswith("data:image/png;base64,")
    payload = uri.split(",", 1)[1]
    assert base64.b64decode(payload) == b"\x89PNG\r\n\x1a\nfake"


def test_data_uri_picks_svg_mime(theme_dir):
    uri = build_html.data_uri(theme_dir / "assets" / "spark.svg")
    assert uri.startswith("data:image/svg+xml;base64,")


def test_data_uri_picks_font_mime(theme_dir):
    uri = build_html.data_uri(theme_dir / "fonts" / "Oswald.ttf")
    assert uri.startswith("data:font/ttf;base64,")


def test_font_css_embeds_both_families(data):
    css = build_html.font_css(data)
    assert css.count("@font-face") == 2
    assert "Oswald" in css and "Montserrat" in css
    assert "data:font/ttf;base64," in css
    assert "http" not in css


def test_font_css_declares_weight_range(data):
    """Вариативный шрифт: один файл на все веса."""
    assert "font-weight: 200 900" in build_html.font_css(data)


def test_css_vars_exposes_brand_colors(data):
    css = build_html.css_vars(data, {"заголовок": 200})
    assert "--акцент: #D97757" in css
    assert "--текст-тела: #33336F" in css
    assert "--заголовок: 200px" in css


def test_build_is_self_contained(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка",
             "заголовок": "Агент.\nХарнес.\nLoop.",
             "подзаголовок": "Звучит как высшая математика."}
    got = build_html.build(slide, data, "LI",
                           {"заголовок": 200, "подзаголовок": 56}, theme_dir)
    assert "<link" not in got
    assert 'src="http' not in got
    assert "url(http" not in got


def test_build_renders_forced_line_breaks(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Агент.\nХарнес."}
    got = build_html.build(slide, data, "LI", {"заголовок": 200}, theme_dir)
    assert "Агент.<br>Харнес." in got


def test_build_applies_accent_on_cover(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Я отдал **Claude**"}
    got = build_html.build(slide, data, "LI", {"заголовок": 150}, theme_dir)
    assert '<b class="акцент">Claude</b>' in got


def test_build_puts_li_signature_in_two_lines(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Тест"}
    got = build_html.build(slide, data, "LI", {"заголовок": 200}, theme_dir)
    assert "Artem Volkov" in got
    assert "AI-Developer &amp; Content Creator" in got


def test_build_puts_ig_signature_in_one_line(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Тест"}
    got = build_html.build(slide, data, "IG", {"заголовок": 200}, theme_dir)
    assert "@ai_rtem" in got
    assert "AI-Developer" not in got


def test_build_includes_measure_js(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Тест"}
    got = build_html.build(slide, data, "LI", {"заголовок": 200}, theme_dir)
    assert "data-overflow" in got


def test_build_rejects_unknown_layout(data, theme_dir):
    with pytest.raises(ValueError, match="лейаут"):
        build_html.build({"№": 1, "лейаут": "карусель-мечты"}, data, "LI", {}, theme_dir)
```

- [ ] **Step 2: Запустить, убедиться что падает**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_build_html.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_html'`

- [ ] **Step 3: Написать base.css**

```css
/* skills/carousel-render/layouts/base.css
   Общее для всех карточек: сброс, размер, фоны, обвязка.
   Значения приходят из темы через CSS-переменные — тут только композиция. */

* { margin: 0; padding: 0; box-sizing: border-box; }

html, body {
  width: var(--ширина);
  height: var(--высота);
  overflow: hidden;
}

.карточка {
  position: relative;
  width: var(--ширина);
  height: var(--высота);
  padding: 80px 72px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.карточка.тёмная {
  background: radial-gradient(circle at 50% 40%, var(--фон-тёмный-1), var(--фон-тёмный-2));
  color: var(--текст-на-тёмном);
}

.карточка.светлая {
  background: radial-gradient(circle at 50% 40%, var(--фон-светлый-1), var(--фон-светлый-2));
  color: var(--текст-тела);
}

/* Зона содержимого: всё, что меряется на переполнение. */
.содержимое {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 0;
}

/* — Обвязка: бейдж «ЛИСТАЙ» — */
.бейдж {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 18px;
  font-family: Montserrat, sans-serif;
  font-weight: var(--бейдж-вес);
  font-size: 34px;
  letter-spacing: 0.08em;
}
.бейдж.верх-центр { top: 56px; left: 50%; transform: translateX(-50%); }
.бейдж.низ-право  { right: 72px; bottom: 64px; }
.бейдж.нет        { display: none; }

.бейдж .кружок {
  width: 62px; height: 62px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 30px; line-height: 1;
}
.тёмная .бейдж            { color: var(--бейдж-на-тёмном); }
.тёмная .бейдж .кружок    { background: var(--бейдж-на-тёмном); color: #111; }
.светлая .бейдж           { color: var(--бейдж-кружок-на-светлом); }
.светлая .бейдж .кружок   { background: var(--бейдж-кружок-на-светлом);
                            color: var(--бейдж-текст-на-светлом); }

/* — Обвязка: подпись с аватаркой — */
.подпись {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 22px;
  font-family: Montserrat, sans-serif;
}
.подпись.низ-центр  { bottom: 60px; left: 50%; transform: translateX(-50%); }
.подпись.низ-лево   { bottom: 60px; left: 72px; }
.подпись.верх-центр { top: 150px; left: 50%; transform: translateX(-50%); }
.подпись.нет        { display: none; }

.подпись img {
  width: 78px; height: 78px; border-radius: 50%; object-fit: cover;
}
.подпись .имя {
  font-weight: var(--подпись-имя-вес);
  font-size: 44px;
  line-height: 1.1;
}
.подпись .должность {
  font-weight: var(--подпись-должность-вес);
  font-size: 26px;
  color: var(--должность);
}

.нить { white-space: nowrap; }
```

- [ ] **Step 4: Написать cover.css**

```css
/* skills/carousel-render/layouts/cover.css
   Обложка: крупный Oswald, три вида — текст, декор, фото на весь кадр. */

.обложка .содержимое { justify-content: center; text-align: center; }

.обложка .заголовок {
  font-family: Oswald, sans-serif;
  font-weight: var(--заголовок-обложки-вес);
  font-size: var(--заголовок);
  line-height: 0.95;
  letter-spacing: -0.02em;
  text-transform: uppercase;
  color: var(--заголовок-обложки);
}

.обложка .подзаголовок {
  font-family: Oswald, sans-serif;
  font-weight: var(--подзаголовок-обложки-вес);
  font-size: var(--подзаголовок);
  line-height: 1.15;
  text-transform: uppercase;
  color: var(--текст-на-тёмном);
  margin-top: 48px;
}

.обложка .акцент { color: var(--акцент); font-weight: inherit; }

/* Вид «декор»: спарк в свободном верхнем углу, под текстом по слою. */
.обложка .спарк {
  position: absolute;
  top: 90px; right: 60px;
  width: 340px; height: 340px;
  z-index: 0;
}
.обложка .содержимое { position: relative; z-index: 1; }

/* Вид «фото»: снимок на весь кадр, текст внизу поверх затемнения. */
.обложка.фото { padding: 0; }
.обложка.фото .фон {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  object-fit: cover;
  z-index: 0;
}
.обложка.фото .затемнение {
  position: absolute; inset: 0; z-index: 1;
  background: linear-gradient(to bottom, transparent 40%, rgba(0,0,0,0.72) 88%);
}
.обложка.фото .содержимое {
  position: relative; z-index: 2;
  justify-content: flex-end;
  padding: 80px 72px 150px;
}
.обложка.фото .заголовок {
  color: var(--текст-на-тёмном);
  font-size: var(--подзаголовок);
  line-height: 1.12;
}
.обложка.фото .низ {
  font-family: Oswald, sans-serif;
  font-size: 32px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-top: 44px;
  opacity: 0.9;
}
```

- [ ] **Step 5: Написать build_html.py**

```python
#!/usr/bin/env python3
"""slides.json + тема → самодостаточный HTML одной карточки. Только stdlib.

Самодостаточный значит буквально: шрифты, картинки и стили встроены как
data: URI. Ни одного внешнего запроса и ни одного обращения к file:// из
документа — это снимает и блокировку шрифтов на file://, и зависимость
результата от порядка загрузки.
"""
import argparse
import base64
import json
from pathlib import Path

import markup
import theme as theme_mod

LAYOUTS_DIR = Path(__file__).parent.parent / "layouts"

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".svg": "image/svg+xml",
        ".ttf": "font/ttf", ".otf": "font/otf", ".woff2": "font/woff2"}

CSS_BY_LAYOUT = {"обложка": "cover.css", "тело": "body.css",
                 "тело-список": "body-list.css", "CTA": "cta.css"}

DARK_LAYOUTS = {"обложка", "CTA"}

MEASURE_JS = """
<script>
  window.addEventListener('load', function () {
    var box = document.querySelector('.содержимое');
    var over = Math.max(0, box.scrollHeight - box.clientHeight);
    var probe = box.querySelector('*');
    var lh = probe ? parseFloat(getComputedStyle(probe).lineHeight) || 0 : 0;
    document.body.dataset.overflow = String(Math.round(over));
    document.body.dataset.lineHeight = String(Math.round(lh));
  });
</script>
"""


def data_uri(path):
    """Файл → data: URI. Тип берётся по расширению."""
    path = Path(path)
    mime = MIME.get(path.suffix.lower(), "application/octet-stream")
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def font_css(data):
    """@font-face на оба семейства со встроенными файлами."""
    blocks = []
    for family, path in data["шрифты"]["файлы"].items():
        blocks.append(
            "@font-face {\n"
            f"  font-family: '{family.capitalize()}';\n"
            f"  src: url({data_uri(path)}) format('truetype');\n"
            "  font-weight: 200 900;\n"
            "  font-style: normal;\n"
            "}"
        )
    return "\n".join(blocks)


def css_vars(data, sizes):
    """Тема + выбранные кегли → блок :root с переменными."""
    colors = data["цвета"]
    fmt = data["формат"]
    roles = data["шрифты"]["роли"]
    lines = [
        f"--ширина: {fmt['ширина']}px;",
        f"--высота: {fmt['высота']}px;",
        f"--фон-тёмный-1: {data['фоны']['тёмный']['стопы'][0]};",
        f"--фон-тёмный-2: {data['фоны']['тёмный']['стопы'][1]};",
        f"--фон-светлый-1: {data['фоны']['светлый']['стопы'][0]};",
        f"--фон-светлый-2: {data['фоны']['светлый']['стопы'][1]};",
    ]
    for name, value in colors.items():
        lines.append(f"--{name.replace('_', '-')}: {value};")
    for name, spec in roles.items():
        lines.append(f"--{name.replace('_', '-')}-вес: {spec['вес']};")
    for name, value in sizes.items():
        lines.append(f"--{name}: {value}px;")
    return ":root {\n  " + "\n  ".join(lines) + "\n}"


def layout_css(layout):
    """base.css + CSS конкретного лейаута."""
    if layout not in CSS_BY_LAYOUT:
        raise ValueError(f"неизвестный лейаут: {layout}")
    base = (LAYOUTS_DIR / "base.css").read_text(encoding="utf-8")
    own = (LAYOUTS_DIR / CSS_BY_LAYOUT[layout]).read_text(encoding="utf-8")
    return base + "\n" + own


def _badge_html(position):
    if position == "нет":
        return ""
    return (f'<div class="бейдж {position}">ЛИСТАЙ'
            f'<span class="кружок">›</span></div>')


def _signature_html(binding, visible):
    if not visible:
        return ""
    lines = binding["подпись"]
    name = markup.escape(lines[0])
    title = f'<div class="должность">{markup.escape(lines[1])}</div>' if len(lines) > 1 else ""
    return (f'<div class="подпись {binding["подпись_позиция"]}">'
            f'<img src="{data_uri(binding["аватар"])}" alt="">'
            f'<div><div class="имя">{name}</div>{title}</div></div>')


def _cover_body(slide, data, base_dir):
    """Содержимое обложки. Виды: текст (по умолчанию), декор, фото."""
    kind = slide.get("вид", "текст")
    title = markup.inline(slide.get("заголовок", ""))
    parts = []

    if kind == "фото":
        photo = base_dir / slide["фото"]
        parts.append(f'<img class="фон" src="{data_uri(photo)}" alt="">')
        parts.append('<div class="затемнение"></div>')
    elif kind == "декор":
        parts.append(f'<img class="спарк" src="{data_uri(data["ассеты"]["спарк"])}" alt="">')

    inner = [f'<div class="заголовок">{title}</div>']
    if slide.get("подзаголовок"):
        inner.append(f'<div class="подзаголовок">{markup.inline(slide["подзаголовок"])}</div>')
    if slide.get("низ"):
        inner.append(f'<div class="низ">{markup.inline(slide["низ"])}</div>')

    parts.append('<div class="содержимое">' + "".join(inner) + "</div>")
    return "".join(parts), kind


def build(slide, data, platform, sizes, base_dir):
    """Собирает полный HTML-документ одной карточки."""
    layout = slide.get("лейаут")
    if layout not in CSS_BY_LAYOUT:
        raise ValueError(f"неизвестный лейаут: {layout}")

    binding = theme_mod.binding(data, platform, layout)
    tone = "тёмная" if layout in DARK_LAYOUTS else "светлая"

    if layout == "обложка":
        body, kind = _cover_body(slide, data, base_dir)
        classes = f"карточка {tone} обложка {kind if kind != 'текст' else ''}".strip()
        # На фото-обложке подпись гасится: автор уже на снимке.
        default_visible = kind != "фото"
    else:
        raise ValueError(f"лейаут {layout} появится в следующих задачах")

    visible = slide.get("подпись", "показать" if default_visible else "скрыть") == "показать"

    return (
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'><style>\n"
        + font_css(data) + "\n" + css_vars(data, sizes) + "\n" + layout_css(layout)
        + "\n</style></head><body>"
        + f'<div class="{classes}">'
        + _badge_html(binding["бейдж"])
        + body
        + _signature_html(binding, visible)
        + "</div>" + MEASURE_JS + "</body></html>"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slides_json")
    ap.add_argument("--theme", required=True)
    ap.add_argument("--slide", type=int, default=1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    spec = json.loads(Path(args.slides_json).read_text(encoding="utf-8"))
    data = theme_mod.load(args.theme)
    slide = next(s for s in spec["слайды"] if s["№"] == args.slide)
    sizes = {"заголовок": theme_mod.steps(data, "обложка_заголовок")[0],
             "подзаголовок": theme_mod.steps(data, "обложка_подзаголовок")[0]}
    html_text = build(slide, data, spec["meta"]["площадка"], sizes,
                      Path(args.slides_json).parent)
    Path(args.out).write_text(html_text, encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Запустить тесты**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_build_html.py -v`
Expected: PASS, 13 тестов

- [ ] **Step 7: Коммит**

```bash
git add skills/carousel-render/scripts/build_html.py skills/carousel-render/layouts/ skills/carousel-render/tests/test_build_html.py
git commit -m "carousel-render: сборка самодостаточного HTML + лейаут обложки"
```

---

## Task 5: Рендер в PNG через headless Chrome

**Files:**
- Create: `skills/carousel-render/scripts/render.py`
- Create: `skills/carousel-render/tests/test_render.py`

**Interfaces:**
- Consumes: ничего из предыдущих задач (работает с готовым HTML-файлом)
- Produces:
  - `render.chrome_cmd(html_path: Path, mode: str, width: int, height: int, scale: int, out: Path | None) -> list[str]`
  - `render.measure(html_path: Path, width: int, height: int) -> dict` с ключами `overflow_px`, `line_height_px`
  - `render.screenshot(html_path: Path, out_png: Path, width: int, height: int, scale: int) -> Path`
  - `render.downscale(png: Path, width: int, height: int) -> Path`
  - `render.parse_overflow(dom: str) -> dict`

- [ ] **Step 1: Написать падающий тест**

```python
# skills/carousel-render/tests/test_render.py
from pathlib import Path

import pytest

import render


def test_chrome_cmd_screenshot_has_scale_and_size(tmp_path):
    cmd = render.chrome_cmd(tmp_path / "s.html", "screenshot", 1080, 1350, 2,
                            tmp_path / "s.png")
    joined = " ".join(cmd)
    assert "--headless" in joined
    assert "--window-size=1080,1350" in joined
    assert "--force-device-scale-factor=2" in joined
    assert "--screenshot=" in joined


def test_chrome_cmd_always_waits_for_fonts(tmp_path):
    """Без virtual-time-budget скриншот снимается до применения @font-face."""
    for mode in ("screenshot", "dom"):
        cmd = render.chrome_cmd(tmp_path / "s.html", mode, 1080, 1350, 1, None)
        assert any(a.startswith("--virtual-time-budget=") for a in cmd)


def test_chrome_cmd_dom_mode_dumps_and_scales_one(tmp_path):
    """Замер идёт в 1×: он нужен для чисел, а не для картинки."""
    cmd = render.chrome_cmd(tmp_path / "s.html", "dom", 1080, 1350, 1, None)
    assert "--dump-dom" in cmd
    assert "--force-device-scale-factor=1" in " ".join(cmd)


def test_chrome_cmd_uses_file_url(tmp_path):
    html = tmp_path / "s.html"
    cmd = render.chrome_cmd(html, "dom", 1080, 1350, 1, None)
    assert cmd[-1].startswith("file:///")
    assert str(html) in cmd[-1]


def test_parse_overflow_reads_dataset():
    dom = '<html><body data-overflow="42" data-line-height="70">x</body></html>'
    assert render.parse_overflow(dom) == {"overflow_px": 42, "line_height_px": 70}


def test_parse_overflow_defaults_to_zero():
    assert render.parse_overflow("<html><body>нет данных</body></html>") == {
        "overflow_px": 0, "line_height_px": 0}


def test_parse_overflow_survives_attribute_order():
    dom = '<body data-line-height="55" class="x" data-overflow="7">'
    assert render.parse_overflow(dom)["overflow_px"] == 7


@pytest.mark.integration
def test_screenshot_produces_exact_size(tmp_path):
    """Живой прогон Chrome: размер должен быть ровно 1080×1350."""
    html = tmp_path / "s.html"
    html.write_text(
        "<!doctype html><html><head><style>"
        "html,body{margin:0;width:1080px;height:1350px;background:#222147}"
        "</style></head><body><div class='содержимое'>тест</div></body></html>",
        encoding="utf-8")
    png = render.screenshot(html, tmp_path / "s.png", 1080, 1350, 2)
    render.downscale(png, 1080, 1350)
    assert png.exists()
    assert render.png_size(png) == (1080, 1350)
```

- [ ] **Step 2: Запустить, убедиться что падает**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_render.py -v -m "not integration"`
Expected: FAIL — `ModuleNotFoundError: No module named 'render'`

- [ ] **Step 3: Написать render.py**

```python
#!/usr/bin/env python3
"""HTML → PNG через headless Chrome, плюс замер переполнения. Только stdlib.

Два прохода. Замер (`--dump-dom`) идёт в 1× и читает то, что страница сама
записала в data-атрибуты body. Съёмка (`--screenshot`) идёт в 2× ради
чистоты текста, затем `sips` ужимает до 1080×1350.
"""
import argparse
import re
import struct
import subprocess
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
VIRTUAL_TIME_MS = 2000

OVERFLOW_RE = re.compile(r'data-overflow="(\d+)"')
LINE_HEIGHT_RE = re.compile(r'data-line-height="(\d+)"')


def chrome_cmd(html_path, mode, width, height, scale, out):
    """Команда Chrome. mode: 'screenshot' | 'dom'."""
    cmd = [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
           f"--window-size={width},{height}",
           f"--force-device-scale-factor={scale if mode == 'screenshot' else 1}",
           f"--virtual-time-budget={VIRTUAL_TIME_MS}"]
    if mode == "screenshot":
        cmd.append(f"--screenshot={out}")
    else:
        cmd.append("--dump-dom")
    cmd.append(Path(html_path).resolve().as_uri())
    return cmd


def parse_overflow(dom):
    """Достаёт замеры, которые страница положила в data-атрибуты."""
    over = OVERFLOW_RE.search(dom)
    line = LINE_HEIGHT_RE.search(dom)
    return {"overflow_px": int(over.group(1)) if over else 0,
            "line_height_px": int(line.group(1)) if line else 0}


def measure(html_path, width, height):
    """Прогоняет страницу и возвращает переполнение в пикселях."""
    out = subprocess.run(chrome_cmd(html_path, "dom", width, height, 1, None),
                         capture_output=True, text=True, check=True).stdout
    return parse_overflow(out)


def screenshot(html_path, out_png, width, height, scale):
    """Снимает карточку в scale×. Возвращает путь к PNG."""
    subprocess.run(chrome_cmd(html_path, "screenshot", width, height, scale, out_png),
                   capture_output=True, check=True)
    return Path(out_png)


def downscale(png, width, height):
    """Ужимает до целевого размера. sips принимает высоту, потом ширину."""
    subprocess.run(["sips", "-z", str(height), str(width), str(png)],
                   capture_output=True, check=True)
    return Path(png)


def png_size(png):
    """Ширина и высота PNG из заголовка IHDR. Без сторонних библиотек."""
    data = Path(png).read_bytes()[16:24]
    return struct.unpack(">II", data)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html")
    ap.add_argument("--out")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1350)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--measure", action="store_true")
    args = ap.parse_args()

    if args.measure:
        print(measure(args.html, args.width, args.height))
        return
    png = screenshot(args.html, args.out, args.width, args.height, args.scale)
    downscale(png, args.width, args.height)
    print(f"{png} {png_size(png)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Запустить юнит-тесты**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_render.py -v -m "not integration"`
Expected: PASS, 7 тестов

- [ ] **Step 5: Запустить интеграционный тест на живом Chrome**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_render.py -v -m integration`
Expected: PASS — PNG ровно 1080×1350

Если падает по размеру: проверить, что `--hide-scrollbars` на месте и в CSS нет полей на `body`.

- [ ] **Step 6: Зарегистрировать маркер integration**

```ini
# skills/carousel-render/pytest.ini
[pytest]
markers =
    integration: требует живого Chrome и sips
```

- [ ] **Step 7: Первая живая карточка глазами**

```bash
cd skills/carousel-render
python3 scripts/build_html.py <путь>/slides.json --theme "$THEME_PATH" --slide 1 --out /tmp/c1.html
python3 scripts/render.py /tmp/c1.html --out /tmp/c1.png
open /tmp/c1.png
```

Проверить главное: **шрифт не засечный**. Если засечный — значит `@font-face` не применился: смотреть, что файлы шрифтов реально встроились (`grep -c "data:font" /tmp/c1.html` должен дать 1) и что `--virtual-time-budget` на месте.

- [ ] **Step 8: Коммит**

```bash
git add skills/carousel-render/scripts/render.py skills/carousel-render/tests/test_render.py skills/carousel-render/pytest.ini
git commit -m "carousel-render: рендер через headless Chrome, замер переполнения, ужатие sips"
```

---

## Task 6: Лейауты тела и списка

**Files:**
- Create: `skills/carousel-render/layouts/body.css`
- Create: `skills/carousel-render/layouts/body-list.css`
- Modify: `skills/carousel-render/scripts/build_html.py`
- Modify: `skills/carousel-render/tests/test_build_html.py`

**Interfaces:**
- Consumes: `build_html.build` (Task 4), `markup.inline`, `markup.with_thread` (Task 3)
- Produces: `build_html._body_body(slide, data) -> str`, `build_html._list_body(slide, data) -> str`; `build` начинает принимать `лейаут` ∈ `{"обложка", "тело", "тело-список"}`

- [ ] **Step 1: Написать падающий тест**

```python
# добавить в skills/carousel-render/tests/test_build_html.py

def test_body_renders_each_block_as_paragraph(data, theme_dir):
    slide = {"№": 2, "лейаут": "тело",
             "блоки": ["Первый абзац.", "Второй абзац."]}
    got = build_html.build(slide, data, "LI", {"тело": 60}, theme_dir)
    assert got.count('class="блок"') == 2
    assert "Первый абзац." in got and "Второй абзац." in got


def test_body_bold_uses_accent_class(data, theme_dir):
    slide = {"№": 2, "лейаут": "тело", "блоки": ["код и **замолчит**."]}
    got = build_html.build(slide, data, "LI", {"тело": 60}, theme_dir)
    assert '<b class="акцент">замолчит</b>' in got


def test_body_thread_arrow_only_on_last_block(data, theme_dir):
    slide = {"№": 2, "лейаут": "тело",
             "блоки": ["Раз.", "Два.", "Первая её часть"], "нить": True}
    got = build_html.build(slide, data, "LI", {"тело": 60}, theme_dir)
    assert got.count('class="нить"') == 1
    tail = got.split("Первая её часть")[1]
    assert 'class="нить"' in tail.split("</div>")[0]


def test_body_without_thread_has_no_arrow(data, theme_dir):
    slide = {"№": 2, "лейаут": "тело", "блоки": ["Раз."]}
    got = build_html.build(slide, data, "LI", {"тело": 60}, theme_dir)
    assert 'class="нить"' not in got


def test_body_is_light_card(data, theme_dir):
    slide = {"№": 2, "лейаут": "тело", "блоки": ["Раз."]}
    got = build_html.build(slide, data, "LI", {"тело": 60}, theme_dir)
    assert "карточка светлая" in got


def test_list_renders_title_subtitle_items_footer(data, theme_dir):
    slide = {"№": 4, "лейаут": "тело-список",
             "заголовок": "Разработка",
             "подзаголовок": "Проект не разваливается на пятой правке.",
             "пункты": ["**superpowers** — не бросишь на середине",
                        "**context7** — код заводится с первого раза"],
             "подвал": "→ Твой отдел разработки"}
    got = build_html.build(slide, data, "IG", {"тело_список": 42}, theme_dir)
    assert "Разработка" in got
    assert "не разваливается" in got
    assert got.count('class="пункт"') == 2
    assert '<b class="акцент">superpowers</b>' in got
    assert "Твой отдел разработки" in got
    assert 'class="подвал"' in got


def test_list_without_footer_omits_it(data, theme_dir):
    slide = {"№": 4, "лейаут": "тело-список", "заголовок": "Разработка",
             "пункты": ["**раз** — два"]}
    got = build_html.build(slide, data, "IG", {"тело_список": 42}, theme_dir)
    assert 'class="подвал"' not in got


def test_list_uses_ig_badge_bottom_right(data, theme_dir):
    slide = {"№": 4, "лейаут": "тело-список", "заголовок": "Р", "пункты": ["**а** — б"]}
    got = build_html.build(slide, data, "IG", {"тело_список": 42}, theme_dir)
    assert "бейдж низ-право" in got
    assert "подпись низ-лево" in got
```

- [ ] **Step 2: Запустить, убедиться что падает**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_build_html.py -k "body or list" -v`
Expected: FAIL — `ValueError: лейаут тело появится в следующих задачах`

- [ ] **Step 3: Написать body.css**

```css
/* skills/carousel-render/layouts/body.css
   Тело: светлая карточка, абзацы Montserrat, блок по центру вертикали. */

.тело .содержимое {
  justify-content: center;
  gap: 44px;
}

.тело .блок {
  font-family: Montserrat, sans-serif;
  font-weight: var(--текст-тела-вес);
  font-size: var(--тело);
  line-height: 1.28;
  color: var(--текст-тела);
}

.тело .блок .акцент {
  font-weight: var(--выделение-тела-вес);
  color: inherit;
}

.тело .нить { letter-spacing: 0.05em; }
```

- [ ] **Step 4: Написать body-list.css**

```css
/* skills/carousel-render/layouts/body-list.css
   Тело-список: заголовок, подзаголовок-боль, пункты, подвал курсивом.
   Отдельный лейаут, а не абзацный: свой ритм отступов и свой подвал. */

.тело-список .содержимое {
  justify-content: flex-start;
  padding-top: 40px;
}

.тело-список .заголовок {
  font-family: Montserrat, sans-serif;
  font-weight: var(--заголовок-списка-вес);
  font-size: calc(var(--тело_список) * 1.55);
  line-height: 1.1;
  color: var(--текст-тела);
}

.тело-список .подзаголовок {
  font-family: Montserrat, sans-serif;
  font-weight: var(--выделение-тела-вес);
  font-size: calc(var(--тело_список) * 1.18);
  line-height: 1.2;
  color: var(--текст-тела);
  margin-top: 10px;
}

.тело-список .пункты {
  margin-top: 56px;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.тело-список .пункт {
  font-family: Montserrat, sans-serif;
  font-weight: var(--текст-тела-вес);
  font-size: var(--тело_список);
  line-height: 1.26;
  color: var(--текст-тела);
}

.тело-список .пункт .акцент {
  font-weight: var(--заголовок-списка-вес);
  color: inherit;
}

.тело-список .подвал {
  margin-top: 48px;
  font-family: Montserrat, sans-serif;
  font-style: italic;
  font-weight: var(--выделение-тела-вес);
  font-size: var(--тело_список);
  color: var(--текст-тела);
}
```

- [ ] **Step 5: Дописать build_html.py**

Заменить ветку `else: raise ValueError(f"лейаут {layout} появится в следующих задачах")` в `build` на разбор по лейаутам и добавить две функции:

```python
def _body_body(slide, data):
    """Абзацы тела. Нить вешается только на последний блок."""
    blocks = slide.get("блоки", [])
    rendered = []
    for i, text in enumerate(blocks):
        html_text = markup.inline(text)
        if slide.get("нить") and i == len(blocks) - 1:
            html_text = markup.with_thread(html_text)
        rendered.append(f'<div class="блок">{html_text}</div>')
    return '<div class="содержимое">' + "".join(rendered) + "</div>"


def _list_body(slide, data):
    """Заголовок → подзаголовок-боль → пункты → подвал курсивом."""
    parts = [f'<div class="заголовок">{markup.inline(slide.get("заголовок", ""))}</div>']
    if slide.get("подзаголовок"):
        parts.append(f'<div class="подзаголовок">{markup.inline(slide["подзаголовок"])}</div>')

    items = "".join(f'<div class="пункт">{markup.inline(x)}</div>'
                    for x in slide.get("пункты", []))
    parts.append(f'<div class="пункты">{items}</div>')

    if slide.get("подвал"):
        parts.append(f'<div class="подвал">{markup.inline(slide["подвал"])}</div>')
    return '<div class="содержимое">' + "".join(parts) + "</div>"
```

И в `build` вместо прежней развилки:

```python
    if layout == "обложка":
        body, kind = _cover_body(slide, data, base_dir)
        classes = f"карточка {tone} обложка {kind if kind != 'текст' else ''}".strip()
        default_visible = kind != "фото"
    elif layout == "тело":
        body = _body_body(slide, data)
        classes = f"карточка {tone} тело"
        default_visible = True
    elif layout == "тело-список":
        body = _list_body(slide, data)
        classes = f"карточка {tone} тело-список"
        default_visible = True
    else:
        raise ValueError(f"лейаут {layout} появится в следующей задаче")
```

- [ ] **Step 6: Запустить тесты**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_build_html.py -v`
Expected: PASS, 21 тест

- [ ] **Step 7: Коммит**

```bash
git add skills/carousel-render/layouts/ skills/carousel-render/scripts/build_html.py skills/carousel-render/tests/test_build_html.py
git commit -m "carousel-render: лейауты тела и тела-списка"
```

---

## Task 7: Лейаут CTA

**Files:**
- Create: `skills/carousel-render/layouts/cta.css`
- Modify: `skills/carousel-render/scripts/build_html.py`
- Modify: `skills/carousel-render/tests/test_build_html.py`

**Interfaces:**
- Consumes: `build_html.build` (Task 6)
- Produces: `build_html._cta_body(slide, data) -> str`; `build` принимает все четыре лейаута из `theme.LAYOUTS`

- [ ] **Step 1: Написать падающий тест**

```python
# добавить в skills/carousel-render/tests/test_build_html.py

def test_cta_is_dark_card(data, theme_dir):
    slide = {"№": 7, "лейаут": "CTA", "блоки": ["Подписывайся."]}
    got = build_html.build(slide, data, "LI", {"cta": 50}, theme_dir)
    assert "карточка тёмная" in got


def test_cta_has_no_badge(data, theme_dir):
    slide = {"№": 7, "лейаут": "CTA", "блоки": ["Подписывайся."]}
    got = build_html.build(slide, data, "LI", {"cta": 50}, theme_dir)
    assert "ЛИСТАЙ" not in got


def test_cta_signature_sits_on_top(data, theme_dir):
    """На CTA подпись крупная и сверху, а не мелкая внизу."""
    slide = {"№": 7, "лейаут": "CTA", "блоки": ["Подписывайся."]}
    got = build_html.build(slide, data, "LI", {"cta": 50}, theme_dir)
    assert "подпись верх-центр" in got
    assert "Artem Volkov" in got


def test_cta_renders_all_blocks(data, theme_dir):
    slide = {"№": 7, "лейаут": "CTA",
             "блоки": ["Хочешь разбираться в AI — подписывайся.",
                       "Разбираю по-честному."]}
    got = build_html.build(slide, data, "LI", {"cta": 50}, theme_dir)
    assert got.count('class="блок"') == 2


def test_all_layouts_build(data, theme_dir):
    """Словарь лейаутов закрыт и целиком поддержан."""
    import theme as theme_mod
    samples = {
        "обложка": {"заголовок": "Т"},
        "тело": {"блоки": ["Т"]},
        "тело-список": {"заголовок": "Т", "пункты": ["**а** — б"]},
        "CTA": {"блоки": ["Т"]},
    }
    for layout in theme_mod.LAYOUTS:
        slide = {"№": 1, "лейаут": layout, **samples[layout]}
        assert build_html.build(slide, data, "LI", {}, theme_dir).startswith("<!doctype")
```

- [ ] **Step 2: Запустить, убедиться что падает**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_build_html.py -k cta -v`
Expected: FAIL — `ValueError: лейаут CTA появится в следующей задаче`

- [ ] **Step 3: Написать cta.css**

```css
/* skills/carousel-render/layouts/cta.css
   CTA: тёмная карточка, крупная подпись сверху, текст по центру, без бейджа. */

.CTA .содержимое {
  justify-content: center;
  text-align: center;
  gap: 40px;
  padding-top: 120px;
}

.CTA .блок {
  font-family: Montserrat, sans-serif;
  font-weight: var(--выделение-тела-вес);
  font-size: var(--cta);
  line-height: 1.3;
  color: var(--текст-на-тёмном);
}

.CTA .блок .акцент { color: var(--акцент); }

/* Подпись на CTA — герой карточки, а не мелкая сноска. */
.CTA .подпись img       { width: 150px; height: 150px; }
.CTA .подпись .имя      { font-size: 58px; }
.CTA .подпись .должность { font-size: 30px; }
```

- [ ] **Step 4: Дописать build_html.py**

Добавить функцию:

```python
def _cta_body(slide, data):
    """Текст призыва. Подпись рисуется отдельно, обвязкой."""
    blocks = "".join(f'<div class="блок">{markup.inline(x)}</div>'
                     for x in slide.get("блоки", []))
    return '<div class="содержимое">' + blocks + "</div>"
```

И заменить ветку `else` в `build`:

```python
    elif layout == "CTA":
        body = _cta_body(slide, data)
        classes = f"карточка {tone} CTA"
        default_visible = True
    else:
        raise ValueError(f"неизвестный лейаут: {layout}")
```

- [ ] **Step 5: Запустить все тесты**

Run: `cd skills/carousel-render && python3 -m pytest tests/ -v -m "not integration"`
Expected: PASS, 64 теста (9 доктор + 11 тема + 11 разметка + 26 сборка HTML + 7 рендер)

- [ ] **Step 6: Коммит**

```bash
git add skills/carousel-render/layouts/cta.css skills/carousel-render/scripts/build_html.py skills/carousel-render/tests/test_build_html.py
git commit -m "carousel-render: лейаут CTA, словарь лейаутов закрыт"
```

---

## Task 8: Подбор ступени кегля и контроль переполнения

**Files:**
- Create: `skills/carousel-render/scripts/fit.py`
- Create: `skills/carousel-render/tests/test_fit.py`

**Interfaces:**
- Consumes: `build_html.build` (Task 7), `render.measure` (Task 5), `theme.steps` (Task 2)
- Produces:
  - `fit.SIZE_KEYS: dict[str, tuple[str, ...]]` — какие ключи ступеней нужны лейауту
  - `fit.sizes_for(data: dict, layout: str, index: int) -> dict[str, int]`
  - `fit.shortfall_chars(overflow_px: int, line_height_px: int, chars_per_line: int) -> int`
  - `fit.fit_slide(slide, data, platform, base_dir, tmp_dir) -> dict` с ключами `html` (Path), `ступень` (int), `переполнение` (int), `недобор_символов` (int)

- [ ] **Step 1: Написать падающий тест**

```python
# skills/carousel-render/tests/test_fit.py
import pytest

import fit
import theme


@pytest.fixture
def data(theme_file):
    return theme.load(theme_file)


def test_size_keys_cover_all_layouts():
    import theme as theme_mod
    assert set(fit.SIZE_KEYS) == set(theme_mod.LAYOUTS)


def test_sizes_for_cover_takes_both_keys(data):
    got = fit.sizes_for(data, "обложка", 0)
    assert got == {"заголовок": 200, "подзаголовок": 56}


def test_sizes_for_second_step_is_smaller(data):
    first = fit.sizes_for(data, "обложка", 0)
    second = fit.sizes_for(data, "обложка", 1)
    assert second["заголовок"] < first["заголовок"]


def test_sizes_for_body_list_uses_own_scale(data):
    assert fit.sizes_for(data, "тело-список", 0) == {"тело_список": 42}


def test_sizes_for_index_beyond_range_raises(data):
    with pytest.raises(IndexError):
        fit.sizes_for(data, "тело", 3)


def test_shortfall_zero_when_fits():
    assert fit.shortfall_chars(0, 70, 34) == 0


def test_shortfall_counts_whole_lines():
    """Переполнение в полторы строки — резать надо две строки."""
    assert fit.shortfall_chars(105, 70, 34) == 68


def test_shortfall_rounds_partial_line_up():
    assert fit.shortfall_chars(10, 70, 34) == 34


def test_shortfall_survives_zero_line_height():
    """Не делим на ноль, если замер не удался."""
    assert fit.shortfall_chars(100, 0, 34) == 0


def test_fit_slide_returns_first_step_when_it_fits(data, theme_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(fit.render, "measure",
                        lambda *a, **k: {"overflow_px": 0, "line_height_px": 70})
    slide = {"№": 2, "лейаут": "тело", "блоки": ["Коротко."]}
    got = fit.fit_slide(slide, data, "LI", theme_dir, tmp_path)
    assert got["ступень"] == 0
    assert got["переполнение"] == 0
    assert got["недобор_символов"] == 0
    assert got["html"].exists()


def test_fit_slide_steps_down_until_it_fits(data, theme_dir, tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_measure(*a, **k):
        calls["n"] += 1
        return {"overflow_px": 0 if calls["n"] >= 3 else 200, "line_height_px": 70}

    monkeypatch.setattr(fit.render, "measure", fake_measure)
    slide = {"№": 2, "лейаут": "тело", "блоки": ["Длинно " * 80]}
    got = fit.fit_slide(slide, data, "LI", theme_dir, tmp_path)
    assert got["ступень"] == 2
    assert got["переполнение"] == 0


def test_fit_slide_reports_shortfall_when_no_step_fits(data, theme_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(fit.render, "measure",
                        lambda *a, **k: {"overflow_px": 140, "line_height_px": 70})
    slide = {"№": 4, "лейаут": "тело", "блоки": ["Очень длинно " * 100]}
    got = fit.fit_slide(slide, data, "LI", theme_dir, tmp_path)
    assert got["ступень"] == 2
    assert got["переполнение"] == 140
    assert got["недобор_символов"] > 0
```

- [ ] **Step 2: Запустить, убедиться что падает**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_fit.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fit'`

- [ ] **Step 3: Написать fit.py**

```python
#!/usr/bin/env python3
"""Подбор ступени кегля под объём контента. Только stdlib.

Кегль ходит по конечному числу ступеней, а не подгоняется плавно. Причина
не техническая: плавная подгонка даёт сорок разных размеров за год и убивает
узнаваемость ленты. Не влезло на минимальной — говорим автору, на сколько
резать, и не ужимаем молча.
"""
import argparse
import json
import math
from pathlib import Path

import build_html
import render
import theme as theme_mod

# Какие ключи ступеней нужны каждому лейауту.
SIZE_KEYS = {
    "обложка": ("заголовок", "подзаголовок"),
    "тело": ("тело",),
    "тело-список": ("тело_список",),
    "CTA": ("cta",),
}

# Ключ ступеней в теме под каждое имя переменной.
STEP_KEY = {
    "заголовок": "обложка_заголовок",
    "подзаголовок": "обложка_подзаголовок",
    "тело": "тело",
    "тело_список": "тело_список",
    "cta": "cta",
}

# Грубая оценка «сколько символов в строке» — для подсказки, не для вёрстки.
CHARS_PER_LINE = 34


def sizes_for(data, layout, index):
    """Кегли для лейаута на ступени index (0 — самая крупная)."""
    result = {}
    for name in SIZE_KEYS[layout]:
        values = theme_mod.steps(data, STEP_KEY[name])
        result[name] = values[index]
    return result


def shortfall_chars(overflow_px, line_height_px, chars_per_line=CHARS_PER_LINE):
    """На сколько примерно символов резать текст.

    Считаем в целых строках: сократить полстроки нельзя, а автору нужна
    понятная цифра, а не точная.
    """
    if overflow_px <= 0 or line_height_px <= 0:
        return 0
    lines = math.ceil(overflow_px / line_height_px)
    return lines * chars_per_line


def step_count(data, layout):
    """Сколько ступеней доступно лейауту."""
    name = SIZE_KEYS[layout][0]
    return len(theme_mod.steps(data, STEP_KEY[name]))


def fit_slide(slide, data, platform, base_dir, tmp_dir):
    """Спускается по ступеням, пока не влезет. Возвращает финальный HTML и отчёт."""
    layout = slide["лейаут"]
    fmt = data["формат"]
    tmp_dir = Path(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    total = step_count(data, layout)
    result = None
    for index in range(total):
        sizes = sizes_for(data, layout, index)
        html_text = build_html.build(slide, data, platform, sizes, base_dir)
        html_path = tmp_dir / f"{slide['№']:02d}.html"
        html_path.write_text(html_text, encoding="utf-8")

        measured = render.measure(html_path, fmt["ширина"], fmt["высота"])
        result = {"html": html_path, "ступень": index,
                  "переполнение": measured["overflow_px"],
                  "недобор_символов": shortfall_chars(measured["overflow_px"],
                                                      measured["line_height_px"])}
        if measured["overflow_px"] <= 0:
            return result
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slides_json")
    ap.add_argument("--theme", required=True)
    ap.add_argument("--tmp", default="/tmp/carousel-render")
    args = ap.parse_args()

    spec = json.loads(Path(args.slides_json).read_text(encoding="utf-8"))
    data = theme_mod.load(args.theme)
    base = Path(args.slides_json).parent
    for slide in spec["слайды"]:
        got = fit_slide(slide, data, spec["meta"]["площадка"], base, args.tmp)
        print(f"{slide['№']:02d} ступень={got['ступень']} "
              f"переполнение={got['переполнение']}px "
              f"недобор={got['недобор_символов']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Запустить тесты**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_fit.py -v`
Expected: PASS, 12 тестов

- [ ] **Step 5: Коммит**

```bash
git add skills/carousel-render/scripts/fit.py skills/carousel-render/tests/test_fit.py
git commit -m "carousel-render: ступени кегля и контроль переполнения"
```

---

## Task 9: Контактный лист и оркестратор

**Files:**
- Create: `skills/carousel-render/scripts/contact_sheet.py`
- Create: `skills/carousel-render/scripts/carousel_render.py`
- Create: `skills/carousel-render/tests/test_contact_sheet.py`
- Create: `skills/carousel-render/tests/test_carousel_render.py`

**Interfaces:**
- Consumes: `theme.load` (Task 2), `fit.fit_slide` (Task 8), `render.screenshot`, `render.downscale`, `render.png_size` (Task 5)
- Produces:
  - `contact_sheet.build_sheet_html(pngs: list[Path], cols: int = 3) -> str`
  - `contact_sheet.build_sheet(pngs: list[Path], out: Path, cols: int = 3) -> Path`
  - `carousel_render.output_dir(slides_json: Path, env_dir: str | None, name: str) -> Path`
  - `carousel_render.run(slides_json: Path, theme_path: str, out_dir: Path | None) -> dict`
  - `carousel_render.format_report(result: dict) -> str`

- [ ] **Step 1: Написать падающий тест контактного листа**

```python
# skills/carousel-render/tests/test_contact_sheet.py
from pathlib import Path

import pytest

import contact_sheet


@pytest.fixture
def pngs(tmp_path):
    out = []
    for i in range(1, 5):
        p = tmp_path / f"{i:02d}.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([i]) * 16)
        out.append(p)
    return out


def test_sheet_html_embeds_every_slide(pngs):
    html = contact_sheet.build_sheet_html(pngs)
    assert html.count("data:image/png;base64,") == 4


def test_sheet_html_has_no_external_requests(pngs):
    html = contact_sheet.build_sheet_html(pngs)
    assert "http" not in html
    assert "file://" not in html


def test_sheet_html_uses_requested_columns(pngs):
    html = contact_sheet.build_sheet_html(pngs, cols=2)
    assert "repeat(2," in html


def test_sheet_html_numbers_slides(pngs):
    html = contact_sheet.build_sheet_html(pngs)
    for n in ("01", "02", "03", "04"):
        assert n in html
```

- [ ] **Step 2: Запустить, убедиться что падает**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_contact_sheet.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'contact_sheet'`

- [ ] **Step 3: Написать contact_sheet.py**

```python
#!/usr/bin/env python3
"""Простыня из всех слайдов одной картинкой. Только stdlib.

Сетку рисует тот же Chrome, что и карточки: PNG встраиваются как data: URI,
поэтому сторонняя графическая библиотека не нужна.
"""
import argparse
from pathlib import Path

import build_html
import render

CELL_W = 360


def build_sheet_html(pngs, cols=3):
    """HTML-сетка со встроенными PNG."""
    cells = []
    for png in pngs:
        cells.append(
            f'<figure><img src="{build_html.data_uri(png)}" alt="">'
            f"<figcaption>{Path(png).stem}</figcaption></figure>"
        )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        "*{margin:0;padding:0;box-sizing:border-box}"
        "body{background:#f2f2f4;padding:24px;font:14px -apple-system,sans-serif}"
        f".сетка{{display:grid;grid-template-columns:repeat({cols},{CELL_W}px);gap:20px}}"
        "figure{background:#fff;padding:8px;border-radius:6px}"
        "img{width:100%;display:block;border-radius:3px}"
        "figcaption{text-align:center;padding-top:6px;color:#666}"
        "</style></head><body><div class='сетка'>"
        + "".join(cells)
        + "</div></body></html>"
    )


def build_sheet(pngs, out, cols=3):
    """Снимает простыню в PNG. Высота считается по числу рядов."""
    out = Path(out)
    html_path = out.with_suffix(".html")
    html_path.write_text(build_sheet_html(pngs, cols), encoding="utf-8")

    rows = (len(pngs) + cols - 1) // cols
    width = cols * CELL_W + (cols + 1) * 20 + 8
    height = rows * int(CELL_W * 1350 / 1080 + 46) + (rows + 1) * 20 + 8
    render.screenshot(html_path, out, width, height, 1)
    html_path.unlink()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pngs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=3)
    args = ap.parse_args()
    print(build_sheet([Path(p) for p in args.pngs], args.out, args.cols))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Запустить тесты контактного листа**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_contact_sheet.py -v`
Expected: PASS, 4 теста

- [ ] **Step 5: Написать падающий тест оркестратора**

```python
# skills/carousel-render/tests/test_carousel_render.py
import json
from pathlib import Path

import pytest

import carousel_render


@pytest.fixture
def slides_json(tmp_path):
    spec = {
        "meta": {"название": "Тест", "площадка": "LI", "тема": "t.json"},
        "слайды": [
            {"№": 1, "лейаут": "обложка", "заголовок": "Раз"},
            {"№": 2, "лейаут": "тело", "блоки": ["Два"]},
        ],
    }
    p = tmp_path / "slides.json"
    p.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    return p


def test_output_dir_prefers_env(slides_json, tmp_path):
    got = carousel_render.output_dir(slides_json, str(tmp_path / "вывод"), "Тест")
    assert got == tmp_path / "вывод" / "Тест"


def test_output_dir_falls_back_next_to_json(slides_json):
    got = carousel_render.output_dir(slides_json, None, "Тест")
    assert got == slides_json.parent / "Тест"


def test_output_dir_ignores_empty_env(slides_json):
    got = carousel_render.output_dir(slides_json, "", "Тест")
    assert got == slides_json.parent / "Тест"


def test_report_lists_counts_and_paths():
    result = {"папка": Path("/tmp/Тест"), "слайды": [
        {"№": 1, "png": Path("/tmp/Тест/01.png"), "ступень": 0,
         "переполнение": 0, "недобор_символов": 0},
        {"№": 2, "png": Path("/tmp/Тест/02.png"), "ступень": 1,
         "переполнение": 0, "недобор_символов": 0},
    ], "простыня": Path("/tmp/Тест/contact-sheet.png"), "проблемы": []}
    text = carousel_render.format_report(result)
    assert "2" in text
    assert "/tmp/Тест" in text
    assert "слайд 2" in text and "ступен" in text


def test_report_shows_overflow_with_char_count():
    result = {"папка": Path("/tmp/Т"), "слайды": [
        {"№": 4, "png": Path("/tmp/Т/04.png"), "ступень": 2,
         "переполнение": 140, "недобор_символов": 68},
    ], "простыня": Path("/tmp/Т/contact-sheet.png"), "проблемы": []}
    text = carousel_render.format_report(result)
    assert "слайд 4" in text
    assert "68" in text
    assert "сократи" in text


def test_report_lists_missing_assets():
    result = {"папка": Path("/tmp/Т"), "слайды": [], "простыня": None,
              "проблемы": ["ассет «спарк» не найден: /nope/spark.svg"]}
    text = carousel_render.format_report(result)
    assert "спарк" in text
```

- [ ] **Step 6: Запустить, убедиться что падает**

Run: `cd skills/carousel-render && python3 -m pytest tests/test_carousel_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'carousel_render'`

- [ ] **Step 7: Написать carousel_render.py**

```python
#!/usr/bin/env python3
"""Оркестратор: slides.json + тема → папка PNG + простыня + отчёт.

Единственная точка входа скилла. Всё остальное — библиотеки, которые он
складывает в конвейер: тема → подбор ступени → съёмка → ужатие → простыня.
"""
import argparse
import json
import os
import tempfile
from pathlib import Path

import contact_sheet
import fit
import render
import theme as theme_mod


def output_dir(slides_json, env_dir, name):
    """Куда складывать. OUTPUT_DIR из .env, иначе рядом со slides.json."""
    base = Path(env_dir) if env_dir else Path(slides_json).parent
    return base / name


def run(slides_json, theme_path, out_dir=None):
    """Полный прогон карусели. Возвращает структуру для отчёта."""
    slides_json = Path(slides_json)
    spec = json.loads(slides_json.read_text(encoding="utf-8"))
    data = theme_mod.load(theme_path)

    problems = theme_mod.validate(data)
    name = spec["meta"]["название"]
    platform = spec["meta"]["площадка"]
    fmt = data["формат"]

    target = Path(out_dir) if out_dir else output_dir(
        slides_json, os.environ.get("OUTPUT_DIR"), name)
    target.mkdir(parents=True, exist_ok=True)

    slides, pngs = [], []
    with tempfile.TemporaryDirectory(prefix="carousel-render-") as tmp:
        for slide in spec["слайды"]:
            fitted = fit.fit_slide(slide, data, platform, slides_json.parent, tmp)
            png = target / f"{slide['№']:02d}.png"
            render.screenshot(fitted["html"], png, fmt["ширина"], fmt["высота"],
                              fmt["масштаб_рендера"])
            render.downscale(png, fmt["ширина"], fmt["высота"])
            pngs.append(png)
            slides.append({"№": slide["№"], "png": png, "ступень": fitted["ступень"],
                           "переполнение": fitted["переполнение"],
                           "недобор_символов": fitted["недобор_символов"]})

    sheet = contact_sheet.build_sheet(pngs, target / "contact-sheet.png") if pngs else None
    return {"папка": target, "слайды": slides, "простыня": sheet, "проблемы": problems}


def format_report(result):
    """Короткий отчёт автору. Без рассуждений."""
    lines = [f"Снято карточек: {len(result['слайды'])} → {result['папка']}"]
    if result.get("простыня"):
        lines.append(f"Простыня: {result['простыня']}")

    lowered = [s for s in result["слайды"] if s["ступень"] > 0 and not s["переполнение"]]
    for s in lowered:
        lines.append(f"слайд {s['№']}: кегль опущен на ступень {s['ступень']}")

    for s in result["слайды"]:
        if s["переполнение"] > 0:
            lines.append(f"слайд {s['№']}: не влезает даже на минимальной ступени — "
                         f"сократи примерно на {s['недобор_символов']} символов")

    for p in result.get("проблемы", []):
        lines.append(f"проблема темы: {p}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slides_json")
    ap.add_argument("--theme", default=os.environ.get("THEME_PATH"))
    ap.add_argument("--out")
    args = ap.parse_args()
    if not args.theme:
        raise SystemExit("THEME_PATH не задан — запусти scripts/check_env.py")
    print(format_report(run(args.slides_json, args.theme, args.out)))


if __name__ == "__main__":
    main()
```

- [ ] **Step 8: Запустить все тесты**

Run: `cd skills/carousel-render && python3 -m pytest tests/ -v -m "not integration"`
Expected: PASS, 86 тестов (64 после Task 7 + 12 ступени + 4 простыня + 6 оркестратор)

- [ ] **Step 9: Коммит**

```bash
git add skills/carousel-render/scripts/contact_sheet.py skills/carousel-render/scripts/carousel_render.py skills/carousel-render/tests/
git commit -m "carousel-render: контактный лист и оркестратор с отчётом"
```

---

## Task 10: SKILL.md, документация, подключение

**Files:**
- Create: `skills/carousel-render/SKILL.md`
- Create: `skills/carousel-render/README.md`
- Create: `skills/carousel-render/references/theme-schema.md`
- Create: `skills/carousel-render/references/layouts.md`
- Create: `skills/carousel-render/evals/evals.json`
- Modify: `skills/README.md`
- Modify: `docs/figma-карусели-гайд.md`

**Interfaces:**
- Consumes: все скрипты из Task 1–9
- Produces: работающий скилл, подхватываемый Claude Code

- [ ] **Step 1: Написать SKILL.md**

Фронтматтер с `name` и `description` по образцу `skills/rough-cut/SKILL.md`. Описание должно ловить триггеры «отрендери карусель», «собери карточки», «сделай PNG из карусели» и явно отбивать чужие: НЕ пишет текст карусели (это `carousel-script`), НЕ качает чужие посты (`instagram-downloader`).

Тело — оркестрация, без дублирования логики:

```markdown
## Шаг 0 — доктор (всегда первым)

python3 scripts/check_env.py

Красный Chrome или sips — стоп, скажи пользователю. Красные шрифты — запусти
scripts/fonts.py <папка темы>, он скачает Oswald и Montserrat с Google Fonts.

## Шаг 1 — прогон

python3 scripts/carousel_render.py <slides.json>

## Шаг 2 — отчёт

Отдай вывод скрипта как есть. Ничего не додумывай: если слайд не влез,
скажи цифру из отчёта и не предлагай «давай я сам сокращу» — сокращение
текста это работа carousel-script, а не рендера.

## Границы

- Схема slides.json — references/layouts.md
- Что можно менять в теме — references/theme-schema.md
- Правишь внешний вид → тема. Правишь композицию → это не сюда.
```

- [ ] **Step 2: Написать references/layouts.md**

Перенести из спеки §5 и §6: контракт `slides.json`, четыре лейаута с полями, правила `**…**`, `\n`, `нить`, автогашение подписи на фото-обложке. Примеры на реальных каруселях автора.

- [ ] **Step 3: Написать references/theme-schema.md**

Перенести из спеки §4: полная структура темы с комментарием на каждое поле, правило «три ступени по убыванию», как задаётся обвязка под площадку, где лежат шрифты и ассеты.

- [ ] **Step 4: Написать README.md скилла**

Коротко: что делает, когда срабатывает, что нужно на входе (`.env` с `THEME_PATH`, папка темы с `fonts/` и `assets/`), что на выходе.

- [ ] **Step 5: Написать evals/evals.json**

По образцу `skills/rough-cut/evals/evals.json`, минимум 5 кейсов:

```json
{
  "skill_name": "carousel-render",
  "evals": [
    {
      "id": 1,
      "prompt": "отрендери карусель «Агент. Харнес. Loop.»",
      "expected_output": "Активируется carousel-render: доктор → carousel_render.py → PNG 1080×1350 + contact-sheet + короткий отчёт",
      "files": []
    },
    {
      "id": 2,
      "prompt": "собери мне карточки вот из этого slides.json",
      "expected_output": "Прогон по указанному файлу, тема из THEME_PATH, отчёт с путями",
      "files": []
    },
    {
      "id": 3,
      "prompt": "напиши карусель про агентов",
      "expected_output": "НЕ carousel-render: это carousel-script — рендер не пишет тексты",
      "files": []
    },
    {
      "id": 4,
      "prompt": "поменяй мне аватарку на карточках на новую фотку",
      "expected_output": "Правка темы (обвязка.<площадка>.аватар), не правка кода лейаутов; затем повторный прогон",
      "files": []
    },
    {
      "id": 5,
      "prompt": "слайд 4 не влез, что делать",
      "expected_output": "Отдаёт цифру недобора из отчёта и отправляет сокращать текст в carousel-script, кегль руками не крутит",
      "files": []
    }
  ]
}
```

- [ ] **Step 6: Добавить в каталог skills/README.md**

В таблицу каталога, после строки `rough-cut`:

```markdown
| [carousel-render/](carousel-render/) | Рендер карусели в готовые PNG 1080×1350: slides.json + тема → HTML/CSS → headless Chrome; четыре лейаута, платформенная обвязка (IG/LinkedIn), ступени кегля с контролем переполнения, контактный лист |
```

- [ ] **Step 7: Пометить figma-гайд как legacy**

В начало `docs/figma-карусели-гайд.md`, сразу после заголовка:

```markdown
> **Legacy.** Для генерации каруселей используй скилл [carousel-render](../skills/carousel-render/) — он собирает карточки из `slides.json` без Figma. Этот гайд оставлен для точечной правки существующих макетов через мост `claude-talk-to-figma`.
```

- [ ] **Step 8: Подключить скилл глобально**

Run: `bash ./skills/install-skills.sh`
Expected: строка `+ подключён: carousel-render`

- [ ] **Step 9: Коммит**

```bash
git add skills/carousel-render/ skills/README.md docs/figma-карусели-гайд.md
git commit -m "carousel-render: SKILL.md, справочники, evals, каталог, figma-гайд в legacy"
```

---

## Task 11: Рендер-контракт в carousel-script

**Files:**
- Modify: `skills/carousel-script/SKILL.md`
- Modify: `skills/carousel-script/references/slide-spec.md`

**Interfaces:**
- Consumes: схема `slides.json` (Task 4, 6, 7), словарь лейаутов `theme.LAYOUTS` (Task 2)
- Produces: `carousel-script` начинает отдавать `slides.json` рядом с таблицей

- [ ] **Step 1: Привести словарь лейаутов в slide-spec.md**

Заменить таблицу «Словарь лейаутов» (`skills/carousel-script/references/slide-spec.md:39-46`) на четыре значения, которые поддерживает рендер:

```markdown
| Значение | Характер |
|---|---|
| `обложка` | Полноэкранный заголовок Oswald + подзаголовок; виды: `текст`, `декор` (значок в углу), `фото` (снимок на весь кадр) |
| `тело` | Светлая карточка, 1–4 абзаца, выделения `**…**`, опциональная стрелка-нить |
| `тело-список` | Заголовок + подзаголовок-боль + пункты `**имя** — что даёт` + подвал курсивом |
| `CTA` | Тёмная карточка: крупная подпись сверху, текст призыва по центру, без бейджа |
```

Значения `большая-цифра`, `цитата`, `текст+визуал`, `сравнение` убрать: рендер их не поддерживает, а расходящийся словарь даёт спек, который нельзя собрать.

- [ ] **Step 2: Добавить раздел «Рендер-контракт» в slide-spec.md**

В конец файла, перед «Заметки»:

````markdown
## Рендер-контракт

Вместе с таблицей для человека скилл кладёт рядом `slides.json` — его читает
`carousel-render`. Парсить markdown-таблицу хрупко, поэтому машинный вход
отдельный.

```json
{
  "meta": { "название": "…", "площадка": "IG", "тема": "…" },
  "слайды": [
    { "№": 1, "лейаут": "обложка", "заголовок": "Строка\nвторая",
      "подзаголовок": "…" },
    { "№": 2, "лейаут": "тело", "блоки": ["Абзац с **выделением**."],
      "нить": true },
    { "№": 3, "лейаут": "тело-список", "заголовок": "…", "подзаголовок": "…",
      "пункты": ["**имя** — что даёт"], "подвал": "→ …" },
    { "№": 9, "лейаут": "CTA", "блоки": ["…"] }
  ]
}
```

Правила:
- `**…**` — выделение. Смысл подставляет лейаут: в теле жирное начертание,
  на обложке акцентный цвет. Не думай про цвет, думай «что выделить».
- `\n` в заголовке — принудительный перенос строки.
- `нить: true` — стрелка `⇢` в конце последнего блока.
- Бейдж «ЛИСТАЙ» и подпись с аватаркой в JSON не пишутся: их рисует тема.
- На обложке с `вид: фото` подпись гасится автоматически.
````

- [ ] **Step 3: Провязать в SKILL.md carousel-script**

В шаг выдачи спека добавить: скилл отдаёт таблицу **и** `slides.json` по разделу «Рендер-контракт» из `references/slide-spec.md`, а на просьбу «отрендери» передаёт управление скиллу `carousel-render`. Логику рендера не описывать — только ссылку.

- [ ] **Step 4: Проверить, что evals carousel-script не сломались**

Run: `cd skills/carousel-script && cat evals/evals.json | python3 -m json.tool > /dev/null && echo "JSON цел"`
Expected: `JSON цел`

Перечитать `evals.json` глазами: если какой-то кейс ожидает лейаут из старого словаря (`цитата`, `сравнение`, `большая-цифра`, `текст+визуал`), поправить ожидание на новый словарь.

- [ ] **Step 5: Коммит**

```bash
git add skills/carousel-script/
git commit -m "carousel-script: рендер-контракт slides.json, словарь лейаутов сведён с carousel-render"
```

---

## Task 12: Приёмка на реальных карточках и калибровка кеглей

**Files:**
- Modify: тема автора (вне репозитория, `$THEME_PATH`) — ступени кегля
- Create: эталонные `slides.json` во временной папке (в репозиторий не коммитятся — личный контент)

**Interfaces:**
- Consumes: весь конвейер (Task 1–11)
- Produces: подтверждённые значения ступеней в теме автора

**Что нужно от автора до начала:** аватарка IG, аватарка LinkedIn, спарк в SVG. Без них рендерятся плейсхолдеры.

- [ ] **Step 1: Собрать тему автора**

Создать `$THEME_PATH` с бренд-константами из раздела Global Constraints, папками `fonts/` и `assets/`. Прогнать `python3 scripts/fonts.py <папка темы>` и `python3 scripts/check_env.py` — всё зелёное.

- [ ] **Step 2: Набрать эталон 1 — LinkedIn «Агент. Харнес. Loop.»**

Записать `slides.json` на 7 слайдов по тексту оригинала: обложка, пять слайдов тела с нитью, CTA. `площадка: "LI"`.

- [ ] **Step 3: Прогнать и сравнить с оригиналом**

```bash
python3 scripts/carousel_render.py /tmp/эталон-1/slides.json
open /tmp/эталон-1/Агент.\ Харнес.\ Loop./contact-sheet.png
```

Открыть рядом оригинал. Сверять по порядку: шрифт не засечный → кегль заголовка → кегль тела → позиция подписи и бейджа → межстрочные и отступы.

- [ ] **Step 4: Откалибровать ступени**

Правки только в `ступени` темы, код не трогать. После каждой правки — повторный прогон. Критерий остановки: наложение на оригинал не выявляет расхождений, заметных глазом на 100% масштабе.

Записать финальные значения в `references/theme-schema.md` как рекомендованный старт.

- [ ] **Step 5: Эталон 2 — IG-карточка «Разработка»**

`slides.json` с одним слайдом `тело-список`, `площадка: "IG"`. Проверить: подпись внизу слева, бейдж внизу справа, шесть пунктов влезают, подвал курсивом.

- [ ] **Step 6: Эталон 3 — IG-обложка «Я отдал свой Instagram Claude»**

`вид: декор`. Проверить: акцент `#D97757` на слове «CLAUDE», спарк в углу не перекрывает текст, подзаголовок с цифрами читается.

- [ ] **Step 7: Эталон 4 — пляжная обложка**

`вид: фото` с реальным снимком. Проверить: фото на весь кадр без искажений, затемнение снизу, текст читается, **подпись с аватаркой отсутствует** без явного указания.

- [ ] **Step 8: Проверить детерминизм**

```bash
cd /tmp/эталон-1 && cp -r "Агент. Харнес. Loop." прогон-1
python3 <путь>/scripts/carousel_render.py slides.json
for f in прогон-1/*.png; do cmp -s "$f" "Агент. Харнес. Loop./$(basename $f)" \
  && echo "= $(basename $f)" || echo "РАЗЛИЧАЮТСЯ: $(basename $f)"; done
```

Expected: все строки со знаком `=`.

Если PNG различаются при одинаковом входе — искать источник недетерминизма: чаще всего это анимация или `transition` в CSS, не успевшая завершиться. Лечится увеличением `--virtual-time-budget`.

- [ ] **Step 9: Проверить точечную правку**

Изменить одну строку в `slides.json` эталона 1, прогнать снова, сравнить: изменился ровно один PNG, остальные байт в байт.

- [ ] **Step 10: Проверить ловлю переполнения**

Вписать в слайд заведомо длинный текст (втрое больше нормы), прогнать. Expected: в отчёте строка «слайд N: не влезает даже на минимальной ступени — сократи примерно на M символов», PNG при этом снят и текст в нём не обрезан визуально по-живому.

- [ ] **Step 11: Прогнать весь набор тестов**

Run: `cd skills/carousel-render && python3 -m pytest tests/ -v`
Expected: PASS, все тесты включая integration

- [ ] **Step 12: Финальный коммит и PR**

```bash
git add skills/carousel-render/references/theme-schema.md
git commit -m "carousel-render: откалиброванные ступени кегля по эталонным карточкам"
git push -u origin carousel-render
gh pr create --title "carousel-render: рендер каруселей в PNG" --body "$(cat <<'EOF'
Новый скилл: slides.json + тема → готовые PNG 1080×1350 без ручной вёрстки.

Спека: docs/superpowers/specs/2026-07-29-carousel-render-skill-design.md

- 4 лейаута из практики: обложка (текст/декор/фото), тело, тело-список, CTA
- тема = данные (цвета, шрифты, ассеты, обвязка, ступени), композиция = код
- обвязка платформенная: IG — хэндл, LinkedIn — имя с должностью, аватарки разные
- ступени кегля вместо плавной подгонки; не влезло — отчёт «сократи на N», не сжатие
- самодостаточный HTML: шрифты и картинки как data: URI, ноль внешних запросов
- carousel-script отдаёт slides.json; словари лейаутов сведены
- docs/figma-карусели-гайд.md помечен legacy

Приёмка пройдена на 4 реальных карточках автора.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review

**Spec coverage:**

| Раздел спеки | Задача |
|---|---|
| §1 что строим, чего не делать | Global Constraints (запреты: не Figma MCP, не генерация картинок, не плавная подгонка кегля) |
| §2 проверено на машине | Global Constraints, Task 1 (доктор), Task 5 (рендер) |
| §3 архитектура: тема / лейауты / рендер | File Structure, Task 2, 4, 5 |
| §4 тема: цвета, шрифты, структура | Task 2, Task 12 (калибровка) |
| §5 контракт slides.json | Task 4, 6, 7; Task 11 (провязка) |
| §6 четыре лейаута | Task 4 (обложка), 6 (тело, список), 7 (CTA) |
| §7 ступени и переполнение | Task 8, Task 12 шаг 10 |
| §8 изображения, 4 слота, SVG | Task 4 (`data_uri`, спарк, фото), Task 2 (аватар) |
| §9 обезличенность, .env | Task 1 (.env.template, .gitignore), Task 2 (example.json) |
| §10 выход, отчёт, вызов | Task 9 (простыня, отчёт), Task 10 (SKILL.md) |
| §11 стык с carousel-script | Task 11 |
| §12 приёмка | Task 12 |
| §13 открытые вопросы | Task 12 шаги 3–7 (позиция обвязки решается глазами) |

**Placeholder scan:** пройден. Все шаги содержат исполнимый код или точный текст правки. Единственное место, где значения намеренно не финальны — ступени кегля: они помечены как стартовые и калибруются в Task 12, что и есть их полноценная реализация.

**Type consistency:** сверено. `theme.load` → `dict` с `_dir: Path` используется в `build_html.build` и `fit.fit_slide`. `theme.binding` возвращает ключи `аватар`/`подпись`/`бейдж`/`подпись_позиция` — те же читаются в `_badge_html` и `_signature_html`. `render.measure` возвращает `overflow_px`/`line_height_px` — те же ключи в `fit.fit_slide` и в тестовых заглушках. `fit.fit_slide` возвращает `html`/`ступень`/`переполнение`/`недобор_символов` — те же читает `carousel_render.run` и `format_report`. Имена ключей ступеней (`обложка_заголовок`, `тело_список`, `cta`) совпадают в `theme.REQUIRED_STEPS`, `fit.STEP_KEY`, `conftest.theme_file` и `themes/example.json`.

**Найдено и исправлено при сверке:** в Task 2 `example.json` появился блок `CTA` в `позиции` с `бейдж: "нет"` — без него `theme.binding` для CTA вернул бы дефолт `верх-центр` и на карточке призыва нарисовался бы бейдж «ЛИСТАЙ», которого там быть не должно.
