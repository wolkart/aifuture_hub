"""Акцент вокруг головы (основа — `wide_drawer`). Чипы вокруг головы (16:9): белые пилюли «значок + слово» встают дугой вокруг лица, каждая на
своё слово, копятся и уходят вместе. Лицо не перекрывают. Родная тема — светлая, раскладка —
overlay поверх кадра с говорящей головой.

Когда брать: перечисление коротких вещей — инструменты, симптомы, что режем, что входит.
Референс: `voronkov-claude-montage` (чипы «вдохи / чихи / кашель / запинки» вокруг головы).
"""
import math

import _common as c
import _wide as w

NAME = "wide_chips"
TITLE = "Чипы вокруг головы (16:9)"
DEFAULT_KIND = "light"
FORMAT = w.FORMAT
DEFAULT_LAYOUT = "overlay"
BASE_TAGS = ["чипы", "перечисление", "вокруг головы"]
# Углы мест (градусы от «вверх», по часовой): сверху-слева/справа, сбоку, снизу.
ANGLES = (-55, 55, -95, 95, -130, 130)
SLOTS = {
    "items": {"about": "2–6 чипов: [{icon, label, at}] — at — секунда своего слова",
              "default": [{"icon": "✦", "label": "первое", "at": 0.2}, {"icon": "✦", "label": "второе", "at": 0.8},
                          {"icon": "✦", "label": "третье", "at": 1.4}]},
    "head": {"about": "центр лица в кадре [x, y] долями (по кадру записи)", "default": [0.45, 0.4]},
    "spread": {"about": "радиус дуги, доля ширины кадра", "default": 0.2},
    "duration": {"about": "длина, с (0 — последний чип + 1,6 с)", "default": 0},
    "tags": {"about": "доп. теги", "default": []},
}


def spots(n, head, spread):
    hx, hy = head[0] * w.WW, head[1] * w.WH
    rx, ry = spread * w.WW, spread * w.WW * 0.78
    out = []
    for a in ANGLES[:n]:
        r = math.radians(a)
        x, y = hx + rx * math.sin(r), hy - ry * math.cos(r)
        out.append((min(max(x, 160), w.WW - 160), min(max(y, 70), w.WH - 90), a))
    return out


def build(slots, theme, kind=None, layout=None):
    layout = layout or DEFAULT_LAYOUT
    s = c.merge_slots(SLOTS, slots)
    pal = c.palette(theme, kind or DEFAULT_KIND)
    items = list(s["items"])[:6]
    files, chips = [], []
    for i, ((x, y, a), it) in enumerate(zip(spots(len(items), s["head"], float(s["spread"])), items)):
        ic, f = c.icon_html(it.get("icon", "✦"), "", name=f"chip{i}")
        files += f
        anchor = "translate(-100%, -50%)" if a < 0 else "translate(0, -50%)"
        dot = "dot logo" if c.is_image(it.get("icon", "")) else "dot"       # логотип — как есть, без синего кружка
        chips.append(f'<div class="chipw" style="left:{x:.0f}px; top:{y:.0f}px; transform:{anchor}">'
                     f'<div class="pill chip" id="ch{i}" style="position:relative"><span class="{dot}">{ic}</span>'
                     f'{c.esc(it.get("label", ""))}</div></div>')
    content = f'<div id="grp">{"".join(chips)}</div>'
    times = w.times_of(items, 0.2, 0.6)
    end = w.end_time(times, s["duration"])
    dur = end + w.EXIT + w.TAIL
    body, bg, size = w.compose(pal, layout, content)
    js, events, sfx = [], [], []
    for i, t in enumerate(times):
        js.append(f'popIn("#ch{i}", {c.fmt(max(0.0, t - 0.15))}, 0.22);')
        events.append(c.ev(max(0.0, t - 0.15), f"чип «{items[i].get('label', '')}» проявляется у головы"))
        sfx.append(w.cue(t - 0.15, w.POP))
    if times:
        js.append(f'sway("#grp", {c.fmt(min(times))}, {c.fmt(max(0.5, end - min(times)))}, 2);')
    js.append(f'groupOut("#grp", {c.fmt(end)});')
    events += [c.ev(max(times) + 0.25 if times else 0.5, "все чипы на месте"), c.ev(end, "чипы уходят вместе")]
    if len(events) < 4:
        events.append(c.ev(min(times) + 0.1 if times else 0.3, "первый чип виден целиком"))
    style = w.css(pal, layout) + """
.chipw { position: absolute; }
.chip { font-size: 34px; color: inherit; padding: 14px 28px 14px 14px; }
.chip .dot { width: 44px; height: 44px; font-size: 22px; }
.chip .dot.logo { background: none; box-shadow: none; border-radius: 0; width: 48px; height: 48px; }
.chip .dot.logo img { width: 100%; height: 100%; object-fit: contain; }
""" + f".chip {{ color: {pal['ink']}; }}\n"
    describes = "чипы вокруг головы: " + ", ".join(it.get("label", "") for it in items)
    return w.result(style, body, js, dur, events, pal, layout, bg, size, files, BASE_TAGS + list(s["tags"]),
                    describes, preview_t=(max(times) + 0.3) if times else 1.0, sfx=sfx)
