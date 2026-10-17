import importlib
import re
from pathlib import Path

import pytest

import _common as c

TEMPLATES = Path(c.__file__).resolve().parent
NAMES = sorted(p.stem for p in TEMPLATES.glob("*.py") if not p.stem.startswith("_"))

# Две темы с цветами-метками: цвет, который не меняется вместе с темой, — хардкод.
MARK_THEME = {
    "bg_dark": ["#101820", "#010203"], "bg_light": ["#FAFAF0", "#E1E2D3"],
    "text_dark": "#202A3B", "secondary": "#3366AA", "muted": "#8899AA", "success": "#22BB66",
    "accent": {"name": "метка", "solid": "#EE5511", "on_light": "#AA3300", "gradient": None},
    "font_main": None, "font_display": None,
}
MARK_THEME_2 = {
    "bg_dark": ["#2A1A0A", "#0B0A01"], "bg_light": ["#F0F4FA", "#D0D8E1"],
    "text_dark": "#3B2A20", "secondary": "#AA6633", "muted": "#AA9988", "success": "#66BB22",
    "accent": {"name": "метка2", "solid": "#11AAEE", "on_light": "#0033AA", "gradient": None},
    "font_main": None, "font_display": None,
}
NEUTRAL = {"#FFFFFF", "#000000"}            # белый и чёрный — для смешивания, бликов и теней
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
RGBA = re.compile(r"rgba\((\d+), (\d+), (\d+),")

CUSTOM = {
    "brand_reveal": {"icon": "★", "name": "Сервис", "font": "display", "sub": "бета", "scan": False, "glow": "secondary"},
    "big_word": {"word": "НАВСЕГДА", "chip": "", "icon": "★"},
    "logo_row": {"title": "", "check": False, "items": [{"icon": "★", "label": "A", "at": 0.1}, {"icon": "●", "label": "B", "at": 0.5},
                                                        {"icon": "▲", "label": "C", "at": 0.9}, {"icon": "■", "label": "D", "at": 1.3}]},
    "coin_flip": {"headline": "Мой *бот*\nработает _ночью_", "context": "Смотри:", "icon": "★",
                  "coin": "accent", "tags": ["a", "b"]},
    "sources_bot": {"sources": ["Канал", "Сайт", "Почта", "Таблица"], "result": "+4 входа",
                    "bot": "⚙", "headline": "Всё в *одно* место"},
    "post_3d": {"text": "Длинный текст поста " * 8, "name": "Блог", "time": "вчера",
                "badge": "AI", "context": ""},
    "flip_board": {"from": 12, "to": 0, "unit": "мин", "notes": [["Отправлено", "10:00"]],
                   "headline": "Минус *12* минут", "subline": ""},
    "end_card": {"cta": "Ссылка\nв *описании*", "link": "site.example/very-long-link-name",
                 "highlight": "click", "pointer": "cursor", "name": "Канал", "glow": "accent"},
}


def tpl(name):
    return importlib.import_module(name)


def all_text(r):
    return r["css"] + r["body"] + r["js"]


@pytest.fixture(params=NAMES)
def name(request):
    return request.param


# ── каждый шаблон (новый модуль в templates/ подхватывается сам) ─────────────

def test_all_four_probe_templates_present():
    assert {"coin_flip", "sources_bot", "post_3d", "flip_board"} <= set(NAMES)


def test_module_contract(name):
    t = tpl(name)
    assert t.NAME == name and t.TITLE and t.DEFAULT_KIND in c.KINDS
    for k, v in t.SLOTS.items():
        assert v["about"] and "default" in v


@pytest.mark.parametrize("slots", ["default", "custom"])
def test_build_shape(name, slots, theme):
    r = tpl(name).build({} if slots == "default" else CUSTOM.get(name, {}), theme)
    for key in ("css", "body", "js", "duration", "events", "theme_kind", "layout", "bg", "size",
                "files", "tags", "describes", "preview_t"):
        assert key in r
    assert r["layout"] == "full" and r["size"] == [1080, 1920]
    assert r["theme_kind"] == tpl(name).DEFAULT_KIND
    assert 0 < r["preview_t"] < r["duration"]


