# `youtube-meta` + режим превью — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Дать `youtube-analytics` режим измерения текста на превью, а затем собрать скилл `youtube-meta`, который пишет тайтл, описание, теги и главы по этим замерам, а не по общим канонам.

**Architecture:** Этап 1 — два новых скрипта в `youtube-analytics`: `thumb_text.py` (чистая арифметика по распознанному тексту) и `fetch_thumbs.py` (скачивание превью + вызов OCR), плюс раздел в отчёте `patterns`. Этап 2 — `youtube-meta` без единого скрипта: вся арифметика осталась в аналитике, скилл только применяет её выводы через `references/`.

**Tech Stack:** Python 3.9+ (только stdlib), Apple Vision через `ocr-cards.sh` (Swift, macOS), pytest через `uv run --with pytest`.

## Global Constraints

- **Ноль сторонних зависимостей в Python.** Только stdlib. Совместимость с Python 3.9: без `match`, без `int | None` в аннотациях; аннотаций типов нет вообще, как в существующих скриптах.
- **Тесты:** `uv run --with pytest pytest skills/youtube-analytics/tests -q` из корня репо. Текущая база — 68 тестов, все зелёные.
- **Порог надёжности группы — 5 роликов**, как в `patterns.py` (`MIN_GROUP = 5`). Группа меньше помечается `reliable: false` и в выводах не участвует.
- **Превью не хранятся:** качаются во временную папку, после OCR удаляются. В карточку идёт `thumbnail_url` и распознанный текст, не файл.
- **OCR только macOS.** Нет `swiftc` или не Darwin — режим честно отказывается, остальные режимы работают.
- **Стоп-лист тайтла** (CAPS, скобки, отрицание лидера) скилл `youtube-meta` не предлагает сам; по прямой просьбе ставит с пометкой «приём одного канала, у Vibecoder вредит».
- **Правило `copy-law` про имя инструмента на YouTube инвертировано** — имя в тайтле работает. Запрет из ленты не тянуть.
- **Числа замеров датированы 2026-08-09** и помечены в `references` как снимок; пересчёт — прогоном `youtube-analytics`, не руками.

---

## Файловая структура

| Файл | Ответственность |
|---|---|
| `skills/youtube-analytics/scripts/thumb_text.py` | Чистые функции: разбор вывода OCR, признаки текста на превью, срез против кратности |
| `skills/youtube-analytics/scripts/fetch_thumbs.py` | Скачивание превью, вызов OCR, сборка `.thumbs.json`. CLI |
| `skills/youtube-analytics/scripts/ocr-cards.sh` + `.swift` | Копия из `instagram-analytics` — скиллы подключаются поштучно и ломаются в отрыве |
| `skills/youtube-analytics/scripts/patterns.py` | +раздел 8 «Текст на превью», если рядом лежит `.thumbs.json` |
| `skills/youtube-analytics/scripts/vault.py` | +секция `## Текст на превью` в карточке |
| `skills/youtube-meta/SKILL.md` | Оркестрация трёх режимов |
| `skills/youtube-meta/references/title-signals.md` | Замеры, стоп-лист, сборка тайтла, порядок теста |
| `skills/youtube-meta/references/description-template.md` | Шаблон описания: что константа, что меняется |
| `skills/youtube-meta/references/tags-chapters-thumbnail.md` | Теги, главы с `00:00`, текст на превью |
| `skills/youtube-meta/references/reference-transfer.md` | Режим ПЕРЕНОС: годность референса + разбор механики |

---

# ЭТАП 1 — режим превью в `youtube-analytics`

### Task 1: `thumb_text.py` — арифметика по тексту превью

**Files:**
- Create: `skills/youtube-analytics/scripts/thumb_text.py`
- Test: `skills/youtube-analytics/tests/test_thumb_text.py`

**Interfaces:**
- Consumes: ничего
- Produces: `parse_ocr_output(text)` → `{video_id: [строки]}`; `features(text)` → dict флагов; `word_count(lines)` → int; `slice_by_feature(records, blocks)` → `{признак: {"n", "median_multiple", "median_without", "reliable"}}`

**Формат входа.** `ocr-cards.sh` печатает блоками: строка `=== <имя файла>`, затем распознанные строки. При ошибке первая строка блока начинается с `!!` — такой блок считается пустым, а не текстом.

- [ ] **Step 1: Напиши падающие тесты**

