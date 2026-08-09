# Скилл `youtube-analytics` — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Собрать скилл, который по `@handle` любого публичного YouTube-канала выгружает ролики с метриками в базу волта, ранжирует по кратности к медиане своего типа, считает закономерности и выборочно разбирает вступление роликов.

**Architecture:** Вся арифметика и сеть — в CLI-скриптах на чистом stdlib; `SKILL.md` остаётся оркестрацией. `scout` идёт через Data API v3 (`fetch_channel.py` → `.channel.json`), `patterns` считает офлайн по этому файлу, `enrich` тянет субтитры и Chapters через yt-dlp. Рендер в волт (`vault.py`) повторяет контракт `instagram-analytics`: `index.md` + `cards/<id>.md` + `export.csv` + Obsidian Base, идемпотентно по `id`.

**Tech Stack:** Python 3.9+ (только stdlib: `urllib`, `json`, `csv`, `statistics`, `re`, `datetime`, `subprocess`), yt-dlp как внешний бинарник, YouTube Data API v3, pytest через `uv run --with pytest`.

## Global Constraints

- **Ноль сторонних зависимостей в Python.** Только stdlib. HTTP — `urllib.request`, не `requests`. yt-dlp вызывается через `subprocess`, а не импортируется.
- **Совместимость с Python 3.9.** Системный `python3` на машине автора — 3.9.6. Запрещены `match`, `int | None` в аннотациях, `dict | dict`. Следуй стилю `rough-cut`: аннотаций типов нет вообще.
- **Тесты гоняются командой** `uv run --with pytest pytest skills/youtube-analytics/tests -q` из корня репо.
- **`search.list` не используется никогда** — 100 юнитов из 10 000 и неполная выборка. Список роликов только через плейлист загрузок.
- **Видео не скачиваются никогда.** yt-dlp вызывается только с `--skip-download`.
- **Границы Shorts:** `duration_sec <= 180` → `short`, иначе `long`.
- **Язык кода:** docstring и комментарии — по-русски, как в `rough-cut`. Имена функций и переменных — латиницей.
- **Секреты:** `YOUTUBE_API_KEY` только из `.env` папки скилла или окружения. Ключ **никогда** не печатается в вывод и не попадает в сообщения об ошибках.
- **Никаких выдуманных данных.** Нет поля в ответе API → поле пустое, а не заполненное правдоподобным значением.

---

### Task 1: Метрики — чистая арифметика

**Files:**
- Create: `skills/youtube-analytics/scripts/metrics.py`
- Create: `skills/youtube-analytics/tests/conftest.py`
- Test: `skills/youtube-analytics/tests/test_metrics.py`

**Interfaces:**
- Consumes: ничего (первая задача)
- Produces: `parse_duration(iso)` → int секунд; `classify_kind(duration_sec)` → `"short"`/`"long"`; `medians_by_kind(records)` → `{"short": float, "long": float}`; `median_multiple(views, median)` → float или None; `views_per_day(views, date_iso, today)` → float; `engagement_rate(likes, comments, views)` → float или None; `enrich_records(records, today)` → тот же список с добавленными `median_multiple`, `views_per_day`, `engagement_rate`

- [ ] **Step 1: Создай conftest, чтобы тесты видели скрипты**

```python
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
```

- [ ] **Step 2: Напиши падающие тесты**

```python
import datetime

import metrics


def test_parse_duration_full():
    assert metrics.parse_duration("PT6H2M49S") == 21769


def test_parse_duration_minutes_seconds():
    assert metrics.parse_duration("PT15M53S") == 953


def test_parse_duration_seconds_only():
    assert metrics.parse_duration("PT45S") == 45


def test_parse_duration_with_days():
    assert metrics.parse_duration("P1DT2H") == 93600


def test_parse_duration_garbage_is_zero():
    assert metrics.parse_duration("") == 0
    assert metrics.parse_duration(None) == 0


def test_classify_kind_boundary():
    assert metrics.classify_kind(180) == "short"
    assert metrics.classify_kind(181) == "long"
    assert metrics.classify_kind(45) == "short"


def test_medians_by_kind_separates_types():
    records = [
        {"kind": "short", "views": 100},
        {"kind": "short", "views": 300},
        {"kind": "long", "views": 1000},
        {"kind": "long", "views": 3000},
        {"kind": "long", "views": 5000},
    ]
    result = metrics.medians_by_kind(records)
    assert result["short"] == 200
    assert result["long"] == 3000


def test_medians_by_kind_missing_type():
    result = metrics.medians_by_kind([{"kind": "long", "views": 10}])
    assert result["long"] == 10
    assert result["short"] is None


def test_median_multiple_rounds():
    assert metrics.median_multiple(3000, 1200) == 2.5


def test_median_multiple_zero_median_is_none():
    assert metrics.median_multiple(3000, 0) is None
    assert metrics.median_multiple(3000, None) is None


def test_views_per_day_minimum_one_day():
    today = datetime.date(2026, 8, 9)
    # опубликовано сегодня — делим на 1 день, а не на 0
    assert metrics.views_per_day(500, "2026-08-09", today) == 500.0


def test_views_per_day_counts_elapsed():
    today = datetime.date(2026, 8, 9)
    assert metrics.views_per_day(1000, "2026-07-30", today) == 100.0


def test_engagement_rate():
    assert metrics.engagement_rate(80, 20, 10000) == 0.01


def test_engagement_rate_no_views_is_none():
    assert metrics.engagement_rate(80, 20, 0) is None


def test_enrich_records_adds_all_derived_fields():
    today = datetime.date(2026, 8, 9)
    records = [
        {"id": "a", "kind": "long", "views": 3000, "likes": 100,
         "comments": 50, "date": "2026-07-30"},
        {"id": "b", "kind": "long", "views": 1000, "likes": 10,
         "comments": 5, "date": "2026-07-30"},
    ]
    out = metrics.enrich_records(records, today)
    assert out[0]["median_multiple"] == 1.5
    assert out[1]["median_multiple"] == 0.5
    assert out[0]["views_per_day"] == 300.0
    assert out[0]["engagement_rate"] == 0.05
```

- [ ] **Step 3: Прогони тесты, убедись что падают**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_metrics.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'metrics'`

- [ ] **Step 4: Реализуй `metrics.py`**

```python
#!/usr/bin/env python3
"""Арифметика разведки: длительность, тип ролика, медианы, кратности. Только stdlib."""
import datetime
import re
import statistics

SHORT_MAX_SEC = 180

_DUR = re.compile(
    r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
)


def parse_duration(iso):
    """ISO 8601 из contentDetails.duration → секунды. Мусор → 0."""
    if not iso:
        return 0
    m = _DUR.fullmatch(iso.strip())
    if not m:
        return 0
    days, hours, mins, secs = (int(g) if g else 0 for g in m.groups())
    return days * 86400 + hours * 3600 + mins * 60 + secs


def classify_kind(duration_sec):
    """Граница эвристическая: YouTube поднимал лимит Shorts до 3 минут."""
    return "short" if duration_sec <= SHORT_MAX_SEC else "long"


def medians_by_kind(records):
    """Медиана просмотров ОТДЕЛЬНО по каждому типу — иначе шорты топят длинные."""
    out = {}
    for kind in ("short", "long"):
        views = [r["views"] for r in records if r.get("kind") == kind
                 and r.get("views") is not None]
        out[kind] = statistics.median(views) if views else None
    return out


def median_multiple(views, median):
    """Во сколько раз ролик обогнал медиану своего типа."""
    if not median:
        return None
    return round(views / median, 2)


def views_per_day(views, date_iso, today=None):
    """Скорость набора. Минимум 1 день, чтобы вчерашний ролик не улетал в бесконечность."""
    today = today or datetime.date.today()
    published = datetime.date.fromisoformat(date_iso[:10])
    days = max((today - published).days, 1)
    return round(views / days, 2)


def engagement_rate(likes, comments, views):
    if not views:
        return None
    return round(((likes or 0) + (comments or 0)) / views, 4)


def enrich_records(records, today=None):
    """Дописывает производные поля в записи (на месте) и возвращает список."""
    medians = medians_by_kind(records)
    for r in records:
        r["median_multiple"] = median_multiple(
            r.get("views") or 0, medians.get(r.get("kind")))
        r["views_per_day"] = views_per_day(
            r.get("views") or 0, r["date"], today)
        r["engagement_rate"] = engagement_rate(
            r.get("likes"), r.get("comments"), r.get("views") or 0)
    return records
```

- [ ] **Step 5: Прогони тесты**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_metrics.py -q`
Expected: PASS, 15 тестов

- [ ] **Step 6: Коммит**

```bash
git add skills/youtube-analytics/scripts/metrics.py skills/youtube-analytics/tests/
git commit -m "youtube-analytics: арифметика разведки (медианы по типу, кратность)"
```

---

### Task 2: Клиент YouTube Data API

**Files:**
- Create: `skills/youtube-analytics/scripts/yt_api.py`
- Test: `skills/youtube-analytics/tests/test_yt_api.py`

