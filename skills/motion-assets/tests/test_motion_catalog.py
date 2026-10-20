import json
import re
import subprocess
import threading
import urllib.error
import urllib.request
from urllib.parse import quote

import pytest

import catalog
import library


def scene(id_="tg-coin", **kw):
    e = {"id": id_, "kind": "scene", "layout": "half", "duration": 3.3, "theme": "dark",
         "template": "coin_flip", "tags": ["telegram", "канал"],
         "describes": "монета-иконка из файла: влетает, переворачивается, волны-кольца",
         "events": [{"t": 0.15, "what": "значок появляется"}, {"t": 1.75, "what": "переворот"}],
         "files": {"mp4": f"{id_}/{id_}.mp4", "preview": f"{id_}/{id_}-preview.png"}}
    e.update(kw)
    return e


def broll(id_="gh-repo", **kw):
    e = {"id": id_, "kind": "broll", "layout": "full", "duration": 3.9, "theme": "light",
         "tags": ["GitHub", "гитхаб", "звёзды"],
         "describes": "страница github.com/x/y (светлая, мобильная): камера к звёздам",
         "private": [{"from": 1.0, "to": 2.0, "what": "IP в заголовке"}],
         "files": {"mp4": f"{id_}/{id_}.mp4"}}
    e.update(kw)
    return e


def overlay(id_="num-ov", **kw):
    e = {"id": id_, "kind": "overlay", "layout": "overlay", "duration": 3.0, "theme": "light",
         "tags": ["число"], "describes": "крупное число на груди",
         "files": {"mov_alpha": f"{id_}/{id_}.mov", "green": f"{id_}/{id_}-green.mp4"}}
    e.update(kw)
    return e


def make_lib(root, entries):
    """Мини-библиотека: index.json + файлы-пустышки из files каждой записи."""
    for e in entries:
        for rel in e.get("files", {}).values():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"0123456789")
    library.save(root, {"version": 1, "assets": entries})
    return root


TPL = {"coin_flip": {"title": "Монета-иконка", "when": "представить один объект крупно"}}


# ── номера ───────────────────────────────────────────────────────────────────

def test_assign_numbers_new_get_next_old_keep():
    nums, added = catalog.assign_numbers(["a", "b", "c"], {"numbers": {}})
    assert nums["numbers"] == {"a": 1, "b": 2, "c": 3} and added == ["a", "b", "c"]
    nums, added = catalog.assign_numbers(["a", "x", "b", "c"], nums)
    assert nums["numbers"] == {"a": 1, "b": 2, "c": 3, "x": 4} and added == ["x"]


def test_assign_numbers_never_reuses_removed():
    nums, _ = catalog.assign_numbers(["a", "b", "c"], {"numbers": {}})
    nums, added = catalog.assign_numbers(["b", "c", "y"], nums)   # «a» удалили
    assert nums["numbers"]["y"] == 4 and nums["numbers"]["a"] == 1 and nums["next"] == 5
    nums, _ = catalog.assign_numbers(["b"], {"numbers": {"b": 2}, "next": 9})
    assert nums["next"] == 9


def test_build_numbers_stable_when_asset_added(tmp_path):
    lib = make_lib(tmp_path, [scene("a"), broll("b")])
    first = {a["id"]: a["no"] for a in catalog.build(lib, use_ffmpeg=False, tpl_info=TPL)["items"]}
    assert first == {"a": 1, "b": 2}

    library.put(lib, scene("c"))
    library.put(lib, scene("a", describes="перерендер: запись заменена целиком"))
    res = catalog.build(lib, use_ffmpeg=False, tpl_info=TPL)
    assert {a["id"]: a["no"] for a in res["items"]} == {"a": 1, "b": 2, "c": 3}
    assert res["added"] == ["c"]
    saved = json.loads((lib / "_каталог" / "numbers.json").read_text(encoding="utf-8"))
    assert saved["numbers"] == {"a": 1, "b": 2, "c": 3}
    # чужой формат не трогаем: номера живут только в numbers.json
    assert all("no" not in e for e in library.load(lib)["assets"])