```python
import thumb_text

OCR = """ocr-cards: собираю бинарник (один раз)…
=== k1DTxuBur-Y.jpg
ПЕРЕСТАНЬ
ИСПОЛЬЗОВАТЬ
CURSOR AI
=== 0Sxf4B-KTvA.jpg
БЕСПЛАТНО
НАВСЕГДА
=== brokenID123.jpg
!! Vision не смог: что-то пошло не так
=== emptyID4567.jpg
"""


def test_parse_ocr_output_splits_blocks():
    blocks = thumb_text.parse_ocr_output(OCR)
    assert blocks["k1DTxuBur-Y"] == ["ПЕРЕСТАНЬ", "ИСПОЛЬЗОВАТЬ", "CURSOR AI"]
    assert blocks["0Sxf4B-KTvA"] == ["БЕСПЛАТНО", "НАВСЕГДА"]


def test_parse_ocr_output_error_block_is_empty():
    # строка с !! — это сообщение об ошибке, а не распознанный текст
    assert thumb_text.parse_ocr_output(OCR)["brokenID123"] == []


def test_parse_ocr_output_empty_block():
    assert thumb_text.parse_ocr_output(OCR)["emptyID4567"] == []


def test_parse_ocr_output_ignores_preamble():
    # строка про сборку бинарника не должна попасть ни в один блок
    blocks = thumb_text.parse_ocr_output(OCR)
    assert all("собираю бинарник" not in " ".join(v) for v in blocks.values())


def test_parse_ocr_output_empty_input():
    assert thumb_text.parse_ocr_output("") == {}


def test_features_free():
    assert thumb_text.features("БЕСПЛАТНО НАВСЕГДА")["бесплатно"] is True
    assert thumb_text.features("Get it FREE now")["бесплатно"] is True
    assert thumb_text.features("СКИДКА 50%")["бесплатно"] is False


def test_features_paid_tool_name():
    f = thumb_text.features("ПЕРЕСТАНЬ ИСПОЛЬЗОВАТЬ CURSOR AI")
    assert f["имя инструмента"] is True
    assert f["запрет"] is True


def test_features_digit():
    assert thumb_text.features("7 ДНЕЙ НЕЙРОСЕТЬ")["цифра"] is True
    assert thumb_text.features("ВЕРНУЛ СЛОВА В МУЗЫКУ")["цифра"] is False


def test_features_on_empty_text():
    f = thumb_text.features("")
    assert all(v is False for v in f.values())


def test_word_count():
    assert thumb_text.word_count(["ПЕРЕСТАНЬ", "ИСПОЛЬЗОВАТЬ CURSOR AI"]) == 3
    assert thumb_text.word_count([]) == 0


def test_slice_by_feature_compares_with_and_without():
    records = {
        "a": {"median_multiple": 4.0},
        "b": {"median_multiple": 3.5},
        "c": {"median_multiple": 1.0},
        "d": {"median_multiple": 0.5},
    }
    blocks = {"a": ["БЕСПЛАТНО"], "b": ["всё БЕСПЛАТНО"],
              "c": ["просто текст"], "d": ["ещё текст"]}
    out = thumb_text.slice_by_feature(records, blocks)
    free = out["бесплатно"]
    assert free["n"] == 2
    assert free["median_multiple"] == 3.75
    assert free["median_without"] == 0.75
    assert free["reliable"] is False  # n=2 < порога 5


def test_slice_marks_reliable_above_threshold():
    records = {str(i): {"median_multiple": 2.0} for i in range(6)}
    records.update({"x%d" % i: {"median_multiple": 1.0} for i in range(6)})
    blocks = {k: (["БЕСПЛАТНО"] if not k.startswith("x") else ["текст"])
              for k in records}
    out = thumb_text.slice_by_feature(records, blocks)
    assert out["бесплатно"]["n"] == 6
    assert out["бесплатно"]["reliable"] is True


def test_slice_ignores_ids_without_metrics():
    records = {"a": {"median_multiple": 2.0}}
    blocks = {"a": ["БЕСПЛАТНО"], "неизвестный": ["БЕСПЛАТНО"]}
    assert thumb_text.slice_by_feature(records, blocks)["бесплатно"]["n"] == 1


def test_length_slice_present():
    records = {str(i): {"median_multiple": 1.0} for i in range(4)}
    blocks = {"0": ["раз два"], "1": ["раз два три четыре пять"],
              "2": ["а"], "3": ["раз два три четыре пять шесть"]}
    out = thumb_text.slice_by_feature(records, blocks)
    assert "текст ≤4 слов" in out
    assert out["текст ≤4 слов"]["n"] == 2
```

- [ ] **Step 2: Прогони тесты, убедись что падают**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_thumb_text.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'thumb_text'`

- [ ] **Step 3: Реализуй `thumb_text.py`**

```python
#!/usr/bin/env python3
"""Текст на превью: разбор вывода OCR и срез признаков. Только stdlib.

Замер 2026-08-09 (Vibecoder School, 47 превью): на превью работает та же
ось, что в тайтле — цена, имя инструмента, конкретика. Расхожий совет
«2–4 слова на превью» не подтвердился: короткие дали 0.89 против 1.27.
"""
import re
import statistics

MIN_GROUP = 5
SHORT_TEXT_WORDS = 4

FEATURES = {
    "бесплатно": r"бесплатн|\bfree\b|0\s*₽|даром",
    "имя инструмента": (r"cursor|claude|chatgpt|\bgpt\b|midjourney|copilot|"
                        r"gemini|windsurf|figma|notion|canva|n8n|codex"),
    "цифра": r"\d",
    "запрет": r"перестань|хватит|забудь|больше не|\bstop\b|don'?t",
}

_HEADER = re.compile(r"^===\s+(.+?)(?:\.[A-Za-z0-9]+)?\s*$")


def parse_ocr_output(text):
    """Вывод ocr-cards.sh → {video_id: [строки]}.

    Блок начинается с '=== <файл>'. Строка на '!!' — сообщение об ошибке
    Vision, а не распознанный текст: такой блок остаётся пустым.
    """
    blocks = {}
    current = None
    for line in (text or "").splitlines():
        m = _HEADER.match(line.strip())
        if m:
            current = m.group(1)
            blocks[current] = []
            continue
        clean = line.strip()
        if current is None or not clean or clean.startswith("!!"):
            continue
        blocks[current].append(clean)
    return blocks