**Interfaces:**
- Consumes: ничего из Task 1
- Produces: `chunked(items, size)` → генератор списков; `resolve_channel(payload)` → `{"channel_id", "title", "handle", "subscribers", "uploads_playlist"}`; `parse_playlist_page(payload)` → `(["videoId", ...], next_token)`; `parse_videos(payload)` → список сырых записей; `best_thumbnail(thumbnails)` → url; `parse_comments(payload)` → список `{"text", "likes", "author"}`; `api_get(endpoint, params, key, opener)` → dict. Все парсеры — чистые функции от готового JSON, сеть только в `api_get`.

- [ ] **Step 1: Напиши падающие тесты**

```python
import json

import pytest

import yt_api


def test_chunked_splits_by_fifty():
    items = list(range(120))
    chunks = list(yt_api.chunked(items, 50))
    assert [len(c) for c in chunks] == [50, 50, 20]


def test_chunked_empty():
    assert list(yt_api.chunked([], 50)) == []


def test_resolve_channel_reads_uploads_playlist():
    payload = {"items": [{
        "id": "UCabc",
        "snippet": {"title": "Nick Saraev", "customUrl": "@nicksaraev"},
        "statistics": {"subscriberCount": "492000"},
        "contentDetails": {"relatedPlaylists": {"uploads": "UUabc"}},
    }]}
    ch = yt_api.resolve_channel(payload)
    assert ch["channel_id"] == "UCabc"
    assert ch["handle"] == "nicksaraev"
    assert ch["subscribers"] == 492000
    assert ch["uploads_playlist"] == "UUabc"


def test_resolve_channel_empty_raises():
    with pytest.raises(LookupError):
        yt_api.resolve_channel({"items": []})


def test_resolve_channel_hidden_subscribers():
    payload = {"items": [{
        "id": "UCx", "snippet": {"title": "T", "customUrl": "@x"},
        "statistics": {},
        "contentDetails": {"relatedPlaylists": {"uploads": "UUx"}},
    }]}
    assert yt_api.resolve_channel(payload)["subscribers"] is None


def test_parse_playlist_page_returns_ids_and_token():
    payload = {
        "items": [
            {"contentDetails": {"videoId": "aaa"}},
            {"contentDetails": {"videoId": "bbb"}},
        ],
        "nextPageToken": "TOKEN2",
    }
    ids, token = yt_api.parse_playlist_page(payload)
    assert ids == ["aaa", "bbb"]
    assert token == "TOKEN2"


def test_parse_playlist_page_last_page_has_no_token():
    ids, token = yt_api.parse_playlist_page(
        {"items": [{"contentDetails": {"videoId": "z"}}]})
    assert token is None


def test_best_thumbnail_prefers_maxres():
    thumbs = {"default": {"url": "d"}, "high": {"url": "h"},
              "maxres": {"url": "m"}}
    assert yt_api.best_thumbnail(thumbs) == "m"


def test_best_thumbnail_falls_back():
    assert yt_api.best_thumbnail({"default": {"url": "d"}}) == "d"
    assert yt_api.best_thumbnail({}) == ""


def test_parse_videos_maps_fields():
    payload = {"items": [{
        "id": "vid1",
        "snippet": {
            "publishedAt": "2026-07-24T14:00:00Z",
            "title": "I Spent $400 Benching Opus-5",
            "description": "line one\n00:00 Intro\n01:20 Demo",
            "tags": ["ai", "claude"],
            "thumbnails": {"high": {"url": "http://t/h.jpg"}},
        },
        "statistics": {"viewCount": "62875", "likeCount": "1577",
                       "commentCount": "165"},
        "contentDetails": {"duration": "PT15M53S"},
    }]}
    rows = yt_api.parse_videos(payload)
    assert len(rows) == 1
    r = rows[0]
    assert r["id"] == "vid1"
    assert r["title"] == "I Spent $400 Benching Opus-5"
    assert r["date"] == "2026-07-24"
    assert r["views"] == 62875
    assert r["likes"] == 1577
    assert r["comments"] == 165
    assert r["duration_sec"] == 953
    assert r["kind"] == "long"
    assert r["tags"] == ["ai", "claude"]
    assert r["thumbnail_url"] == "http://t/h.jpg"
    assert r["url"] == "https://www.youtube.com/watch?v=vid1"


def test_parse_videos_hidden_likes_are_none():
    payload = {"items": [{
        "id": "v2",
        "snippet": {"publishedAt": "2026-01-01T00:00:00Z", "title": "t",
                    "description": "", "thumbnails": {}},
        "statistics": {"viewCount": "10"},
        "contentDetails": {"duration": "PT30S"},
    }]}
    r = yt_api.parse_videos(payload)[0]
    assert r["likes"] is None
    assert r["comments"] is None
    assert r["tags"] == []
    assert r["kind"] == "short"


def test_parse_comments_sorts_by_likes():
    payload = {"items": [
        {"snippet": {"topLevelComment": {"snippet": {
            "textOriginal": "мало", "likeCount": 2,
            "authorDisplayName": "a"}}}},
        {"snippet": {"topLevelComment": {"snippet": {
            "textOriginal": "много", "likeCount": 40,
            "authorDisplayName": "b"}}}},
    ]}
    out = yt_api.parse_comments(payload)
    assert [c["text"] for c in out] == ["много", "мало"]
    assert out[0]["likes"] == 40


def test_api_get_builds_url_and_never_leaks_key(monkeypatch):
    seen = {}

    def fake_opener(url, timeout=None):
        seen["url"] = url

        class R:
            def read(self):
                return json.dumps({"ok": True}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return R()

    data = yt_api.api_get("videos", {"id": "abc"}, "SECRETKEY",
                          opener=fake_opener)
    assert data == {"ok": True}
    assert "youtube/v3/videos" in seen["url"]
    assert "id=abc" in seen["url"]
    assert "key=SECRETKEY" in seen["url"]
    # ключ в URL нужен, но в человекочитаемой ошибке его быть не должно
    assert "SECRETKEY" not in yt_api.safe_url(seen["url"])
```

- [ ] **Step 2: Прогони тесты, убедись что падают**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_yt_api.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'yt_api'`

- [ ] **Step 3: Реализуй `yt_api.py`**

```python
#!/usr/bin/env python3
"""Клиент YouTube Data API v3. Только stdlib.

Парсеры — чистые функции от готового JSON, сеть живёт только в api_get:
так всё тестируется без единого сетевого вызова.

search.list НЕ используется: 100 юнитов из 10 000 и неполная выборка.
Список роликов берётся через плейлист загрузок канала.
"""
import json
import re
import urllib.parse
import urllib.request

import metrics

BASE = "https://www.googleapis.com/youtube/v3"
TIMEOUT = 30
THUMB_ORDER = ("maxres", "standard", "high", "medium", "default")


def safe_url(url):
    """URL без ключа — для логов и сообщений об ошибках."""
    return re.sub(r"key=[^&]+", "key=***", url)