@pytest.mark.parametrize("slots", ["default", "custom"])
def test_events_sorted_and_inside(name, slots, theme):
    r = tpl(name).build({} if slots == "default" else CUSTOM.get(name, {}), theme)
    ts = [e["t"] for e in r["events"]]
    assert ts == sorted(ts) and len(ts) >= 4
    assert all(0 <= t <= r["duration"] for t in ts)
    assert all(e["what"].strip() for e in r["events"])
    import library
    entry = {"id": "x", "kind": "scene", "layout": "full", "duration": r["duration"],
             "theme": r["theme_kind"], "events": r["events"]}
    assert library.validate_entry(entry) == []


def test_seek_safe_js(name, theme):
    for slots in ({}, CUSTOM.get(name, {})):
        js = tpl(name).build(slots, theme)["js"]
        for bad in ("Math.random", "Date.now", "performance.now", "tl.call", "new Date",
                    "innerHTML", "textContent"):
            assert bad not in js, bad
        assert not re.search(r"\b(top|left|right|bottom|width|height)\s*:", js)


def test_no_hardcoded_colors(name):
    """Каждый цвет в выдаче должен меняться вместе с темой, кроме белого и чёрного."""
    for slots in ({}, CUSTOM.get(name, {})):
        for kind in c.KINDS:
            a = all_text(tpl(name).build(slots, MARK_THEME, kind=kind))
            b = all_text(tpl(name).build(slots, MARK_THEME_2, kind=kind))
            fixed = {h.upper() for h in HEX.findall(a)} & {h.upper() for h in HEX.findall(b)}
            assert fixed <= NEUTRAL, fixed - NEUTRAL
            fixed_rgba = set(RGBA.findall(a)) & set(RGBA.findall(b))
            assert fixed_rgba <= {("0", "0", "0"), ("255", "255", "255")}, fixed_rgba


def test_default_slots_are_neutral(name):
    """Дефолты без чужих аккаунтов и брендов: только общие слова."""
    defaults = all_text(tpl(name).build({}, MARK_THEME))
    assert not re.search(r"@\w", defaults)
    assert "Telegram" not in defaults


def test_theme_colors_flow_in(name):
    r = tpl(name).build({}, MARK_THEME)
    text = all_text(r).upper()
    pal = c.palette(MARK_THEME, r["theme_kind"])
    assert pal["acc"].upper() in text or pal["sec"].upper() in text
    assert r["bg"] == pal["bg1"]


def test_unknown_slot_is_error(name, theme):
    with pytest.raises(ValueError):
        tpl(name).build({"headlin": "опечатка"}, theme)


def test_layouts(name, theme):
    half = tpl(name).build({}, theme, layout="half")
    assert half["size"] == [1080, 960] and "scale(" in half["body"]
    over = tpl(name).build({}, theme, layout="overlay")
    assert over["bg"] == "transparent" and over["layout"] == "overlay"
    assert "bgfill" not in over["body"] and 'id="tg' not in over["body"]
    assert "#tg" not in over["js"]                      # нет анимаций несуществующих тегов
    with pytest.raises(ValueError):
        tpl(name).build({}, theme, layout="side")


def test_ids_used_in_js_exist(name, theme):
    for layout in c.LAYOUTS:
        r = tpl(name).build(CUSTOM.get(name, {}), theme, layout=layout)
        ids = set(re.findall(r'id="([^"]+)"', r["body"]))
        used = set(re.findall(r'"#([\w-]+)', r["js"]))
        assert used <= ids, used - ids


def test_theme_override(name, theme):
    t = tpl(name)
    other = "light" if t.DEFAULT_KIND == "dark" else "dark"
    assert t.build({}, theme, kind=other)["theme_kind"] == other


# ── частности шаблонов ───────────────────────────────────────────────────────

def test_coin_icon_from_file(tmp_path, theme):
    svg = tmp_path / "logo.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    r = tpl("coin_flip").build({"icon": str(svg)}, theme)
    assert r["files"] == [(str(svg), "icon.svg")] and 'src="icon.svg"' in r["body"]
    with pytest.raises(ValueError):
        tpl("coin_flip").build({"icon": str(tmp_path / "nope.png")}, theme)