def features(text):
    text = text or ""
    return {name: bool(re.search(pattern, text, re.I))
            for name, pattern in FEATURES.items()}


def word_count(lines):
    return len(" ".join(lines or []).split())


def _median(values):
    return round(statistics.median(values), 2) if values else None


def _pair(records, ids_yes, ids_no):
    yes = [records[i]["median_multiple"] for i in ids_yes
           if records.get(i, {}).get("median_multiple") is not None]
    no = [records[i]["median_multiple"] for i in ids_no
          if records.get(i, {}).get("median_multiple") is not None]
    return {"n": len(yes), "median_multiple": _median(yes),
            "median_without": _median(no), "reliable": len(yes) >= MIN_GROUP}


def slice_by_feature(records, blocks):
    """Срез по каждому признаку + по длине текста. records: {id: {...}}."""
    known = [i for i in blocks if i in records]
    out = {}
    for name in FEATURES:
        yes = [i for i in known if features(" ".join(blocks[i]))[name]]
        no = [i for i in known if not features(" ".join(blocks[i]))[name]]
        out[name] = _pair(records, yes, no)

    short = [i for i in known if 0 < word_count(blocks[i]) <= SHORT_TEXT_WORDS]
    long_ = [i for i in known if word_count(blocks[i]) > SHORT_TEXT_WORDS]
    out["текст ≤%d слов" % SHORT_TEXT_WORDS] = _pair(records, short, long_)
    return out
```

- [ ] **Step 4: Прогони тесты**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_thumb_text.py -q`
Expected: PASS, 14 тестов

- [ ] **Step 5: Коммит**

```bash
git add skills/youtube-analytics/scripts/thumb_text.py \
        skills/youtube-analytics/tests/test_thumb_text.py
git commit -m "youtube-analytics: арифметика по тексту превью"
```

---

### Task 2: `fetch_thumbs.py` — скачивание превью и вызов OCR

**Files:**
- Create: `skills/youtube-analytics/scripts/fetch_thumbs.py`
- Copy: `skills/instagram-analytics/scripts/ocr-cards.sh` → `skills/youtube-analytics/scripts/ocr-cards.sh`
- Copy: `skills/instagram-analytics/scripts/ocr-cards.swift` → `skills/youtube-analytics/scripts/ocr-cards.swift`
- Test: `skills/youtube-analytics/tests/test_fetch_thumbs.py`

**Interfaces:**
- Consumes: `thumb_text.parse_ocr_output`, `thumb_text.slice_by_feature`
- Produces: `ocr_available(platform, which)` → bool; `download_all(videos, out_dir, fetcher)` → список id; `build(data, ocr_runner, fetcher, work_dir)` → `{"slices": {...}, "texts": {id: "строка"}, "covered": int, "total": int}`; CLI `python3 fetch_thumbs.py --in .channel.json --out .thumbs.json`

- [ ] **Step 1: Скопируй OCR-скрипт**

```bash
cp skills/instagram-analytics/scripts/ocr-cards.sh \
   skills/instagram-analytics/scripts/ocr-cards.swift \
   skills/youtube-analytics/scripts/
chmod +x skills/youtube-analytics/scripts/ocr-cards.sh
```

Проверь, что копия работает автономно:
Run: `bash skills/youtube-analytics/scripts/ocr-cards.sh 2>&1 | head -2`
Expected: сообщение об использовании (код 2) — значит скрипт нашёл свой `.swift` рядом.

- [ ] **Step 2: Напиши падающие тесты**

```python
import json

import fetch_thumbs

OCR_OUT = """=== aaa.jpg
БЕСПЛАТНО
НАВСЕГДА
=== bbb.jpg
просто текст без признаков
"""


def _data():
    return {
        "channel": {"title": "T", "handle": "t"},
        "videos": [
            {"id": "aaa", "thumbnail_url": "http://t/a.jpg",
             "median_multiple": 4.0, "title": "A"},
            {"id": "bbb", "thumbnail_url": "http://t/b.jpg",
             "median_multiple": 0.5, "title": "B"},
            {"id": "ccc", "thumbnail_url": "", "median_multiple": 1.0,
             "title": "C"},
        ],
    }


def test_ocr_available_needs_macos_and_swiftc():
    assert fetch_thumbs.ocr_available("darwin", lambda c: "/usr/bin/swiftc")
    assert not fetch_thumbs.ocr_available("linux", lambda c: "/usr/bin/swiftc")
    assert not fetch_thumbs.ocr_available("darwin", lambda c: None)


def test_download_all_skips_videos_without_thumbnail(tmp_path):
    got = []

    def fetcher(url, path):
        got.append(url)
        open(path, "wb").write(b"jpg")

    ids = fetch_thumbs.download_all(_data()["videos"], tmp_path, fetcher)
    assert ids == ["aaa", "bbb"]
    assert len(got) == 2


def test_download_all_survives_single_failure(tmp_path):
    def fetcher(url, path):
        if "b.jpg" in url:
            raise IOError("сеть отвалилась")
        open(path, "wb").write(b"jpg")

    ids = fetch_thumbs.download_all(_data()["videos"], tmp_path, fetcher)
    # один упал — остальные собраны, а не потеряны
    assert ids == ["aaa"]


def test_build_returns_slices_and_texts(tmp_path):
    def fetcher(url, path):
        open(path, "wb").write(b"jpg")

    def ocr_runner(paths):
        return OCR_OUT

    out = fetch_thumbs.build(_data(), ocr_runner=ocr_runner, fetcher=fetcher,
                             work_dir=tmp_path)
    assert out["covered"] == 2
    assert out["total"] == 3
    assert out["texts"]["aaa"] == "БЕСПЛАТНО НАВСЕГДА"
    assert out["slices"]["бесплатно"]["n"] == 1
    assert out["slices"]["бесплатно"]["median_multiple"] == 4.0


def test_build_deletes_downloaded_thumbnails(tmp_path):
    """Превью не хранятся — то же правило, что «видео не храним»."""
    def fetcher(url, path):
        open(path, "wb").write(b"jpg")

    fetch_thumbs.build(_data(), ocr_runner=lambda p: OCR_OUT,
                       fetcher=fetcher, work_dir=tmp_path)
    assert list(tmp_path.glob("*.jpg")) == []


def test_build_without_ocr_returns_honest_empty(tmp_path):
    out = fetch_thumbs.build(_data(), ocr_runner=None, fetcher=lambda u, p: None,
                             work_dir=tmp_path)
    assert out["covered"] == 0
    assert out["slices"] == {}
    assert "macOS" in out["skipped"]
```