# ── тексты ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text, title, rest", [
    ("дорожка монтажа в 3D: вспыхивают куски", "Дорожка монтажа в 3D", "вспыхивают куски"),
    ("страница github.com/x (светлая, мобильная): камера", "Страница github.com/x (светлая, мобильная)", "камера"),
    ("проба «канал, автопилот», 4 сцены", "Проба «канал, автопилот»", "4 сцены"),
    ("3D-ноутбук падает; на экране видео", "3D-ноутбук падает", "на экране видео"),
    ("README без кода", "README без кода", ""),
    ("rea.tools/ru/showcase: карточка", "rea.tools/ru/showcase", "карточка"),
    ("", "", ""),
])
def test_split_describes(text, title, rest):
    assert catalog.split_describes(text) == (title, rest)


def test_split_describes_long_title_cut_by_word():
    title, rest = catalog.split_describes("слово " * 20)
    assert title.endswith("…") and len(title) <= catalog.TITLE_MAX + 1 and rest.startswith("слово")


def test_when_from_template_else_tags():
    assert catalog.when_text(scene(), TPL["coin_flip"]) == "представить один объект крупно"
    assert catalog.when_text(broll(), None) == "на словах «GitHub», «гитхаб», «звёзды»"
    assert catalog.when_text(broll(tags=[]), None) == ""


def test_template_info_reads_real_templates():
    info = catalog.template_info()
    assert info["coin_flip"]["title"] == "Монета-иконка"
    assert "объект крупно" in info["coin_flip"]["when"]
    assert "`" not in info["end_card"]["when"] and "*" not in info["end_card"]["when"]


# ── страница ─────────────────────────────────────────────────────────────────

def test_build_html_from_mini_library(tmp_path):
    lib = make_lib(tmp_path, [scene(), broll(), overlay()])
    res = catalog.build(lib, use_ffmpeg=False, tpl_info=TPL)
    out = lib / "_каталог"
    html = (out / "index.html").read_text(encoding="utf-8")
    data = json.loads((out / "data.json").read_text(encoding="utf-8"))
    assert res["html"] == out / "index.html" and data["count"] == 3
    by = {a["id"]: a for a in data["assets"]}

    s = by["tg-coin"]
    assert (s["no"], s["title"], s["template"]) == (1, "Монета-иконка из файла", "Монета-иконка")
    assert s["video"] == "../tg-coin/tg-coin.mp4" and s["poster"] == "../tg-coin/tg-coin-preview.png"
    assert s["when"] == "представить один объект крупно" and s["format"] == "9:16"
    assert [e["t"] for e in s["events"]] == [0.15, 1.75]

    b = by["gh-repo"]
    assert b["group"] == "свой б-ролл" and b["when"].startswith("на словах «GitHub»")
    assert b["private"] == ["1,0–2,0 с: IP в заголовке"] and b["poster"] is None

    o = by["num-ov"]
    assert o["video"] is None and "mov" in o["note"]
    assert {f["label"] for f in o["files"]} == {"mov с альфой", "зелёный"}

    # данные встроены в страницу — работает и файлом, и по IP без интернета
    payload = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    assert json.loads(payload.group(1).replace("<\\/", "</"))["count"] == 3
    assert not re.search(r'(src|href)\s*=\s*"(https?:)?//', html)
    assert "@import" not in html and "cdn" not in html.lower()


def test_build_quotes_unsafe_file_names(tmp_path):
    e = broll("t1", files={"mp4": "t1/t1 — Telegram (моушн, 14 с).mp4"}, describes="</script>")
    lib = make_lib(tmp_path, [e])
    catalog.build(lib, use_ffmpeg=False, tpl_info={})
    data = json.loads((lib / "_каталог" / "data.json").read_text(encoding="utf-8"))
    url = data["assets"][0]["video"]
    assert " " not in url and url == "../t1/" + quote("t1 — Telegram (моушн, 14 с).mp4")
    html = (lib / "_каталог" / "index.html").read_text(encoding="utf-8")
    assert html.count("</script>") == 2          # описание не закрывает тег данных


