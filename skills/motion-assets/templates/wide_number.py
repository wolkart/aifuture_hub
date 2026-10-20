"""Акцент вокруг головы (основа — `wide_drawer`). Крупное число на уровне груди (16:9): значение проявляется из размытия чуть крупнее и садится
на место, под ним — пилюля-подпись. На overlay текст белый со свечением прямо на кадре.
Родная тема — светлая; раскладка — overlay.

Когда брать: названная цифра — цена, срок, сколько заработал, сколько сэкономил. Одна цифра — один
показ, ~3 с. Референс: `voronkov-claude-montage` («55 млн руб» на груди).
"""
import _common as c
import _wide as w

NAME = "wide_number"
TITLE = "Крупное число (16:9)"
DEFAULT_KIND = "light"
FORMAT = w.FORMAT
DEFAULT_LAYOUT = "overlay"
BASE_TAGS = ["цифра", "число", "цена", "результат"]
PLACES = ("chest", "right", "left")
SLOTS = {
    "value": {"about": "крупно: «300 ₽», «×10», «20 минут»; *часть* — синим", "default": "×10"},
    "caption": {"about": "пилюля под числом, можно пусто", "default": "быстрее"},
    "at": {"about": "секунда, когда звучит число", "default": 0.3},
    "place": {"about": "chest (под лицом) | right | left", "default": "chest"},
    "head": {"about": "центр лица [x, y] долями — для chest", "default": [0.45, 0.4]},
    "duration": {"about": "длина, с (0 — at + 2,8 с)", "default": 0},
    "tags": {"about": "доп. теги", "default": []},
}


def value_html(text):
    out, blue = [], False
    for part in str(text).split("*"):
        if part:
            out.append(f'<span class="blue">{c.esc(part)}</span>' if blue else c.esc(part))
        blue = not blue
    return "".join(out)


def build(slots, theme, kind=None, layout=None):
    layout = layout or DEFAULT_LAYOUT
    s = c.merge_slots(SLOTS, slots)
    if s["place"] not in PLACES:
        raise ValueError(f"place {s['place']!r}: одно из {', '.join(PLACES)}")
    pal = c.palette(theme, kind or DEFAULT_KIND)
    plain = str(s["value"]).replace("*", "")
    px = c.fit_px(plain, 168, 8, 96)
    if s["place"] == "chest":
        x, y, anchor = s["head"][0] * w.WW, min(w.WH - 330, s["head"][1] * w.WH + 0.1 * w.WH), "translate(-50%, 0)"
    elif s["place"] == "right":
        x, y, anchor = w.WW - 470, w.WH * 0.38, "translate(-50%, 0)"
    else:
        x, y, anchor = 470, w.WH * 0.38, "translate(-50%, 0)"
    cap = f'<div class="pill" id="cap" style="position:relative; margin-top:18px">{c.esc(s["caption"])}</div>' if s["caption"] else ""
    content = (f'<div id="grp" style="position:absolute; left:{x:.0f}px; top:{y:.0f}px; transform:{anchor}; text-align:center">'
               f'<div class="big" id="num" style="position:relative; font-size:{px}px">{value_html(s["value"])}</div>{cap}</div>')
    at = float(s["at"])
    start = max(0.0, at - 0.15)
    end = float(s["duration"]) or (at + 2.8)
    dur = end + w.EXIT + w.TAIL
    body, bg, size = w.compose(pal, layout, content)
    js = [f'tl.fromTo("#num", {{ opacity: 0, scale: 1.06, filter: "blur(14px)" }}, '
          f'{{ opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.16, ease: "power3.out" }}, {c.fmt(start)});']
    events = [c.ev(start, f"число «{plain}» проявляется из размытия"), c.ev(start + 0.16, f"«{plain}» на месте")]
    sfx = [w.cue(start, w.POP)]
    if s["caption"]:
        js.append(f'popIn("#cap", {c.fmt(start + 0.25)}, 0.22);')
        events.append(c.ev(start + 0.25, f"подпись «{s['caption']}»"))
        sfx.append(w.cue(start + 0.25, w.POP))
    js.append(f'groupOut("#grp", {c.fmt(end)});')
    events.append(c.ev(end, "число уходит размытием"))
    style = w.css(pal, layout) + f"#cap {{ font-size: 34px; color: {pal['ink']}; }}\n"
    describes = f"крупное число «{plain}»" + (f" с подписью «{s['caption']}»" if s["caption"] else "") + f" ({s['place']})"
    return w.result(style, body, js, dur, events, pal, layout, bg, size, [], BASE_TAGS + list(s["tags"]),
                    describes, preview_t=start + 0.6, sfx=sfx)