- [ ] **Step 3: Прогони тесты, убедись что падают**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_fetch_thumbs.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_thumbs'`

- [ ] **Step 4: Реализуй `fetch_thumbs.py`**

```python
#!/usr/bin/env python3
"""Режим thumbs: превью → текст → срез признаков. Только stdlib.

Превью НЕ хранятся: качаются во временную папку, после OCR удаляются.
В базу идёт распознанный текст и thumbnail_url, не файл.

OCR — Apple Vision через ocr-cards.sh, только macOS. Нет условий —
режим честно отказывается, остальные режимы скилла работают.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import thumb_text

WORKERS = 8
OCR_SCRIPT = Path(__file__).parent / "ocr-cards.sh"


def ocr_available(platform=None, which=None):
    platform = platform if platform is not None else sys.platform
    which = which or shutil.which
    return platform == "darwin" and bool(which("swiftc"))


def _default_fetcher(url, path):
    urllib.request.urlretrieve(url, path)


def download_all(videos, out_dir, fetcher=None):
    """Качает превью параллельно. Упавшие пропускаются, остальные собираются."""
    fetcher = fetcher or _default_fetcher
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = [v for v in videos if v.get("thumbnail_url")]

    done = []

    def one(v):
        path = out_dir / (v["id"] + ".jpg")
        try:
            fetcher(v["thumbnail_url"], str(path))
            return v["id"]
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for got in pool.map(one, targets):
            if got:
                done.append(got)
    return done


def _default_ocr(paths):
    result = subprocess.run(["bash", str(OCR_SCRIPT)] + [str(p) for p in paths],
                            capture_output=True, text=True, check=False)
    return result.stdout


def build(data, ocr_runner=None, fetcher=None, work_dir=None):
    videos = data["videos"]
    total = len(videos)
    if ocr_runner is None and not ocr_available():
        return {"slices": {}, "texts": {}, "covered": 0, "total": total,
                "skipped": "OCR недоступен: нужен macOS и swiftc "
                           "(xcode-select --install)"}

    ocr_runner = ocr_runner or _default_ocr
    tmp = Path(work_dir) if work_dir else Path(tempfile.mkdtemp())
    ids = download_all(videos, tmp, fetcher)
    paths = [tmp / (i + ".jpg") for i in ids]

    raw = ocr_runner(paths) if paths else ""
    blocks = thumb_text.parse_ocr_output(raw)

    for p in paths:
        try:
            p.unlink()
        except OSError:
            pass

    records = {v["id"]: v for v in videos}
    return {
        "slices": thumb_text.slice_by_feature(records, blocks),
        "texts": {k: " ".join(v) for k, v in blocks.items() if v},
        "covered": sum(1 for v in blocks.values() if v),
        "total": total,
        "skipped": "",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="текст на превью канала")
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    data = json.loads(Path(args.src).read_text(encoding="utf-8"))
    result = build(data)
    Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"covered": result["covered"], "total": result["total"],
                      "skipped": result["skipped"], "out": args.out},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Прогони тесты**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_fetch_thumbs.py -q`
Expected: PASS, 6 тестов

- [ ] **Step 6: Коммит**

```bash
git add skills/youtube-analytics/scripts/fetch_thumbs.py \
        skills/youtube-analytics/scripts/ocr-cards.sh \
        skills/youtube-analytics/scripts/ocr-cards.swift \
        skills/youtube-analytics/tests/test_fetch_thumbs.py
git commit -m "youtube-analytics: режим thumbs — превью в текст, превью не храним"
```

---

### Task 3: Проводка режима в отчёт, карточки и SKILL.md