def test_sources_count_and_auto_result(theme):
    r = tpl("sources_bot").build({"sources": ["a", "b", "c", "d", "e", "f"]}, theme)
    assert r["body"].count('class="chip"') == 4 and "+4 источника" in r["body"]
    r = tpl("sources_bot").build({"sources": ["один"]}, theme)
    assert "+1 источник<" in r["body"]
    assert tpl("sources_bot").plural(5, "a", "b", "c") == "c"
    assert tpl("sources_bot").plural(22, "a", "b", "c") == "b"
    assert tpl("sources_bot").plural(11, "a", "b", "c") == "c"


def test_post_typing_length_drives_duration(theme):
    short = tpl("post_3d").build({"text": "Коротко."}, theme)
    long = tpl("post_3d").build({"text": "очень длинный текст " * 6}, theme)
    assert long["duration"] > short["duration"]
    assert short["body"].count('class="ch"') == len("Коротко.")


def test_flip_steps():
    steps = tpl("flip_board").steps
    assert steps(3, 0) == ["3", "2", "1", "0"]
    assert steps(0, 2) == ["0", "1", "2"]
    s = steps(100, 0)
    assert s[0] == "100" and s[-1] == "0" and len(s) == 11
    assert steps("A", "B") == ["A", "B"]
    assert steps(5, 5) == ["5"]


def test_flip_board_stack_not_text_swap(theme):
    r = tpl("flip_board").build({}, theme)
    assert r["body"].count('class="d" id="d') == 4               # 3, 2, 1, 0 стопкой
    assert r["js"].count("rotationX: -90") == 3


def png(path, w, h):
    """Минимальный PNG-заголовок нужного размера (размер читается из IHDR)."""
    import struct
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", w, h)
                     + b"\x08\x02\x00\x00\x00" + b"\x00" * 4)
    return path


@pytest.mark.parametrize("hl", ["pop", "click", "zoom"])
def test_end_card_highlights(hl, theme):
    r = tpl("end_card").build({"highlight": hl}, theme)
    assert ('id="bub"' in r["body"]) == (hl == "click")
    assert ('id="pill"' in r["body"]) == (hl != "click")
    assert ('id="scrim"' in r["body"]) == (hl == "zoom")
    whats = " ".join(e["what"] for e in r["events"])
    assert "ссылка" in whats or "ссылк" in whats
    assert "кодов" in r["describes"] and "без кодового слова" in r["describes"]


def test_end_card_has_no_code_word_slot():
    """Концовка-ссылка — анти-кодовое слово: слота под СЛОВО нет и не будет."""
    slots = set(tpl("end_card").SLOTS)
    assert not slots & {"word", "code", "code_word", "кодовое_слово"}


def test_end_card_pointer_auto_and_bad_values(theme):
    t = tpl("end_card")
    assert 'class="cur"' in t.build({"highlight": "click"}, theme)["body"]
    assert 'id="tap"' in t.build({"highlight": "pop"}, theme)["body"]
    assert 'id="ptr"' not in t.build({"pointer": "none"}, theme)["body"]
    with pytest.raises(ValueError):
        t.build({"highlight": "wobble"}, theme)
    with pytest.raises(ValueError):
        t.build({"pointer": "laser"}, theme)


def test_end_card_screenshot_geometry(tmp_path, theme):
    t = tpl("end_card")
    shot = png(tmp_path / "профиль.png", 576, 1280)
    assert t.image_size(shot) == (576, 1280)
    r = t.build({"profile": str(shot), "crop": [0, 62, 576, 380], "link_box": [22, 409, 157, 25],
                 "tone": "light"}, theme)
    assert r["files"] == [(str(shot), "profile.png")] and 'src="profile.png"' in r["body"]
    # шапка 576 px → карточка 900 px: масштаб 1.5625, скриншот сдвинут на обрезку
    assert "width: 900px; height: 594px" in r["css"] and "top: -96.9px" in r["css"]
    with pytest.raises(ValueError):            # без места ссылки плашку не к чему привязать
        t.build({"profile": str(shot)}, theme)
    with pytest.raises(ValueError):
        t.build({"profile": str(tmp_path / "нет.png"), "link_box": [0, 0, 1, 1]}, theme)