def test_build_out_elsewhere_keeps_relative_links(tmp_path):
    lib = make_lib(tmp_path / "lib", [scene()])
    res = catalog.build(lib, out=tmp_path / "site", use_ffmpeg=False, tpl_info=TPL)
    assert res["items"][0]["video"] == "../lib/tg-coin/tg-coin.mp4"
    assert (lib / "_каталог" / "numbers.json").exists()


# ── сервер ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("header, span", [
    ("bytes=2-5", (2, 5)),
    ("bytes=2-", (2, 9)),
    ("bytes=-3", (7, 9)),
    ("bytes=0-100", (0, 9)),
    ("bytes=10-", False),
    ("bytes=-0", False),
    ("bytes=5-2", None),
    ("bytes=0-1,4-5", None),
    ("items=0-1", None),
])
def test_byte_range(header, span):
    assert catalog.byte_range(header, 10) == span


@pytest.fixture
def server(tmp_path):
    lib = make_lib(tmp_path, [scene(), broll("t1", files={"mp4": "t1/имя с пробелом.mp4"})])
    catalog.build(lib, use_ffmpeg=False, tpl_info=TPL)
    srv = catalog.make_server(lib, "127.0.0.1", 0)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def test_server_range_returns_206(server):
    code, h, body = get(server + "/tg-coin/tg-coin.mp4", {"Range": "bytes=2-5"})
    assert code == 206 and body == b"2345"
    assert h["Content-Range"] == "bytes 2-5/10" and h["Content-Length"] == "4"
    assert h["Content-Type"] == "video/mp4"


def test_server_full_and_unsatisfiable(server):
    code, h, body = get(server + "/tg-coin/tg-coin.mp4")
    assert code == 200 and body == b"0123456789" and h["Accept-Ranges"] == "bytes"
    code, h, _ = get(server + "/tg-coin/tg-coin.mp4", {"Range": "bytes=50-"})
    assert code == 416 and h["Content-Range"] == "bytes */10"
    code, _, body = get(server + "/tg-coin/tg-coin.mp4", {"Range": "bytes=-3"})
    assert code == 206 and body == b"789"


def test_server_catalog_page_and_quoted_names(server):
    code, _, body = get(server + "/")                       # корень → каталог
    assert code == 200 and "Каталог приёмов" in body.decode("utf-8")
    code, _, body = get(server + "/t1/" + quote("имя с пробелом.mp4"), {"Range": "bytes=0-0"})
    assert code == 206 and body == b"0"


def test_server_no_directory_listing(server):
    code, _, _ = get(server + "/tg-coin/")
    assert code == 404


# ── ffmpeg ───────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_posters_and_format_from_real_video(tmp_path):
    lib = tmp_path
    for id_, size in (("v", "270x480"), ("w", "480x270")):
        (lib / id_).mkdir()
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                        f"color=c=0x3060F0:s={size}:r=30:d=1", "-c:v", "libx264",
                        "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(lib / id_ / f"{id_}.mp4")],
                       check=True)
    library.save(lib, {"version": 1, "assets": [
        broll("v", files={"mp4": "v/v.mp4"}, private=[], duration=1.0),
        broll("w", files={"mp4": "w/w.mp4"}, private=[], duration=1.0)]})
    res = catalog.build(lib, use_ffmpeg=True, tpl_info={})
    by = {a["id"]: a for a in res["items"]}
    assert by["v"]["format"] == "9:16" and by["w"]["format"] == "16:9"
    assert by["v"]["poster"] == "posters/v.jpg" and (lib / "_каталог/posters/v.jpg").stat().st_size
    assert res["posters_made"] == 2
    assert catalog.build(lib, use_ffmpeg=True, tpl_info={})["posters_made"] == 0   # кэш