**Files:**
- Modify: `skills/youtube-analytics/scripts/patterns.py` (добавить раздел 8)
- Modify: `skills/youtube-analytics/scripts/vault.py` (секция карточки)
- Modify: `skills/youtube-analytics/SKILL.md` (режим `thumbs`)
- Modify: `skills/youtube-analytics/references/patterns-reading.md` (как читать срез превью)
- Modify: `skills/youtube-analytics/README.md`
- Test: `skills/youtube-analytics/tests/test_patterns.py`, `test_vault.py`

**Interfaces:**
- Consumes: `.thumbs.json` из Task 2
- Produces: `patterns.render_markdown(report, channel, thumbs=None)` — третий необязательный аргумент; `vault.card_markdown` с секцией `## Текст на превью`

- [ ] **Step 1: Напиши падающие тесты**

В `tests/test_patterns.py` добавь:

```python
def test_render_markdown_adds_thumbnail_section_when_given():
    data = {"channel": {"title": "T", "handle": "t", "subscribers": 1},
            "videos": [{"id": "a", "title": "t", "date": "2026-07-01",
                        "kind": "long", "views": 10, "duration_sec": 600,
                        "description": "", "median_multiple": 1.0,
                        "engagement_rate": 0.01, "views_per_day": 1.0}]}
    thumbs = {"covered": 40, "total": 47, "skipped": "",
              "slices": {"бесплатно": {"n": 6, "median_multiple": 3.75,
                                       "median_without": 0.96,
                                       "reliable": True}}}
    md = patterns.render_markdown(patterns.build_report(data),
                                  data["channel"], thumbs)
    assert "## 8. Текст на превью" in md
    assert "3.75" in md
    assert "0.96" in md
    # раздел «Что забираем себе» остаётся последним
    assert md.index("## Что забираем себе") > md.index("## 8. Текст на превью")


def test_render_markdown_without_thumbs_has_no_section():
    data = {"channel": {"title": "T", "handle": "t", "subscribers": 1},
            "videos": [{"id": "a", "title": "t", "date": "2026-07-01",
                        "kind": "long", "views": 10, "duration_sec": 600,
                        "description": "", "median_multiple": 1.0,
                        "engagement_rate": 0.01, "views_per_day": 1.0}]}
    md = patterns.render_markdown(patterns.build_report(data), data["channel"])
    assert "Текст на превью" not in md


def test_render_markdown_reports_skipped_ocr():
    data = {"channel": {"title": "T", "handle": "t", "subscribers": 1},
            "videos": [{"id": "a", "title": "t", "date": "2026-07-01",
                        "kind": "long", "views": 10, "duration_sec": 600,
                        "description": "", "median_multiple": 1.0,
                        "engagement_rate": 0.01, "views_per_day": 1.0}]}
    thumbs = {"covered": 0, "total": 47, "skipped": "OCR недоступен: нужен macOS",
              "slices": {}}
    md = patterns.render_markdown(patterns.build_report(data),
                                  data["channel"], thumbs)
    assert "OCR недоступен" in md
```

В `tests/test_vault.py` добавь:

```python
def test_card_has_thumbnail_text_section():
    md = vault.card_markdown(_video(), CHANNEL)
    assert "## Текст на превью" in md


def test_card_fills_thumbnail_text_when_known():
    v = _video()
    v["thumbnail_text"] = "БЕСПЛАТНО НАВСЕГДА"
    md = vault.card_markdown(v, CHANNEL)
    assert "БЕСПЛАТНО НАВСЕГДА" in md
```

- [ ] **Step 2: Прогони тесты, убедись что падают**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests -q`
Expected: FAIL, 5 новых тестов падают

- [ ] **Step 3: Добавь раздел 8 в `patterns.py`**

Замени сигнатуру и хвост `render_markdown`:

```python
def _thumbs_section(thumbs):
    if not thumbs:
        return []
    out = ["## 8. Текст на превью", ""]
    if thumbs.get("skipped"):
        return out + [thumbs["skipped"], ""]
    out += ["Распознано у %d превью из %d. На превью работает та же ось, что "
            "в тайтле: цена, имя инструмента, конкретика."
            % (thumbs.get("covered", 0), thumbs.get("total", 0)),
            "",
            "| признак на превью | с признаком | без | роликов | надёжно |",
            "|---|---|---|---|---|"]
    for name in sorted(thumbs.get("slices", {})):
        s = thumbs["slices"][name]
        out.append("| %s | %s | %s | %d | %s |" % (
            name,
            "—" if s["median_multiple"] is None else s["median_multiple"],
            "—" if s["median_without"] is None else s["median_without"],
            s["n"], "да" if s["reliable"] else "нет (<%d)" % MIN_GROUP))
    out.append("")
    return out
