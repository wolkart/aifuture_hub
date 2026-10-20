"""Акцент вокруг головы (основа — `wide_drawer`). Список карточек сбоку от головы (16:9): сверху пилюля-рубрика, под ней пункты — белые
карточки с иконкой в синем квадрате, каждая на своё слово; группа уходит общим выходом.
Родная тема — светлая; основная раскладка — overlay поверх кадра с говорящей головой.

Когда брать: перечисление в речи — шаги, причины, ошибки, «что нужно» (до 4 пунктов).
Референс: `labada-popups` (список пунктов + рубрика), система — `voronkov-claude-montage`.
"""
import _common as c
import _wide as w

NAME = "wide_list"
TITLE = "Список карточек сбоку (16:9)"
DEFAULT_KIND = "light"
FORMAT = w.FORMAT
DEFAULT_LAYOUT = "overlay"
BASE_TAGS = ["список", "пункты", "шаги", "перечисление"]
SLOTS = {
    "rubric": {"about": "пилюля над списком «контекст · деталь», можно пусто", "default": "Коротко"},
    "rubric_icon": {"about": "значок в пилюле: эмодзи/символ или путь к картинке", "default": "✦"},
    "items": {"about": "1–4 пункта: [{icon, title, sub, at}] — at — секунда своего слова",
              "default": [{"icon": "1", "title": "Первый пункт", "sub": "пояснение", "at": 0.3},
                          {"icon": "2", "title": "Второй пункт", "sub": "пояснение", "at": 1.0}]},
    "side": {"about": "сторона кадра: right | left (лицо — в другой)", "default": "right"},
    "duration": {"about": "длина, с (0 — последний пункт + 1,6 с)", "default": 0},
    "tags": {"about": "доп. теги", "default": []},
}


def build(slots, theme, kind=None, layout=None):
    layout = layout or DEFAULT_LAYOUT
    s = c.merge_slots(SLOTS, slots)
    if s["side"] not in w.SIDES:
        raise ValueError(f"side {s['side']!r}: одна из {', '.join(w.SIDES)}")
    pal = c.palette(theme, kind or DEFAULT_KIND)
    items = list(s["items"])[:4]
    size = 40 if len(items) <= 2 else 36
    files, rows = [], []
    for i, it in enumerate(items):
        h, f = w.item_html(i, it, size)
        rows.append(h)
        files += f
    pill = ""
    if s["rubric"]:
        ic, f = c.icon_html(s["rubric_icon"], "", name="rubric")
        files += f
        pill = f'<div class="pill" id="rub" style="position:relative"><span class="dot">{ic}</span>{c.esc(s["rubric"])}</div>'
    row_h = size * 2.1 + 40 + 16
    col_h = len(items) * row_h + (80 if pill else 0)
    top = max(60, int((w.WH - col_h) / 2) - 40)
    side = "right:110px" if s["side"] == "right" else "left:110px"
    content = f'<div id="col" style="{side}; top:{top}px">{pill}{"".join(rows)}</div>'
    times = w.times_of(items, 0.35, 0.8)
    end = w.end_time(times, s["duration"])
    dur = end + w.EXIT + w.TAIL
    body, bg, size_ = w.compose(pal, layout, content)
    first = min(times) if times else 0.3
    js, events, sfx = [], [], []
    if pill:
        js.append(f'popIn("#rub", {c.fmt(max(0.0, first - 0.4))});')
        events.append(c.ev(max(0.0, first - 0.4), f"пилюля-рубрика «{s['rubric']}»"))
        sfx.append(w.cue(first - 0.4, w.POP))
    for i, t in enumerate(times):
        js.append(f'popIn("#it{i}", {c.fmt(max(0.0, t - 0.12))});')
        events.append(c.ev(max(0.0, t - 0.12), f"пункт «{items[i].get('title', '')}» проявляется"))
        events.append(c.ev(t + 0.2, f"пункт {i + 1} виден целиком"))
        sfx.append(w.cue(t - 0.12, w.POP))
    js.append(f'sway("#col", {c.fmt(first)}, {c.fmt(max(0.5, end - first))});')
    js.append(f'groupOut("#col", {c.fmt(end)});')
    events.append(c.ev(max(times) + 0.3 if times else 0.6, "все пункты на месте"))
    events.append(c.ev(end, "группа уходит размытием"))
    style = w.css(pal, layout) + f"""
#col {{ position: absolute; width: 700px; }}
.row {{ display: flex; align-items: center; gap: 22px; padding: 20px 28px 20px 20px; margin-top: 16px;
  background: {c.WHITE}; border-radius: 24px; color: {pal['ink']}; opacity: 0;
  box-shadow: 0 22px 60px rgba(0, 0, 0, 0.22), 0 2px 6px rgba(0, 0, 0, 0.08); }}
"""
    titles = "; ".join(it.get("title", "") for it in items)
    describes = (f"список сбоку ({s['side']}): {titles}" + (f" — рубрика «{s['rubric']}»" if s["rubric"] else ""))
    return w.result(style, body, js, dur, events, pal, layout, bg, size_, files, BASE_TAGS + list(s["tags"]),
                    describes, preview_t=(max(times) + 0.4) if times else 1.0, sfx=sfx)