def test_end_card_jpeg_size(tmp_path):
    import struct
    sof = b"\xff\xc0" + struct.pack(">HBHH", 17, 8, 1280, 576) + b"\x00" * 10
    jpg = tmp_path / "a.jpg"
    jpg.write_bytes(b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 4) + b"\x00\x00" + sof)
    assert tpl("end_card").image_size(jpg) == (576, 1280)


@pytest.mark.parametrize("lcx", [0, 120, 468, 820, 936])
def test_end_card_pill_stays_in_frame(lcx):
    """Плашка над карточкой с учётом перспективы не вылезает за кадр, где бы ни была ссылка."""
    t = tpl("end_card")
    ow, pw, z = 936, 440, 170
    x = t.pill_x(lcx, ow, pw, z)
    f = t.PERSPECTIVE / (t.PERSPECTIVE - z)
    fx = c.W / 2 + ((c.W - ow) / 2 + x - c.W / 2) * f
    assert fx - pw * f / 2 >= 69.9 and fx + pw * f / 2 <= c.W - 69.9


@pytest.mark.integration
def test_end_card_frame_from_recording(tmp_path, theme, monkeypatch):
    import subprocess
    monkeypatch.setenv("HOME", str(tmp_path))
    rec = tmp_path / "профиль.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=white:s=320x640:d=1",
                    "-pix_fmt", "yuv420p", str(rec)], check=True)
    r = tpl("end_card").build({"profile": str(rec), "profile_at": 0.5, "link_box": [10, 500, 120, 20]}, theme)
    src, name = r["files"][0]
    assert name == "profile.png" and src.endswith(".png") and "профиль-0.50" in src
    assert 'background: #FFFFFF' in r["css"]           # белая запись → светлая плашка (tone auto)


# ── общий модуль ─────────────────────────────────────────────────────────────

def test_parse_headline_marks():
    lines = c.parse_headline("Свой _сервис,_ который работает *сам*")
    assert len(lines) == 1
    words = lines[0]
    assert words[1] == [("сервис,", "sec")] and words[-1] == [("сам", "acc")]
    assert words[0] == [("Свой", None)]


def test_parse_headline_multiword_and_punct_and_lines():
    lines = c.parse_headline("под *твой стиль*!\nи всё")
    assert lines[0][1] == [("твой", "acc")]
    assert lines[0][2] == [("стиль", "acc"), ("!", None)]
    assert c.plain(lines) == "под твой стиль! и всё"


def test_headline_html_ids_and_size():
    h = c.headline("один *два* три", context="Контекст", prefix="h")
    assert h["ids"] == ["hw0", "hw1", "hw2"] and h["styles"] == [None, "acc", None]
    assert 'id="hctx"' in h["html"] and "Контекст" in h["html"]
    long = c.headline("слово " * 20)
    assert long["size"] < h["size"]


def test_word_times_spread():
    assert c.word_times(1, 0.1, 1.6) == [0.1]
    t = c.word_times(6, 0.1, 1.6)
    assert t[0] == 0.1 and abs((t[1] - t[0]) - 0.28) < 1e-9        # шаг упёрся в максимум
    t = c.word_times(20, 0.0, 1.0)
    assert abs((t[1] - t[0]) - 0.12) < 1e-9                         # и в минимум
    assert c.word_times(0, 0, 1) == []


def test_mix_and_rgba():
    assert c.mix("#000000", "#FFFFFF", 0.5) == "#80808" + "0"
    assert c.mix("#102030", "#102030", 0.7) == "#102030"
    assert c.rgba("#FF0080", 0.5) == "rgba(255, 0, 128, 0.5)"


def test_escape_user_text(theme):
    r = tpl("post_3d").build({"name": "<b>я</b>", "headline": "a & b"}, theme)
    assert "<b>я</b>" not in r["body"] and "&lt;b&gt;" in r["body"]