```

Затем в `render_markdown` смени сигнатуру на `def render_markdown(report, channel, thumbs=None):` и вставь секцию **перед** блоком «Что забираем себе»:

```python
    out += ["## 7. Ритм публикаций", ""] + _table("Роликов в месяц",
                                                  report["rhythm"])
    out += _thumbs_section(thumbs)
    out += ["## Что забираем себе", "",
```

И в `main()` подхвати файл, если он лежит рядом:

```python
    thumbs_path = Path(args.src).parent / ".thumbs.json"
    thumbs = (json.loads(thumbs_path.read_text(encoding="utf-8"))
              if thumbs_path.exists() else None)
    Path(args.out).write_text(
        render_markdown(report, data["channel"], thumbs), encoding="utf-8")
```

- [ ] **Step 4: Добавь секцию в карточку `vault.py`**

В `card_markdown`, в список `body`, после блока `## Описание` вставь:

```python
        "## Текст на превью",
        record.get("thumbnail_text") or "(пусто — прогони режим thumbs)",
        "",
```

И добавь `"## Текст на превью"` в кортеж `KEEP_SECTIONS`, чтобы повторный скаут не затирал уже распознанный текст.

- [ ] **Step 5: Прогони все тесты**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests -q`
Expected: PASS, 93 теста

- [ ] **Step 6: Опиши режим в `SKILL.md`**

В раздел «Три режима» добавь четвёртый — `thumbs`, с текстом:

```markdown
### `thumbs` (Tier-1.5 — текст на превью)

`python3 scripts/fetch_thumbs.py --in "<...>/.channel.json" --out "<...>/.thumbs.json"`
затем перегенерируй разбор: `python3 scripts/patterns.py --in "<...>/.channel.json" --out "<...>/Разбор — тайтлы и паттерны.md"`

Качает превью, снимает текст Apple Vision (локально, бесплатно, ~0.07 с на
превью), считает срез признаков против кратности и добавляет раздел 8 в разбор.

**Превью не хранятся** — качаются во временную папку и стираются после OCR.
**Только macOS** (Vision): нет `swiftc` — режим честно отказывается, остальные
режимы работают.

Что меряем и почему именно это — [references/patterns-reading.md](references/patterns-reading.md).
```

Заголовок раздела поменяй с «Три режима» на «Четыре режима», и в `description` фронтматтера добавь `thumbs` в перечисление режимов.

- [ ] **Step 7: Допиши в `references/patterns-reading.md` раздел про превью**

Содержание: срез читается как остальные (порог 5); на превью подтвердилась та же ось, что в тайтле; **расхожий совет «2–4 слова на превью» на замере опровергнут** — короткие дали 0.89 против 1.27, поэтому длину не оптимизируем вслепую; OCR не видит текст, вшитый в сложный фон, поэтому «пусто» означает «не распозналось», а не «текста не было».

- [ ] **Step 8: Обнови `README.md` скилла**

Добавь `thumbs` в список режимов и в требования — строку про macOS для OCR.

- [ ] **Step 9: Боевой прогон**

```bash
OUT="/Users/wolkart/Yandex.Disk.localized/Obsidian/AI Automation Knowledge Base/2-Контент/Разведка YouTube"
cd skills/youtube-analytics/scripts
python3 fetch_thumbs.py --in "$OUT/VibecoderSchool/.channel.json" --out "$OUT/VibecoderSchool/.thumbs.json"
python3 patterns.py --in "$OUT/VibecoderSchool/.channel.json" --out "$OUT/VibecoderSchool/Разбор — тайтлы и паттерны.md"
```

Expected: `covered` близко к 47; в разборе появился раздел 8; строка «бесплатно» показывает примерно `3.75 / 0.96` при `n=6` — это воспроизведение замера из спеки. Расхождение больше чем на 10% — разбирайся, не подгоняй.

- [ ] **Step 10: Коммит**

```bash
git add skills/youtube-analytics/
git commit -m "youtube-analytics: режим thumbs в отчёте, карточках и SKILL.md"
```

---

# ЭТАП 2 — скилл `youtube-meta`

### Task 4: Каркас скилла и таблица сигналов тайтла

**Files:**
- Create: `skills/youtube-meta/SKILL.md`
- Create: `skills/youtube-meta/references/title-signals.md`

**Interfaces:**
- Consumes: замеры из спеки `2026-08-09-youtube-meta-skill-design.md`
- Produces: скилл, готовый к режиму `СОБРАТЬ` по части тайтла

- [ ] **Step 1: Напиши `SKILL.md`**

Фронтматтер `description` — единственный триггер. Обязан содержать: живые формулировки запроса («напиши тайтл для ролика», «описание под видео», «собери мету», «проверь мету моего ролика», «сделай как у него, но под меня»), и явные границы: НЕ пишет сценарий и вступление, НЕ анализирует каналы (это `youtube-analytics`), НЕ про Shorts (там работает `reels-script`).

Тело: главное правило → дисциплина ответа → три режима → голос посекционно → предохранители → границы → references. Структура повторяет `youtube-analytics/SKILL.md`.

Обязательные формулировки в теле:

```markdown
## Главное правило

Скилл стоит на **замерах, а не на общих канонах**. Каждая рекомендация имеет
степень уверенности: подтверждено на 4 каналах / на 3 / приём одного канала.
Чего не мерили — того не советуем.

**Правила ленты сюда не переносятся.** Лента показывает непрошеное, YouTube
поисковый. Конкретно: запрет `copy-law` на имя инструмента здесь **не
действует** — имя в тайтле работает, потому что это поисковый запрос.
```

- [ ] **Step 2: Напиши `references/title-signals.md`**

Содержание, в этом порядке:

1. **Таблица замеров** — скопировать целиком из спеки (4 канала × 8 признаков, с `n`), с датой снимка 2026-08-09 и пометкой «пересчёт — прогоном `youtube-analytics`, не руками».
2. **Три уровня уверенности:** подтверждено на 4 из 4 («бесплатно», формат курса) → 3 из 4 (имя инструмента, цифра) → стоп-лист.
3. **Стоп-лист с объяснением, а не запретом:** CAPS (у Vibecoder 0.98 против 1.38 — топ-1 канала написан капсом, но капс не причина топа), скобки (разнобой: 1.3 / 0.96 / 0.75 / 1.29), отрицание лидера (у Нейта 0.61 — вредит), тег года (приём одного канала: три остальных не ставят вовсе, поэтому «не работает» про них сказать нельзя).
4. **Как собирать первый тайтл:** максимум подтверждённых сигналов под тему — цена, если она есть в ролике; имя инструмента; формат курса или гайда, если объём тянет; конкретная цифра, если она правдива.
5. **Как собирать второй:** другая дверь при той же теме. Список дверей: цена → результат за время → провал и как выбрался → сравнение двух инструментов → «что я бы учил вместо». **Два похожих тайтла — бессмысленный тест.**
6. **Порядок теста:** первым — с максимумом сигналов; замер первые 48 часов по кратности к медиане своего типа (CTR публичный API не отдаёт); не вышел на планку — ставим второй.
7. **Длина:** ≤100 символов, смысл в первых ~50 (мобильная выдача режет на 48–55).

- [ ] **Step 3: Проверь фронтматтер**

Run: `head -20 skills/youtube-meta/SKILL.md`
Expected: валидный YAML, `name: youtube-meta`, `description` одной логической строкой.

- [ ] **Step 4: Коммит**

```bash
git add skills/youtube-meta/SKILL.md skills/youtube-meta/references/title-signals.md
git commit -m "youtube-meta: каркас скилла и таблица сигналов тайтла"
```

---

### Task 5: Описание, теги, главы, превью

**Files:**
- Create: `skills/youtube-meta/references/description-template.md`
- Create: `skills/youtube-meta/references/tags-chapters-thumbnail.md`

- [ ] **Step 1: Напиши `description-template.md`**

Обязательные части:

1. **Честная рамка:** описание — воронка и SEO-подложка, **не рычаг охвата**. Причинность на нём недоказуема: у Сараева и Нейта первые 125 символов — константа-оффер, одинаковая у топа и у середины, а величина, которая не меняется, не может объяснять разницу между роликами. Рычаг — тайтл и превью.
2. **Скелет с пометкой «константа / меняется»:**
   - хук с ключевиками, ≈125 символов — **меняется** (видно в поиске и под плеером);
   - оффер-ссылка — константа;
   - «если видишь меня впервые» — константа, пишется **голосом автора**;
   - ссылки на свои длинные ролики — константа, обновляется по мере выхода;
   - `Summary ⤵️` с ключевиками — **меняется**;
   - инструменты и партнёрские ссылки — константа;
   - `Chapters` — **меняется**.
3. **Почему хук впереди оффера** (решение автора): на канале в сотню подписчиков сначала нужно, чтобы находили; у Сараева и Нейта оффер первым, потому что трафик уже есть.
4. **Объём:** 200–500 слов ориентировочно; медианы замера — Сараев 2783 символа, Нейт 1350, автор 960.
5. **Запрет:** не обещать того, чего в ролике нет; не сочинять формулировки из транскрипта (транскрипт — источник фактов, не фраз).

- [ ] **Step 2: Напиши `tags-chapters-thumbnail.md`**

Три раздела:

**Теги.** Ориентир 20–40, от общего к частному. Число из медианы Сараева (37). **Прямо сказать: это гигиена, а не рычаг** — у Нейта тегов почти нет (43 ролика из 300) при вдвое большей аудитории. Ставим, потому что бесплатно, а не потому что растит.

**Главы.** Первая метка **обязательно `00:00`** — иначе YouTube создаёт безымянную заглушку `<Untitled Chapter 1>` (реальный случай на ролике автора: главы начинались с 00:19). Минимум 3 главы, каждая от 10 секунд. Замер: у Сараева ролики с главами дают 1.2 против 0.64 без них — но у Нейта разницы нет (0.97 против 1.0), поэтому подаём как «дёшево и вероятно полезно», а не как закон.

**Текст на превью.** Замер (Vibecoder, 47 превью): «бесплатно» 3.75/0.96 (n=6), запрет 1.59/0.98 (n=3), имя платного инструмента 1.31/0.96 (n=16), цифра 1.19/0.72 (n=31). **Отдельно: расхожий совет «2–4 слова» опровергнут** — короткие дали 0.89 против 1.27. Скилл предлагает 2–3 варианта текста из подтверждённых признаков и **не даёт советов по композиции** (лицо, эмоция, контраст) — CTR недоступен, композицию не мерили.

- [ ] **Step 3: Коммит**

```bash
git add skills/youtube-meta/references/
git commit -m "youtube-meta: описание, теги, главы, текст на превью"
```

---

### Task 6: Режим ПЕРЕНОС, упаковка и боевая проверка

**Files:**
- Create: `skills/youtube-meta/references/reference-transfer.md`
- Create: `skills/youtube-meta/README.md`
- Modify: `skills/README.md`

- [ ] **Step 1: Напиши `reference-transfer.md`**

1. **Проверка годности — ДО сборки** (по образцу `carousel-script`). Не переносится: ценность на личном доказательстве автора (скриншоты его заработка, его прогоны, его цифры) и витрина чужих продуктов. Переносится структура, не оболочка. Не проходит — сказать прямо и предложить сменить формат, а не выдавать пустой каркас.
2. **Что разбираем у референса:** из каких сигналов собран тайтл; что стоит в первых 125 символах описания; есть ли главы и с какой метки; текст на превью; порядок битов вступления (какой ход в первые 3 секунды, где обещание, где первое доказательство, на какой секунде появляется результат).
3. **Данные берём делегированием.** Референс уже в базе — берём оттуда; нет — сначала прогон `youtube-analytics` (`scout` для меты, `enrich` для вступления, `thumbs` для превью). **Скрипты соседнего скилла напрямую не вызываем.**
4. **Живой разбор как эталон** — вступление `How to Use Claude Code for FREE (2026)`: 0:00–0:02 тема дословно из тайтла без приветствия → 0:02–0:10 боль в деньгах ($20–200/мес, лимиты) → 0:10–0:29 обещание в цифрах (80–90% качества за 2–5% цены) → 0:29–0:59 доказательство (собранное приложение: «стоило бы $5–10, обошлось в 3 цента»). Пять числовых якорей за минуту, результат показан к 30-й секунде.
5. **Что переносится, а что нет:** переносится порядок битов и наличие числовых якорей; не переносятся сами цифры и сам кейс — их надо заменить своими, иначе выйдет ложь под своим именем.

- [ ] **Step 2: Напиши `README.md` скилла**

По образцу `youtube-analytics/README.md`: зачем, три режима одной строкой каждый, на чём стоит (замеры 5 каналов), чего не делает (не сценарий, не Shorts, не композиция превью, не автопостинг), примеры вызова.

- [ ] **Step 3: Добавь строку в каталог-витрину**

Run: `grep -n "youtube-analytics" skills/README.md`
Добавь строку про `youtube-meta` в том же формате, следующей после `youtube-analytics`.

- [ ] **Step 4: Подключи скилл глобально**

Run: `bash skills/install-skills.sh`
Expected: `+ подключён: youtube-meta`; существующие ссылки не тронуты.

- [ ] **Step 5: Боевая проверка режима `ПРОВЕРИТЬ`**

Прогони скилл на ролике автора `0Sxf4B-KTvA` («Claude Code бесплатно и как собрать на нём первое приложение»).

Expected: скилл находит обе известные поломки — **теги отсутствуют** (0 из 7 роликов канала) и **главы начинаются с 00:19, а не с 00:00**. Не находит хотя бы одну — режим недоделан, чини.

- [ ] **Step 6: Боевая проверка режима `ПЕРЕНОС`**

Прогони на `U6gg_bi1I70` (`How to Use Claude Code for FREE (2026)`) с темой автора.

Expected: референс признан годным (ценность в способе, а не в личном доказательстве); выданы два тайтла с указанием, какой первым; ни в одном месте не всплыл запрет на имя инструмента из `copy-law`.

- [ ] **Step 7: Прогони тесты аналитики ещё раз**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests -q`
Expected: PASS, 93 теста

- [ ] **Step 8: Коммит**

```bash
git add skills/youtube-meta/ skills/README.md
git commit -m "youtube-meta: режим ПЕРЕНОС, упаковка и каталог"
```

---

## Self-Review

**Покрытие спеки.** Этап 1: режим `thumbs` — Task 1–3 (арифметика, скачивание с удалением превью, отказ без macOS, раздел 8, секция карточки, SKILL.md). Копирование OCR вместо межскилловой ссылки — Task 2 Step 1. Этап 2: три режима — Task 4 (СОБРАТЬ, часть тайтла), Task 5 (описание, теги, главы, превью), Task 6 (ПЕРЕНОС, ПРОВЕРИТЬ проверяется боевым прогоном). Голос посекционно — Task 4 Step 1 и Task 5 Step 1. Предохранители — Task 5 Step 1 пункт 5, Task 4 Step 1. Критерии готовности 1–7 покрыты шагами Task 3 Step 9, Task 6 Steps 4–6.

**Плейсхолдеры.** В Task 4–6 шаги описывают состав документов по пунктам с конкретными формулировками и числами, а не готовый текст целиком: это документация, где дословный текст пишется по месту, но состав задан так, что выбора «о чём писать» не остаётся. Ни одного «TBD», «добавь обработку ошибок», «аналогично Task N».

**Согласованность имён.** `thumb_text.parse_ocr_output` / `features` / `word_count` / `slice_by_feature` определены в Task 1 и вызываются под теми же именами в Task 2. Ключи среза (`бесплатно`, `имя инструмента`, `цифра`, `запрет`, `текст ≤4 слов`) заданы в `FEATURES` Task 1 и используются в тестах Task 3. `build()` возвращает `slices` / `texts` / `covered` / `total` / `skipped` — ровно эти ключи читают `patterns._thumbs_section` и тесты Task 3. Поле карточки `thumbnail_text` заведено в Task 3 Step 4 и там же тестируется.

**Число тестов.** 68 сейчас → +14 (Task 1) → 82 → +6 (Task 2) → 88 → +5 (Task 3: три в `test_patterns.py`, два в `test_vault.py`) → **93**. Эти же числа стоят в шагах прогона.