def api_get(endpoint, params, key, opener=None):
    """GET к Data API. opener подменяется в тестах."""
    opener = opener or urllib.request.urlopen
    query = dict(params)
    query["key"] = key
    url = BASE + "/" + endpoint + "?" + urllib.parse.urlencode(query)
    try:
        with opener(url, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(
            "запрос к " + safe_url(url) + " не прошёл: " + str(exc))


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _int_or_none(value):
    return int(value) if value not in (None, "") else None


def resolve_channel(payload):
    items = payload.get("items") or []
    if not items:
        raise LookupError("канал не найден: проверь @handle")
    it = items[0]
    snippet = it.get("snippet", {})
    return {
        "channel_id": it.get("id", ""),
        "title": snippet.get("title", ""),
        "handle": (snippet.get("customUrl", "") or "").lstrip("@"),
        "subscribers": _int_or_none(
            it.get("statistics", {}).get("subscriberCount")),
        "uploads_playlist": it.get("contentDetails", {})
                              .get("relatedPlaylists", {}).get("uploads", ""),
    }


def parse_playlist_page(payload):
    ids = [i["contentDetails"]["videoId"]
           for i in payload.get("items", [])
           if i.get("contentDetails", {}).get("videoId")]
    return ids, payload.get("nextPageToken")


def best_thumbnail(thumbnails):
    for name in THUMB_ORDER:
        url = (thumbnails or {}).get(name, {}).get("url")
        if url:
            return url
    return ""


def parse_videos(payload):
    rows = []
    for it in payload.get("items", []):
        snippet = it.get("snippet", {})
        stats = it.get("statistics", {})
        duration_sec = metrics.parse_duration(
            it.get("contentDetails", {}).get("duration"))
        rows.append({
            "id": it.get("id", ""),
            "title": snippet.get("title", ""),
            "url": "https://www.youtube.com/watch?v=" + it.get("id", ""),
            "date": (snippet.get("publishedAt", "") or "")[:10],
            "description": snippet.get("description", ""),
            "tags": snippet.get("tags", []) or [],
            "thumbnail_url": best_thumbnail(snippet.get("thumbnails")),
            "duration_sec": duration_sec,
            "kind": metrics.classify_kind(duration_sec),
            "views": int(stats.get("viewCount", 0) or 0),
            "likes": _int_or_none(stats.get("likeCount")),
            "comments": _int_or_none(stats.get("commentCount")),
        })
    return rows


def parse_comments(payload):
    out = []
    for it in payload.get("items", []):
        top = (it.get("snippet", {})
                 .get("topLevelComment", {}).get("snippet", {}))
        out.append({
            "text": top.get("textOriginal", ""),
            "likes": int(top.get("likeCount", 0) or 0),
            "author": top.get("authorDisplayName", ""),
        })
    out.sort(key=lambda c: c["likes"], reverse=True)
    return out
```

- [ ] **Step 4: Прогони тесты**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_yt_api.py -q`
Expected: PASS, 13 тестов

- [ ] **Step 5: Коммит**

```bash
git add skills/youtube-analytics/scripts/yt_api.py skills/youtube-analytics/tests/test_yt_api.py
git commit -m "youtube-analytics: клиент Data API (парсеры отдельно от сети)"
```

---

### Task 3: `fetch_channel.py` — режим scout

**Files:**
- Create: `skills/youtube-analytics/scripts/fetch_channel.py`
- Create: `skills/youtube-analytics/.env.template`
- Test: `skills/youtube-analytics/tests/test_fetch_channel.py`

**Interfaces:**
- Consumes: `yt_api.*`, `metrics.enrich_records`
- Produces: `read_env(path)` → dict; `require_key(env)` → строка ключа; `collect(handle, key, limit, getter)` → `{"channel": {...}, "videos": [...], "quota_units": int}`; CLI `python3 fetch_channel.py @handle --limit 300 --out path.json`

- [ ] **Step 1: Напиши падающие тесты**

```python
import json

import pytest

import fetch_channel


def test_read_env_ignores_comments_and_quotes(tmp_path):
    p = tmp_path / ".env"
    p.write_text(
        '# комментарий\n'
        'YOUTUBE_API_KEY="abc 123"\n'
        "YT_OUTPUT_DIR=/path/with space/dir\n"
        "\n",
        encoding="utf-8")
    env = fetch_channel.read_env(p)
    assert env["YOUTUBE_API_KEY"] == "abc 123"
    assert env["YT_OUTPUT_DIR"] == "/path/with space/dir"


def test_read_env_missing_file_is_empty(tmp_path):
    assert fetch_channel.read_env(tmp_path / "нет.env") == {}


def test_require_key_raises_with_instruction():
    with pytest.raises(SystemExit) as exc:
        fetch_channel.require_key({})
    assert "YOUTUBE_API_KEY" in str(exc.value)


def _fake_getter(pages):
    """Отдаёт заранее заготовленные ответы по порядку вызовов."""
    calls = []

    def getter(endpoint, params, key):
        calls.append((endpoint, params))
        return pages.pop(0)
    getter.calls = calls
    return getter


def test_collect_walks_playlist_and_counts_quota():
    channel_page = {"items": [{
        "id": "UCx", "snippet": {"title": "T", "customUrl": "@t"},
        "statistics": {"subscriberCount": "100"},
        "contentDetails": {"relatedPlaylists": {"uploads": "UUx"}},
    }]}
    playlist_page1 = {
        "items": [{"contentDetails": {"videoId": "v1"}},
                  {"contentDetails": {"videoId": "v2"}}],
        "nextPageToken": "T2",
    }
    playlist_page2 = {"items": [{"contentDetails": {"videoId": "v3"}}]}

    def video_item(vid, dur, views):
        return {
            "id": vid,
            "snippet": {"publishedAt": "2026-07-01T00:00:00Z", "title": vid,
                        "description": "", "thumbnails": {}},
            "statistics": {"viewCount": str(views), "likeCount": "1",
                           "commentCount": "1"},
            "contentDetails": {"duration": dur},
        }

    videos_page = {"items": [video_item("v1", "PT10M", 1000),
                             video_item("v2", "PT10M", 3000),
                             video_item("v3", "PT30S", 500)]}

    getter = _fake_getter([channel_page, playlist_page1,
                           playlist_page2, videos_page])
    result = fetch_channel.collect("@t", "KEY", limit=300, getter=getter)

    assert result["channel"]["handle"] == "t"
    assert len(result["videos"]) == 3
    # 1 channels + 2 playlistItems + 1 videos
    assert result["quota_units"] == 4
    # производные поля посчитаны, медианы раздельные
    by_id = {v["id"]: v for v in result["videos"]}
    assert by_id["v2"]["median_multiple"] == 1.5
    assert by_id["v3"]["median_multiple"] == 1.0
    # search.list не вызывался ни разу
    assert all(ep != "search" for ep, _ in getter.calls)


def test_collect_respects_limit():
    channel_page = {"items": [{
        "id": "UCx", "snippet": {"title": "T", "customUrl": "@t"},
        "statistics": {}, "contentDetails": {
            "relatedPlaylists": {"uploads": "UUx"}}}]}
    playlist_page = {
        "items": [{"contentDetails": {"videoId": "v%d" % i}}
                  for i in range(50)],
        "nextPageToken": "MORE",
    }
    videos_page = {"items": [{
        "id": "v0",
        "snippet": {"publishedAt": "2026-07-01T00:00:00Z", "title": "v0",
                    "description": "", "thumbnails": {}},
        "statistics": {"viewCount": "10"},
        "contentDetails": {"duration": "PT10M"}}]}
    getter = _fake_getter([channel_page, playlist_page, videos_page])
    result = fetch_channel.collect("@t", "KEY", limit=2, getter=getter)
    # лимит обрезает список id ДО запроса videos — вторая страница не берётся
    assert len(getter.calls) == 3
    assert result["requested_limit"] == 2
```

- [ ] **Step 2: Прогони тесты, убедись что падают**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_fetch_channel.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_channel'`

- [ ] **Step 3: Реализуй `fetch_channel.py`**

```python
#!/usr/bin/env python3
"""scout: канал → нормализованный .channel.json. Только stdlib.

Квота: channels 1 + playlistItems 1/страница + videos 1/пачка.
Канал на 300 роликов ≈ 14 юнитов из 10 000.
"""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

import metrics
import yt_api

PAGE = 50


def read_env(path):
    """Читает .env БЕЗ source: zsh ломается на значениях с пробелами."""
    env = {}
    path = Path(path)
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        env[name.strip()] = value.strip().strip('"').strip("'")
    return env


def require_key(env):
    key = env.get("YOUTUBE_API_KEY") or os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise SystemExit(
            "нет YOUTUBE_API_KEY. Заведи ключ в Google Cloud "
            "(включи YouTube Data API v3) и положи в "
            "skills/youtube-analytics/.env")
    return key


def collect(handle, key, limit=300, getter=None, today=None):
    """Собирает канал целиком. getter подменяется в тестах."""
    getter = getter or (lambda ep, p, k: yt_api.api_get(ep, p, k))
    units = 0

    handle_clean = handle.lstrip("@")
    channel = yt_api.resolve_channel(
        getter("channels",
               {"part": "snippet,statistics,contentDetails",
                "forHandle": "@" + handle_clean}, key))
    units += 1

    video_ids = []
    token = None
    while len(video_ids) < limit:
        params = {"part": "contentDetails",
                  "playlistId": channel["uploads_playlist"],
                  "maxResults": PAGE}
        if token:
            params["pageToken"] = token
        page = getter("playlistItems", params, key)
        units += 1
        ids, token = yt_api.parse_playlist_page(page)
        video_ids.extend(ids)
        if not token:
            break
    video_ids = video_ids[:limit]

    videos = []
    for batch in yt_api.chunked(video_ids, PAGE):
        page = getter("videos",
                      {"part": "snippet,statistics,contentDetails",
                       "id": ",".join(batch)}, key)
        units += 1
        videos.extend(yt_api.parse_videos(page))

    metrics.enrich_records(videos, today)
    videos.sort(key=lambda v: (v.get("median_multiple") or 0), reverse=True)

    return {
        "channel": channel,
        "videos": videos,
        "quota_units": units,
        "requested_limit": limit,
        "collected_at": (today or datetime.date.today()).isoformat(),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="scout канала YouTube")
    ap.add_argument("handle", help="@handle канала")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--out", required=True, help="куда писать .channel.json")
    ap.add_argument("--env", default=str(
        Path(__file__).parent.parent / ".env"))
    args = ap.parse_args(argv)

    key = require_key(read_env(args.env))
    result = collect(args.handle, key, args.limit)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(json.dumps({
        "channel": result["channel"]["title"],
        "videos": len(result["videos"]),
        "quota_units": result["quota_units"],
        "out": str(out),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Прогони тесты**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_fetch_channel.py -q`
Expected: PASS, 5 тестов

- [ ] **Step 5: Создай `.env.template`**

```bash
# YouTube Data API v3 — ключ из Google Cloud Console.
# Включи "YouTube Data API v3" в проекте: https://console.cloud.google.com/apis/credentials
YOUTUBE_API_KEY=

# Куда складывать разведку. Мостик в Obsidian-волт.
# Дефолт, если пусто: ./youtube-analytics-output
YT_OUTPUT_DIR=
```

- [ ] **Step 6: Убедись, что `.env` не попадёт в git**

Run: `grep -n "env" /Users/wolkart/AI/aifuture_hub/.gitignore`
Expected: строка, покрывающая `skills/*/.env`. Если её нет — добавь `skills/*/.env` в `.gitignore` и включи файл в коммит.

- [ ] **Step 7: Коммит**

```bash
git add skills/youtube-analytics/scripts/fetch_channel.py \
        skills/youtube-analytics/tests/test_fetch_channel.py \
        skills/youtube-analytics/.env.template .gitignore
git commit -m "youtube-analytics: режим scout — канал в .channel.json"
```

---

### Task 4: `patterns.py` — семь срезов

**Files:**
- Create: `skills/youtube-analytics/scripts/patterns.py`
- Test: `skills/youtube-analytics/tests/test_patterns.py`

**Interfaces:**
- Consumes: `.channel.json` из Task 3
- Produces: `has_timecodes(description)` → bool; `title_features(title)` → dict флагов; `bucket(value, edges)` → строка-ярлык; `slice_stats(records, key_fn)` → `{ярлык: {"n", "median_multiple", "reliable"}}`; `by_month(records)` → срез по месяцам; `build_report(data)` → dict всех семи срезов; `render_markdown(report, channel)` → строка; CLI `python3 patterns.py --in .channel.json --out "Разбор — тайтлы и паттерны.md"`

**Порог надёжности:** группа меньше 5 роликов помечается `reliable: false` и в выводах не участвует — иначе один удачный ролик становится «закономерностью».

- [ ] **Step 1: Напиши падающие тесты**

```python
import patterns


def test_has_timecodes_detects_chapter_block():
    desc = "Мой канал\n00:00 Intro\n01:20 Demo\n05:00 Итог"
    assert patterns.has_timecodes(desc) is True


def test_has_timecodes_ignores_inline_time():
    assert patterns.has_timecodes("это заняло 10:30 утра, представь") is False


def test_has_timecodes_needs_two_marks():
    assert patterns.has_timecodes("00:00 Intro") is False


def test_title_features_flags():
    f = patterns.title_features("I Spent $400 Benching Opus-5 (2026)")
    assert f["has_digit"] is True
    assert f["has_year_tag"] is True
    assert f["has_brackets"] is True
    assert f["has_question"] is False


def test_title_features_caps_word():
    assert patterns.title_features("CLAUDE CODE FULL COURSE")["has_caps"] is True
    assert patterns.title_features("Claude Code course")["has_caps"] is False


def test_title_features_short_caps_not_counted():
    # аббревиатуры вроде AI/API — не «капслок-приём»
    assert patterns.title_features("What is AI now")["has_caps"] is False


def test_bucket_picks_range():
    edges = [(0, 40, "≤40"), (41, 60, "41–60"), (61, 9999, "61+")]
    assert patterns.bucket(35, edges) == "≤40"
    assert patterns.bucket(41, edges) == "41–60"
    assert patterns.bucket(900, edges) == "61+"


def test_slice_stats_marks_small_groups_unreliable():
    records = [{"median_multiple": 1.0, "g": "a"}] * 3 + \
              [{"median_multiple": 2.0, "g": "b"}] * 6
    stats = patterns.slice_stats(records, lambda r: r["g"])
    assert stats["a"]["n"] == 3
    assert stats["a"]["reliable"] is False
    assert stats["b"]["n"] == 6
    assert stats["b"]["reliable"] is True
    assert stats["b"]["median_multiple"] == 2.0


def test_by_month_separates_kinds():
    records = [
        {"date": "2026-07-02", "kind": "long", "views": 100},
        {"date": "2026-07-20", "kind": "long", "views": 300},
        {"date": "2026-07-05", "kind": "short", "views": 1000},
        {"date": "2026-06-01", "kind": "long", "views": 50},
    ]
    out = patterns.by_month(records)
    assert out["2026-07"]["long"]["median_views"] == 200
    assert out["2026-07"]["short"]["median_views"] == 1000
    assert out["2026-06"]["long"]["n"] == 1


def test_build_report_has_all_seven_slices():
    data = {
        "channel": {"title": "T", "handle": "t", "subscribers": 1000},
        "videos": [
            {"id": "v%d" % i, "title": "Заголовок номер %d" % i,
             "date": "2026-07-%02d" % (i + 1), "kind": "long",
             "views": 100 * (i + 1), "duration_sec": 600,
             "description": "00:00 a\n01:00 b", "median_multiple": 1.0 * i,
             "engagement_rate": 0.01, "views_per_day": 10.0}
            for i in range(12)
        ],
    }
    report = patterns.build_report(data)
    for key in ("by_month", "title_length", "title_composition",
                "duration", "description", "extremes", "rhythm"):
        assert key in report
    assert len(report["extremes"]["top"]) <= 15
    assert len(report["extremes"]["bottom"]) <= 15


def test_render_markdown_ends_with_takeaways_section():
    data = {"channel": {"title": "T", "handle": "t", "subscribers": 1},
            "videos": [{"id": "a", "title": "t", "date": "2026-07-01",
                        "kind": "long", "views": 10, "duration_sec": 600,
                        "description": "", "median_multiple": 1.0,
                        "engagement_rate": 0.01, "views_per_day": 1.0}]}
    md = patterns.render_markdown(patterns.build_report(data), data["channel"])
    assert "## Что забираем себе" in md
    # секция «Что забираем себе» — последняя, её не перекрывают другие срезы
    assert md.index("## Что забираем себе") > md.index("## 7. Ритм публикаций")
```

- [ ] **Step 2: Прогони тесты, убедись что падают**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_patterns.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'patterns'`

- [ ] **Step 3: Реализуй `patterns.py`**

```python
#!/usr/bin/env python3
"""patterns: закономерности канала по уже собранным метрикам. Только stdlib.

Считает офлайн по .channel.json — к API не обращается, квоту не тратит.
Группа меньше MIN_GROUP роликов помечается ненадёжной: один удачный ролик
не должен превращаться в «закономерность».
"""
import argparse
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

MIN_GROUP = 5
TOP_N = 15

TITLE_LEN_EDGES = [(0, 40, "≤40"), (41, 60, "41–60"),
                   (61, 80, "61–80"), (81, 9999, "81+")]
DURATION_EDGES = [(0, 180, "Shorts ≤3мин"), (181, 480, "3–8 мин"),
                  (481, 900, "8–15 мин"), (901, 1800, "15–30 мин"),
                  (1801, 999999, "30+ мин")]
DESC_LEN_EDGES = [(0, 300, "≤300"), (301, 800, "301–800"),
                  (801, 2000, "801–2000"), (2001, 999999, "2000+")]

_TIMECODE_LINE = re.compile(r"^\s*\d{1,2}:\d{2}(?::\d{2})?\s+\S", re.M)
_YEAR_TAG = re.compile(r"\((?:19|20)\d{2}\)")
_CAPS_WORD = re.compile(r"\b[A-ZА-ЯЁ]{4,}\b")


def has_timecodes(description):
    """Блок глав = минимум две строки, начинающиеся с таймкода."""
    return len(_TIMECODE_LINE.findall(description or "")) >= 2


def title_features(title):
    title = title or ""
    return {
        "has_digit": any(ch.isdigit() for ch in title),
        "has_year_tag": bool(_YEAR_TAG.search(title)),
        "has_brackets": ("(" in title) or ("[" in title),
        "has_caps": bool(_CAPS_WORD.search(title)),
        "has_question": "?" in title,
    }


def bucket(value, edges):
    for low, high, label in edges:
        if low <= value <= high:
            return label
    return edges[-1][2]


def _median_mult(records):
    vals = [r["median_multiple"] for r in records
            if r.get("median_multiple") is not None]
    return round(statistics.median(vals), 2) if vals else None


def slice_stats(records, key_fn):
    groups = defaultdict(list)
    for r in records:
        groups[key_fn(r)].append(r)
    return {
        label: {
            "n": len(rows),
            "median_multiple": _median_mult(rows),
            "reliable": len(rows) >= MIN_GROUP,
        }
        for label, rows in groups.items()
    }


def by_month(records):
    out = defaultdict(lambda: defaultdict(list))
    for r in records:
        out[r["date"][:7]][r["kind"]].append(r["views"])
    return {
        month: {
            kind: {"n": len(views),
                   "median_views": statistics.median(views),
                   "reliable": len(views) >= MIN_GROUP}
            for kind, views in kinds.items()
        }
        for month, kinds in out.items()
    }


def _composition_slices(videos):
    out = {}
    for flag in ("has_digit", "has_year_tag", "has_brackets",
                 "has_caps", "has_question"):
        out[flag] = slice_stats(
            videos, lambda r, f=flag: "да" if title_features(r["title"])[f]
            else "нет")
    return out


def build_report(data):
    videos = data["videos"]
    ranked = [v for v in videos if v.get("median_multiple") is not None]
    ranked.sort(key=lambda v: v["median_multiple"], reverse=True)

    def extreme(rows):
        return [{"title": v["title"], "kind": v["kind"],
                 "views": v["views"],
                 "median_multiple": v["median_multiple"],
                 "url": v.get("url", "")} for v in rows]

    return {
        "total": len(videos),
        "by_kind": {k: sum(1 for v in videos if v["kind"] == k)
                    for k in ("short", "long")},
        "by_month": by_month(videos),
        "title_length": slice_stats(
            videos, lambda r: bucket(len(r["title"]), TITLE_LEN_EDGES)),
        "title_composition": _composition_slices(videos),
        "duration": slice_stats(
            videos, lambda r: bucket(r["duration_sec"], DURATION_EDGES)),
        "description": {
            "length": slice_stats(
                videos,
                lambda r: bucket(len(r.get("description") or ""),
                                 DESC_LEN_EDGES)),
            "timecodes": slice_stats(
                videos,
                lambda r: "есть главы" if has_timecodes(r.get("description"))
                else "нет глав"),
        },
        "extremes": {"top": extreme(ranked[:TOP_N]),
                     "bottom": extreme(ranked[-TOP_N:][::-1])},
        "rhythm": slice_stats(videos, lambda r: r["date"][:7]),
    }


def _table(title, stats):
    lines = ["### " + title, "",
             "| группа | роликов | медианная кратность | надёжно |",
             "|---|---|---|---|"]
    for label in sorted(stats, key=lambda k: str(k)):
        s = stats[label]
        lines.append("| %s | %d | %s | %s |" % (
            label, s["n"],
            "—" if s["median_multiple"] is None else s["median_multiple"],
            "да" if s["reliable"] else "нет (<%d)" % MIN_GROUP))
    lines.append("")
    return lines


def render_markdown(report, channel):
    out = [
        "# Разбор — тайтлы и паттерны: %s" % channel.get("title", ""),
        "",
        "Канал: `@%s` · подписчиков: %s · роликов в выборке: %d "
        "(Shorts %d / длинных %d)" % (
            channel.get("handle", ""),
            channel.get("subscribers") if channel.get("subscribers")
            is not None else "скрыто",
            report["total"], report["by_kind"]["short"],
            report["by_kind"]["long"]),
        "",
        "Кратность = просмотры / медиана СВОЕГО типа. Группы меньше %d "
        "роликов помечены ненадёжными — на них выводы не строим." % MIN_GROUP,
        "",
    ]

    out += ["## 1. Медиана просмотров по месяцам", "",
            "| месяц | тип | роликов | медиана просмотров | надёжно |",
            "|---|---|---|---|---|"]
    for month in sorted(report["by_month"], reverse=True):
        for kind, s in sorted(report["by_month"][month].items()):
            out.append("| %s | %s | %d | %d | %s |" % (
                month, kind, s["n"], s["median_views"],
                "да" if s["reliable"] else "нет"))
    out.append("")

    out += ["## 2. Длина тайтла", ""] + _table("Символов в тайтле",
                                               report["title_length"])
    out += ["## 3. Состав тайтла", ""]
    names = {"has_digit": "Цифра в тайтле",
             "has_year_tag": "Тег свежести (год)",
             "has_brackets": "Скобки",
             "has_caps": "CAPS-слово",
             "has_question": "Вопрос"}
    for flag, stats in report["title_composition"].items():
        out += _table(names[flag], stats)

    out += ["## 4. Длительность", ""] + _table("Длительность",
                                               report["duration"])
    out += ["## 5. Описание", ""]
    out += _table("Длина описания", report["description"]["length"])
    out += _table("Блок глав в описании", report["description"]["timecodes"])

    out += ["## 6. Верх и низ по кратности", "",
            "Здесь смотрим глазами: механику тайтла посчитать нельзя, "
            "её видно только на контрасте верха и низа.", ""]
    for label, rows in (("Топ", report["extremes"]["top"]),
                        ("Дно", report["extremes"]["bottom"])):
        out += ["### %s-%d" % (label, TOP_N), "",
                "| кратность | тип | просмотры | тайтл |", "|---|---|---|---|"]
        for r in rows:
            out.append("| %s | %s | %d | %s |" % (
                r["median_multiple"], r["kind"], r["views"],
                r["title"].replace("|", "\\|")))
        out.append("")

    out += ["## 7. Ритм публикаций", ""] + _table("Роликов в месяц",
                                                  report["rhythm"])
    out += ["## Что забираем себе", "",
            "_Заполняется руками после чтения срезов выше: "
            "механика тайтлов из топа, что НЕ повторять из дна, "
            "рабочая длительность и ритм._", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="patterns по .channel.json")
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    data = json.loads(Path(args.src).read_text(encoding="utf-8"))
    report = build_report(data)
    Path(args.out).write_text(
        render_markdown(report, data["channel"]), encoding="utf-8")
    print(json.dumps({"videos": report["total"], "out": args.out},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Прогони тесты**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_patterns.py -q`
Expected: PASS, 11 тестов

- [ ] **Step 5: Коммит**

```bash
git add skills/youtube-analytics/scripts/patterns.py \
        skills/youtube-analytics/tests/test_patterns.py
git commit -m "youtube-analytics: режим patterns — семь срезов с порогом надёжности"
```

---

### Task 5: `vault.py` — выгрузка в волт

**Files:**
- Create: `skills/youtube-analytics/scripts/vault.py`
- Test: `skills/youtube-analytics/tests/test_vault.py`

**Interfaces:**
- Consumes: `.channel.json` из Task 3
- Produces: `short_title(title, limit=60)` → ярлык; `card_markdown(record, channel)` → строка; `index_markdown(data)` → строка; `write_all(data, out_dir)` → dict путей; `write_base(root)` → путь; CLI `python3 vault.py --in .channel.json --out-dir <YT_OUTPUT_DIR>`

**Идемпотентность:** повторный запуск по тому же каналу перезаписывает карточки по `id` и не плодит дублей. Поле `notes` и секции, дописанные `enrich`, при перезаписи **сохраняются** — иначе разведка затирает ручную работу.

- [ ] **Step 1: Напиши падающие тесты**

```python
import json
from pathlib import Path

import vault

CHANNEL = {"title": "Nick Saraev", "handle": "nicksaraev",
           "subscribers": 492000, "channel_id": "UCx"}


def _video(vid="v1", title="I Spent $400 Benching Opus-5", kind="long"):
    return {
        "id": vid, "title": title, "kind": kind,
        "url": "https://www.youtube.com/watch?v=" + vid,
        "date": "2026-07-24", "duration_sec": 953,
        "views": 62875, "likes": 1577, "comments": 165,
        "median_multiple": 2.4, "views_per_day": 4000.0,
        "engagement_rate": 0.0277,
        "description": "текст описания", "tags": ["ai"],
        "thumbnail_url": "http://t/h.jpg", "tier2_status": "skeleton",
    }


def _data(videos=None):
    return {"channel": CHANNEL, "videos": videos or [_video()],
            "collected_at": "2026-08-09", "quota_units": 4}


def test_short_title_cuts_on_word_boundary():
    out = vault.short_title("I Spent $400 Benching Opus-5 And Here Is What "
                            "It Can Actually Do For You", limit=30)
    assert len(out) <= 30
    assert not out.endswith(" ")
    assert "|" not in out


def test_short_title_escapes_pipe():
    assert "|" not in vault.short_title("До | После")


def test_card_has_frontmatter_and_backlink():
    md = vault.card_markdown(_video(), CHANNEL)
    assert md.startswith("---\n")
    assert "median_multiple: 2.4" in md
    assert "tier2_status: skeleton" in md
    assert "[[nicksaraev]]" in md
    assert "## Разбор вступления" in md


def test_index_splits_shorts_and_long():
    data = _data([_video("v1", kind="long"),
                  _video("v2", title="Шорт", kind="short")])
    md = vault.index_markdown(data)
    assert "## Длинные" in md
    assert "## Shorts" in md
    assert "[[cards/v1\\|" in md


def test_write_all_creates_structure(tmp_path):
    paths = vault.write_all(_data(), tmp_path)
    root = Path(paths["channel_dir"])
    assert (root / "index.md").exists()
    assert (root / "cards" / "v1.md").exists()
    assert (root / "export.csv").exists()
    assert root.name == "nicksaraev"


def test_write_all_is_idempotent(tmp_path):
    vault.write_all(_data(), tmp_path)
    vault.write_all(_data(), tmp_path)
    cards = list((tmp_path / "nicksaraev" / "cards").glob("*.md"))
    assert len(cards) == 1


def test_write_all_preserves_enriched_sections(tmp_path):
    vault.write_all(_data(), tmp_path)
    card = tmp_path / "nicksaraev" / "cards" / "v1.md"
    text = card.read_text(encoding="utf-8")
    text = text.replace("## Заметки\n", "## Заметки\nмоя ручная заметка\n")
    card.write_text(text, encoding="utf-8")

    vault.write_all(_data(), tmp_path)
    assert "моя ручная заметка" in card.read_text(encoding="utf-8")


def test_csv_has_all_columns(tmp_path):
    vault.write_all(_data(), tmp_path)
    csv_text = (tmp_path / "nicksaraev" / "export.csv").read_text(
        encoding="utf-8")
    header = csv_text.splitlines()[0]
    for col in ("id", "title", "kind", "median_multiple", "views_per_day",
                "engagement_rate", "tier2_status"):
        assert col in header


def test_write_base_creates_obsidian_base(tmp_path):
    path = Path(vault.write_base(tmp_path))
    assert path.name == "_Разведка YouTube.base"
    text = path.read_text(encoding="utf-8")
    assert "median_multiple" in text
    assert "file.name" in text
```

- [ ] **Step 2: Прогони тесты, убедись что падают**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_vault.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'vault'`

- [ ] **Step 3: Реализуй `vault.py`**

```python
#!/usr/bin/env python3
"""Рендер выгрузки в волт: index.md + карточки + CSV + Obsidian Base.

Контракт повторяет instagram-analytics. Идемпотентность по id;
ручные заметки и секции enrich при перезаписи сохраняются.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

BASE_NAME = "_Разведка YouTube.base"

COLUMNS = ["id", "title", "channel", "url", "kind", "date", "duration_sec",
           "views", "likes", "comments", "median_multiple", "views_per_day",
           "engagement_rate", "description", "tags", "thumbnail_url",
           "tier2_status", "intro_transcript", "top_comments", "notes"]

KEEP_SECTIONS = ("## Вступление (дословно)", "## Разбор вступления",
                 "## Главы", "## Комментарии", "## Заметки")


def short_title(title, limit=60):
    """Читаемый ярлык для навигации. Режем по границе слова."""
    clean = (title or "").replace("|", "／").replace("[", "(").replace(
        "]", ")").strip()
    if len(clean) <= limit:
        return clean
    cut = clean[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,.—-")


def _yaml_value(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return "[" + ", ".join(str(v) for v in value) + "]"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def card_markdown(record, channel):
    label = short_title(record["title"])
    head = ["---", 'aliases: ["%s"]' % label]
    for field in ("id", "title", "url", "kind", "date", "duration_sec",
                  "views", "likes", "comments", "median_multiple",
                  "views_per_day", "engagement_rate", "thumbnail_url"):
        head.append("%s: %s" % (field, _yaml_value(record.get(field))))
    head.append("channel: %s" % channel.get("handle", ""))
    head.append("tags_video: %s" % _yaml_value(record.get("tags", [])))
    head.append("tier2_status: %s" % record.get("tier2_status", "skeleton"))
    head.append("---")

    body = [
        "",
        "# " + label,
        "",
        "*[[%s]] · %s · %s · %s просмотров · кратность %s*" % (
            channel.get("handle", ""), record["kind"], record["date"],
            record["views"], record.get("median_multiple")),
        "",
        "## Тайтл",
        record["title"],
        "",
        "## Описание",
        record.get("description", "") or "",
        "",
        "## Вступление (дословно)",
        "(пусто до enrich)",
        "",
        "## Разбор вступления",
        "- **Хук (0–3 сек):** (пусто до enrich)",
        "- **Обещание:** (пусто до enrich)",
        "- **Первое доказательство:** (пусто до enrich)",
        "",
        "## Главы",
        "(пусто до enrich)",
        "",
        "## Комментарии",
        "(пусто до enrich)",
        "",
        "## Заметки",
        "",
    ]
    return "\n".join(head + body)


def _merge_preserved(new_text, old_text):
    """Сохраняет содержимое секций, которые наполняет enrich или человек."""
    if not old_text:
        return new_text
    for section in KEEP_SECTIONS:
        old_block = _section_body(old_text, section)
        if old_block and old_block.strip() and "(пусто до enrich)" not in old_block:
            new_text = _replace_section(new_text, section, old_block)
    return new_text


def _section_body(text, header):
    pattern = re.compile(
        "^" + re.escape(header) + r"\n(.*?)(?=^## |\Z)", re.S | re.M)
    m = pattern.search(text)
    return m.group(1) if m else ""


def _replace_section(text, header, body):
    pattern = re.compile(
        "^(" + re.escape(header) + r"\n)(.*?)(?=^## |\Z)", re.S | re.M)
    return pattern.sub(lambda m: m.group(1) + body, text)


def _rows_table(rows):
    out = ["| # | Тема | кратность | просмотры | лайки | комменты | дата | "
           "длит. | tier2 |",
           "|---|------|-----------|-----------|-------|----------|------|"
           "-------|-------|"]
    for i, v in enumerate(rows, 1):
        out.append("| %d | [[cards/%s\\|%s]] | %s | %d | %s | %s | %s | %d с | %s |"
                   % (i, v["id"], short_title(v["title"]),
                      v.get("median_multiple"), v["views"],
                      v.get("likes") if v.get("likes") is not None else "—",
                      v.get("comments") if v.get("comments") is not None
                      else "—",
                      v["date"], v["duration_sec"],
                      v.get("tier2_status", "skeleton")))
    return out


def index_markdown(data):
    ch = data["channel"]
    out = [
        "# Разведка: @%s — scout %s" % (ch.get("handle", ""),
                                        data.get("collected_at", "")),
        "",
        "Источник: YouTube Data API v3 · подписчиков: %s · роликов: %d"
        % (ch.get("subscribers") if ch.get("subscribers") is not None
           else "скрыто", len(data["videos"])),
        "",
        "Ранжировано по **кратности к медиане своего типа** "
        "(просмотры / медиана Shorts или длинных отдельно). "
        "Клик по теме → карточка.",
        "",
    ]
    for label, kind in (("Длинные", "long"), ("Shorts", "short")):
        rows = [v for v in data["videos"] if v["kind"] == kind]
        if not rows:
            continue
        rows.sort(key=lambda v: v.get("median_multiple") or 0, reverse=True)
        out += ["## " + label, ""] + _rows_table(rows) + [""]
    return "\n".join(out)


def write_base(root):
    path = Path(root) / BASE_NAME
    path.write_text("""filters:
  and:
    - file.hasProperty("median_multiple")
    - file.folder.contains("cards")
views:
  - type: table
    name: Все по кратности
    order: [file.name, title, channel, kind, median_multiple, views, tier2_status]
    sort:
      - property: median_multiple
        direction: DESC
  - type: table
    name: По каналам
    order: [file.name, title, channel, median_multiple, views, date]
    sort:
      - property: channel
        direction: ASC
      - property: median_multiple
        direction: DESC
""", encoding="utf-8")
    return str(path)


def write_all(data, out_dir):
    ch = data["channel"]
    root = Path(out_dir)
    channel_dir = root / (ch.get("handle") or ch.get("channel_id"))
    cards_dir = channel_dir / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    for v in data["videos"]:
        v.setdefault("tier2_status", "skeleton")
        card = cards_dir / (v["id"] + ".md")
        old = card.read_text(encoding="utf-8") if card.exists() else ""
        card.write_text(_merge_preserved(card_markdown(v, ch), old),
                        encoding="utf-8")

    (channel_dir / "index.md").write_text(index_markdown(data),
                                          encoding="utf-8")

    with (channel_dir / "export.csv").open("w", newline="",
                                           encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS,
                                extrasaction="ignore")
        writer.writeheader()
        for v in data["videos"]:
            row = dict(v)
            row["channel"] = ch.get("handle", "")
            row["tags"] = ";".join(v.get("tags", []))
            writer.writerow(row)

    return {"channel_dir": str(channel_dir),
            "index": str(channel_dir / "index.md"),
            "csv": str(channel_dir / "export.csv"),
            "base": write_base(root)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="выгрузка канала в волт")
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    data = json.loads(Path(args.src).read_text(encoding="utf-8"))
    print(json.dumps(write_all(data, args.out_dir), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Прогони тесты**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_vault.py -q`
Expected: PASS, 9 тестов

- [ ] **Step 5: Коммит**

```bash
git add skills/youtube-analytics/scripts/vault.py \
        skills/youtube-analytics/tests/test_vault.py
git commit -m "youtube-analytics: выгрузка в волт, идемпотентно и без затирания enrich"
```

---

### Task 6: `fetch_intro.py` — вступление и главы через yt-dlp

**Files:**
- Create: `skills/youtube-analytics/scripts/fetch_intro.py`
- Test: `skills/youtube-analytics/tests/test_fetch_intro.py`

**Interfaces:**
- Consumes: ничего из предыдущих задач (автономен)
- Produces: `parse_vtt(text)` → список `{"t": "MM:SS", "sec": int, "text": str}` без дублей; `intro_lines(cues, seconds=60)` → срез до N секунд; `format_intro(cues)` → строка `00:00 текст`; `chapters_from_json(payload)` → список `{"start_sec", "title"}`; `fetch(video_id, runner)` → dict; CLI `python3 fetch_intro.py <video_id> --seconds 60`

**Деградация:** субтитров нет / отключены → `intro` пустой, `subtitles_available: false`, код возврата 0. Скилл в этом случае строит разбор по тайтлу, описанию и главам.

- [ ] **Step 1: Напиши падающие тесты**

```python
import json

import fetch_intro

VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.080 --> 00:00:02.560 align:start position:0%
Anthropic just dropped Claude Opus 5 and

00:00:02.560 --> 00:00:05.120 align:start position:0%
Anthropic just dropped Claude Opus 5 and
it is by far probably the best Frontier

00:00:05.120 --> 00:00:07.200 align:start position:0%
it is by far probably the best Frontier
large language model currently available

00:01:30.000 --> 00:01:32.000
this line is past the intro window
"""


def test_parse_vtt_dedupes_rolling_captions():
    cues = fetch_intro.parse_vtt(VTT)
    texts = [c["text"] for c in cues]
    assert texts == [
        "Anthropic just dropped Claude Opus 5 and",
        "it is by far probably the best Frontier",
        "large language model currently available",
        "this line is past the intro window",
    ]


def test_parse_vtt_keeps_seconds():
    cues = fetch_intro.parse_vtt(VTT)
    assert cues[0]["sec"] == 0
    assert cues[3]["sec"] == 90


def test_parse_vtt_strips_inline_tags():
    text = ("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n"
            "<c.colorE5E5E5>привет</c> мир\n")
    assert fetch_intro.parse_vtt(text)[0]["text"] == "привет мир"


def test_parse_vtt_empty_input():
    assert fetch_intro.parse_vtt("") == []


def test_intro_lines_cuts_at_window():
    cues = fetch_intro.parse_vtt(VTT)
    intro = fetch_intro.intro_lines(cues, seconds=60)
    assert len(intro) == 3
    assert all(c["sec"] <= 60 for c in intro)


def test_format_intro_has_timecodes():
    cues = fetch_intro.parse_vtt(VTT)
    out = fetch_intro.format_intro(fetch_intro.intro_lines(cues, 60))
    assert out.splitlines()[0].startswith("00:00 ")
    assert "Anthropic just dropped" in out


def test_chapters_from_json():
    payload = {"chapters": [
        {"start_time": 0.0, "title": "Intro"},
        {"start_time": 80.5, "title": "Demo"},
    ]}
    ch = fetch_intro.chapters_from_json(payload)
    assert ch == [{"start_sec": 0, "title": "Intro"},
                  {"start_sec": 80, "title": "Demo"}]


def test_chapters_from_json_missing():
    assert fetch_intro.chapters_from_json({}) == []
    assert fetch_intro.chapters_from_json({"chapters": None}) == []


def test_fetch_degrades_when_no_subtitles(tmp_path):
    def runner(cmd, **kwargs):
        # -J отдаёт метаданные, скачивание субтитров ничего не создаёт
        if "-J" in cmd:
            return json.dumps({"chapters": [], "title": "T"})
        return ""

    out = fetch_intro.fetch("vid", runner=runner, workdir=tmp_path)
    assert out["subtitles_available"] is False
    assert out["intro"] == ""
    assert out["chapters"] == []


def test_fetch_reads_downloaded_vtt(tmp_path):
    def runner(cmd, **kwargs):
        if "-J" in cmd:
            return json.dumps({"chapters": [
                {"start_time": 0, "title": "Intro"}], "title": "T"})
        (tmp_path / "vid.en.vtt").write_text(VTT, encoding="utf-8")
        return ""

    out = fetch_intro.fetch("vid", runner=runner, workdir=tmp_path)
    assert out["subtitles_available"] is True
    assert "Anthropic just dropped" in out["intro"]
    assert out["chapters"][0]["title"] == "Intro"
```

- [ ] **Step 2: Прогони тесты, убедись что падают**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_fetch_intro.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_intro'`

- [ ] **Step 3: Реализуй `fetch_intro.py`**

```python
#!/usr/bin/env python3
"""enrich: вступление ролика дословно + главы. Через yt-dlp, только stdlib.

Видео НИКОГДА не скачивается: только --skip-download.
Субтитров нет → отдаём пустое вступление и честный флаг, а не падаем.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TIMECODE = re.compile(r"^(\d\d):(\d\d):(\d\d)\.\d+\s+-->")
TAGS = re.compile(r"<[^>]+>")
DEFAULT_WINDOW = 60


def _run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True,
                          check=False, **kwargs).stdout


def parse_vtt(text):
    """VTT → реплики без дублей.

    Авто-субтитры YouTube «катятся»: каждая карточка повторяет предыдущую
    строку. Дедупим по тексту, сохраняя первое появление.
    """
    cues = []
    seen = set()
    current = None
    for line in (text or "").splitlines():
        m = TIMECODE.match(line.strip())
        if m:
            h, mm, ss = (int(g) for g in m.groups())
            current = h * 3600 + mm * 60 + ss
            continue
        clean = TAGS.sub("", line).strip()
        if current is None or not clean or clean.startswith("WEBVTT"):
            continue
        if clean in seen:
            continue
        seen.add(clean)
        cues.append({"sec": current,
                     "t": "%02d:%02d" % (current // 60, current % 60),
                     "text": clean})
    return cues


def intro_lines(cues, seconds=DEFAULT_WINDOW):
    return [c for c in cues if c["sec"] <= seconds]


def format_intro(cues):
    return "\n".join("%s %s" % (c["t"], c["text"]) for c in cues)


def chapters_from_json(payload):
    chapters = (payload or {}).get("chapters") or []
    return [{"start_sec": int(c.get("start_time") or 0),
             "title": c.get("title", "")} for c in chapters]


def fetch(video_id, runner=None, workdir=None, seconds=DEFAULT_WINDOW):
    runner = runner or _run
    url = "https://www.youtube.com/watch?v=" + video_id

    meta_raw = runner(["yt-dlp", "-J", "--skip-download", url])
    try:
        meta = json.loads(meta_raw) if meta_raw else {}
    except ValueError:
        meta = {}

    tmp = Path(workdir) if workdir else Path(tempfile.mkdtemp())
    tmp.mkdir(parents=True, exist_ok=True)
    runner(["yt-dlp", "--skip-download", "--write-auto-subs",
            "--write-subs", "--sub-langs", "en.*,ru.*", "--sub-format", "vtt",
            "-o", str(tmp / "%(id)s.%(ext)s"), url])

    vtt_files = sorted(tmp.glob("*.vtt"))
    if not vtt_files:
        return {"video_id": video_id, "title": meta.get("title", ""),
                "subtitles_available": False, "intro": "",
                "chapters": chapters_from_json(meta)}

    cues = parse_vtt(vtt_files[0].read_text(encoding="utf-8"))
    return {
        "video_id": video_id,
        "title": meta.get("title", ""),
        "subtitles_available": bool(cues),
        "intro": format_intro(intro_lines(cues, seconds)),
        "chapters": chapters_from_json(meta),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="вступление ролика + главы")
    ap.add_argument("video_id")
    ap.add_argument("--seconds", type=int, default=DEFAULT_WINDOW)
    args = ap.parse_args(argv)
    print(json.dumps(fetch(args.video_id, seconds=args.seconds),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Прогони тесты**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests/test_fetch_intro.py -q`
Expected: PASS, 10 тестов

- [ ] **Step 5: Прогони весь набор тестов скилла**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests -q`
Expected: PASS, 63 теста суммарно

- [ ] **Step 6: Коммит**

```bash
git add skills/youtube-analytics/scripts/fetch_intro.py \
        skills/youtube-analytics/tests/test_fetch_intro.py
git commit -m "youtube-analytics: вступление и главы через yt-dlp, с деградацией"
```

---

### Task 7: Упаковка — SKILL.md, references, README, каталог

**Files:**
- Create: `skills/youtube-analytics/SKILL.md`
- Create: `skills/youtube-analytics/README.md`
- Create: `skills/youtube-analytics/references/api.md`
- Create: `skills/youtube-analytics/references/patterns-reading.md`
- Modify: `skills/README.md` (добавить строку в каталог-витрину)

**Interfaces:**
- Consumes: все скрипты из Task 1–6
- Produces: рабочий скилл, подключаемый через `skills/install-skills.sh`

- [ ] **Step 1: Напиши `SKILL.md`**

Frontmatter `description` — единственный триггер, поэтому в нём должны стоять живые формулировки запроса и явные границы. Структура повторяет `instagram-analytics/SKILL.md`: главное правило → дисциплина ответа → режимы → метод → выход → хэндофф → ограничения → references.

```markdown
---
name: youtube-analytics
description: >-
  Разведчик YouTube-каналов через Data API v3: по @handle любого публичного канала
  собирает ролики с метриками (просмотры, лайки, комментарии, тайтлы, описания,
  длительность), ранжирует «что залетело» по кратности к медиане своего типа и
  выгружает в структурированную базу (Markdown-индекс + карточки + CSV).
  Три режима: scout (массово, дёшево) → patterns (закономерности тайтлов и
  форматов) → enrich (выборочно: вступление дословно с таймкодами, главы,
  комментарии). Используй всегда, когда пользователь хочет «разбери YouTube-канал»,
  «что заходит на ютубе у N», «проанализируй мой канал», «выгрузи ролики канала
  в таблицу», «какие тайтлы работают», «разбери вступление ролика». Работает и по
  СВОЕМУ каналу — механика та же. НЕ отдаёт CTR, показы и удержание (публичный API
  их не видит ни по какому каналу — нужен OAuth владельца) и НЕ пишет тайтлы с
  описаниями — это youtube-meta.
---

# YouTube-analytics — разведчик каналов

Ты — **разведчик контента на YouTube**. По каналу собираешь ролики с метриками,
ранжируешь «что залетело», считаешь закономерности и выгружаешь в базу.
Цель — сырьё для СВОИХ роликов: из чего сделан сработавший тайтл и из чего
сделаны первые 60 секунд.

## Главное правило

Это **разведка для создания своего контента**, а не материал для копирования.
Собранное всегда трактуется как **референс**; финал — переупаковка.

## Дисциплина ответа

Пользователю нужен результат, а не отчёт о ходе мыслей. Запросы к API, парсинг,
запись файлов делай молча.

- **Не печатай рассуждения** вроде «Зову API…», «Считаю медианы…».
- Видимый ответ: сводка (сколько собрано, расход квоты, топ-3 по кратности,
  пути к файлам) + блок «Допущения», если что-то вывел сам.
- **Не заканчивай призывом к диалогу.**

## Три режима

Определи режим по запросу. Дефолт — `scout`.

### `scout` (Tier-1 — дёшево, массово)

1. Извлеки `@handle` из запроса (из URL канала тоже).
2. Определи `<YT_OUTPUT_DIR>` из `.env` (дефолт `./youtube-analytics-output`).
3. Запусти:
   `python3 scripts/fetch_channel.py @handle --limit 300 --out "<YT_OUTPUT_DIR>/<handle>/.channel.json"`
4. Разложи в волт:
   `python3 scripts/vault.py --in "<...>/.channel.json" --out-dir "<YT_OUTPUT_DIR>"`
5. Сводка: сколько роликов, расход квоты, топ-3 по кратности, пути.

Ранжирование — по **кратности к медиане своего типа**: медиана считается
отдельно для Shorts и отдельно для длинных. Иначе шорт на 200k «побеждает»
20-минутный ролик, и выборка референсов ломается.

### `patterns` (Tier-1.5 — главный артефакт)

`python3 scripts/patterns.py --in "<...>/.channel.json" --out "<...>/Разбор — тайтлы и паттерны.md"`

Считает офлайн, к API не обращается. Семь срезов — как их читать и какие выводы
из них законны, смотри [references/patterns-reading.md](references/patterns-reading.md).

**Группы меньше 5 роликов помечены ненадёжными — выводы на них не строй.**
Прочитай готовый файл и допиши секцию «Что забираем себе» своими словами:
механика тайтлов из топа, что не повторять из дна, рабочая длительность и ритм.
Механику тайтла посчитать нельзя — её видно только на контрасте верха и низа.

### `enrich` (Tier-2 — выборочно)

По каждому выбранному ролику:
1. `python3 scripts/fetch_intro.py <video_id> --seconds 60` — вступление
   дословно с таймкодами + главы.
2. Комментарии — `commentThreads` (1 юнит на ролик), топ-50 по лайкам.
3. **Разбор вступления по битам:** какой ход в первых 3 секундах, где обещание,
   где первое доказательство, на какой секунде появляется результат.
   Раскладка по битам, не пересказ.
4. Допиши в карточку, `tier2_status` → `enriched`.

Субтитров нет → строй разбор по тайтлу, описанию и главам; `tier2_status`
всё равно `enriched`.

## Метод

- **Ключ:** `YOUTUBE_API_KEY` в `.env` папки скилла (шаблон — `.env.template`).
  Читать `.env` **без `source`** — zsh ломается на значениях с пробелами;
  скрипты читают файл сами.
- **`search.list` не вызывать никогда** — 100 юнитов из 10 000 и неполная
  выборка. Список роликов только через плейлист загрузок.
- **Видео не скачиваются** ни в одном режиме.
- Детали ручек и расход квоты — [references/api.md](references/api.md).

## Выход

`<YT_OUTPUT_DIR>/<handle>/`: `index.md` (две таблицы — длинные и Shorts),
`cards/<id>.md`, `export.csv`, `Разбор — тайтлы и паттерны.md`,
служебный `.channel.json`. Плюс `_Разведка YouTube.base` в корне.
Идемпотентно по `id`: повторный скаут не плодит дубли и не затирает
ручные заметки и секции enrich.

Не вываливай таблицу в чат — она в файлах.

## Хэндофф

- Паттерны → `youtube-meta` (тайтл, описание, теги).
- Вступления из enrich → `hook-base`, операция ПОЛОЖИТЬ, формат `youtube-intro`.
- Shorts → `reels-script`.

## Ограничения

- **Не отдаёт CTR, показы, удержание и watch time.** Публичный Data API их не
  видит **ни по какому каналу**. Это OAuth-ветка (Analytics API) и только по
  своему каналу. Скажи это прямо, если пользователь спрашивает про удержание,
  — не подменяй ответ похожими метриками.
- **Не пишет тайтлы и описания** — это `youtube-meta`.
- **Не ищет по ключевым словам и нишам** — `search.list` слишком дорог.
- **Не даёт объёмы поисковых запросов** — их нет в API. Не выдумывай цифры.
- **Граница Shorts эвристическая** (≤180 сек) — при спорных случаях скажи об этом
  в «Допущениях».
- **Конкретика, без выдумок:** только реальные данные API; нет данных — поле пусто.

## Где что брать

- **Ручки API и квота** — [references/api.md](references/api.md).
- **Как читать срезы** — [references/patterns-reading.md](references/patterns-reading.md).
```

- [ ] **Step 2: Проверь frontmatter**

Run: `head -30 skills/youtube-analytics/SKILL.md`
Expected: валидный YAML frontmatter, `name: youtube-analytics`, блок `description`
читается как единая строка (это единственный триггер скилла).

- [ ] **Step 3: Напиши `references/api.md`**

Содержимое: точные ручки с параметрами и стоимостью в юнитах, форма ответа
для каждой, правило «`search.list` — никогда», расчёт квоты для канала на 300
роликов (≈14 юнитов), поведение при `quotaExceeded` (сказать честно, предложить
подождать до сброса квоты в полночь по тихоокеанскому времени), заметка про
`snippet.tags` (может быть пустым для чужих каналов — тогда теги берутся
из yt-dlp в Tier-2).

- [ ] **Step 4: Напиши `references/patterns-reading.md`**

Содержимое: что означает каждый из семи срезов, какие выводы из него законны,
а какие нет. Обязательно: порог надёжности 5 роликов; «кратность сравнивает
ролик с медианой СВОЕГО типа, а не с другим каналом»; «медиана по месяцам
падает — формат сдулся, а не аудитория ушла»; «топ и дно читаются глазами:
ищем механику (разрыв статуса, невероятная цифра, отрицание лидера, момент
провала), а не тему»; «лайки растут вместе с каналом — длинную выборку
сравнивай внутри квартала».

- [ ] **Step 5: Напиши `README.md` скилла**

По образцу `skills/instagram-analytics/README.md`: зачем скилл, что нужно
(ключ + yt-dlp), три режима одной строкой каждый, куда кладёт результат,
чего НЕ делает (CTR/удержание — только OAuth).

- [ ] **Step 6: Добавь строку в каталог-витрину**

Run: `grep -n "instagram-analytics" skills/README.md`
Затем добавь строку про `youtube-analytics` в том же формате, что соседние.

- [ ] **Step 7: Прогони весь набор тестов ещё раз**

Run: `uv run --with pytest pytest skills/youtube-analytics/tests -q`
Expected: PASS, 63 теста

- [ ] **Step 8: Подключи скилл глобально**

Run: `bash skills/install-skills.sh`
Expected: создана ссылка `~/.claude/skills/youtube-analytics`; существующие не тронуты.

Проверь: `ls -la ~/.claude/skills/youtube-analytics`

- [ ] **Step 9: Коммит**

```bash
git add skills/youtube-analytics/SKILL.md \
        skills/youtube-analytics/README.md \
        skills/youtube-analytics/references/ \
        skills/README.md
git commit -m "youtube-analytics: SKILL.md, references и каталог"
```

---

## Боевой прогон (после Task 7, вместе с пользователем)

Не автоматизируется — требует настоящего ключа. Порядок:

1. Пользователь заводит `YOUTUBE_API_KEY` в Google Cloud и кладёт в `.env`.
2. `scout` по `@nicksaraev` — проверить: отработал, **фактический расход квоты**
   совпал с расчётным, `snippet.tags` **пришли или пусты** (открытый вопрос спеки
   — если пусты, теги переезжают в Tier-2 через yt-dlp, и это правится в `api.md`).
3. `patterns` по нему же — прочитать срезы, проверить, что маленькие бакеты
   помечены ненадёжными.
4. `enrich` по топ-3 — вступление с таймкодами и главы на месте.
5. Повторный `scout` — дублей нет, ручная заметка в карточке цела.
6. `scout` по своему каналу пользователя.
7. Итоги прогона дописать в `references/api.md` (как в `rough-cut` — раздел
   с результатами настоящего прогона).

## Self-Review

**Покрытие спеки:** три режима — Task 3/4/6; схема записи — Task 2 и 5;
ранжирование по кратности — Task 1; выгрузка и Base — Task 5; семь срезов
с порогом надёжности — Task 4; деградация без субтитров — Task 6; границы,
ключи и хэндофф — Task 7; открытый вопрос про теги — раздел боевого прогона.
Раздел спеки «Почему не берём готовое» — обоснование, кода не требует.
Раздел «Голос и описание» относится к будущему `youtube-meta` — здесь
не реализуется намеренно.

**Плейсхолдеры:** в шагах Task 7 (`references`, `README`) описан состав
содержимого по пунктам, а не готовый текст — это документация, где дословный
текст пишется по месту; состав задан достаточно, чтобы не осталось выбора
«о чём писать».

**Согласованность типов:** `metrics.enrich_records` дописывает
`median_multiple` / `views_per_day` / `engagement_rate` — те же имена читают
`patterns.build_report`, `vault.card_markdown` и колонки CSV. `yt_api.parse_videos`
выдаёт `kind` и `duration_sec` — их же ждут `metrics.medians_by_kind`,
`patterns.bucket` и `vault.index_markdown`. `fetch_intro.fetch` возвращает
`intro` / `chapters` / `subtitles_available` — читается только скиллом,
в других скриптах не используется.
