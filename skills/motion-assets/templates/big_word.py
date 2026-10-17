"""Крупное слово: панель от верхнего края, слово огромными буквами падает по букве с отскоком,
под ним проходит маркер, рядом выскакивает чип. Родная тема — светлая.

Когда брать: ударное слово ролика («БЕСПЛАТНО», «НАВСЕГДА») — так у автора в его рилсах.
Только на по-настоящему ударных словах, не на каждом (урок 2026-10-17: приёмы чередовать).
"""
import _common as c

NAME = "big_word"
TITLE = "Крупное слово"
DEFAULT_KIND = "light"
BOX = (380, 1300)
BASE_TAGS = ["крупно", "слово", "акцент", "панель"]
SLOTS = {
    "word": {"about": "слово (капсом), 4–12 букв", "default": "БЕСПЛАТНО"},
    "chip": {"about": "чип под словом, можно пусто", "default": "0 ₽"},
    "icon": {"about": "значок над словом: эмодзи или путь к SVG/PNG, можно пусто", "default": ""},
    "count_from": {"about": "отсчёт в чипе: с какого числа цифры прокручиваются до последнего числа чипа (0 — без отсчёта)",
                   "default": 0},
    "tags": {"about": "до 4 фоновых слов", "default": []},
}


def css(pal, px, marker):
    return f"""
.bw {{ position: absolute; left: 0; right: 0; top: 640px; text-align: center; }}
#bicon {{ display: inline-block; width: 170px; height: 170px; margin-bottom: 10px; opacity: 0; }}
#bicon img, #bicon span {{ width: 170px; height: 170px; font-size: 150px; line-height: 170px; object-fit: contain; }}
#word {{ position: relative; display: inline-block; font-family: var(--display); font-size: {px}px; font-weight: 700;
  line-height: 1; letter-spacing: 0.01em; color: {pal['ink'] if not pal['dark'] else c.WHITE}; text-transform: uppercase; }}
#word .ch {{ display: inline-block; opacity: 0; }}
#mark {{ position: absolute; left: -16px; right: -16px; bottom: 6px; height: 34%; border-radius: 10px;
  background: {marker}; z-index: -1; transform-origin: 0 50%; transform: scaleX(0); }}
#chip {{ position: relative; display: inline-block; margin-top: 40px; padding: 10px 56px; border-radius: 999px; font-family: var(--display);
  font-size: 150px; font-weight: 700; line-height: 1; background: {pal['ink'] if not pal['dark'] else pal['acc']};
  color: {c.WHITE if not pal['dark'] else pal['ink']}; opacity: 0; }}
#chip .win {{ display: inline-block; height: 1em; overflow: hidden; vertical-align: top; }}
#chip .strip {{ display: block; }}
#chip .strip span {{ display: block; height: 1em; text-align: right; }}
#cglow {{ position: absolute; inset: -18px; border-radius: 999px; box-shadow: 0 0 60px 22px {marker}; opacity: 0; z-index: -1; }}
"""


def build(slots, theme, kind=None, layout="full"):
    s = c.merge_slots(SLOTS, slots)
    pal = c.palette(theme, kind or DEFAULT_KIND)
    word = s["word"].upper()
    px = c.fit_px(word, 210, 7, 130)
    icon, files = ("", [])
    if s["icon"]:
        icon, files = c.icon_html(s["icon"], "", name="bicon")
    letters = "".join(f'<span class="ch">{c.esc(ch)}</span>' for ch in word)
    chip = c.esc(s["chip"])
    steps = []
    if s["chip"] and int(s["count_from"] or 0) > 0:
        import re
        m = re.match(r"\s*(\d+)(.*)", s["chip"])
        end, unit = (int(m.group(1)), m.group(2)) if m else (0, " " + s["chip"])
        n0 = int(s["count_from"])
        steps = [round(n0 - (n0 - end) * k / 7) for k in range(8)]
        strip = "".join(f"<span>{v}</span>" for v in steps)
        chip = f'<span class="win"><span class="strip" id="strip">{strip}</span></span>{c.esc(unit)}'
    content = ('<div class="bw">' + (f'<div><div id="bicon">{icon}</div></div>' if s["icon"] else "")
               + f'<div id="word"><div id="mark"></div>{letters}</div>'
               + (f'<div><span id="chip"><span id="cglow"></span>{chip}</span></div>' if s["chip"] else "") + "</div>")
    n = len(word)
    step = min(0.05, 0.4 / max(1, n))
    land = 0.05 + step * n + 0.18
    dur = land + (1.6 if s["chip"] and int(s["count_from"] or 0) > 0 else 0.9)
    deco, deco_js = c.decor(pal, layout, s["tags"], dur)
    body, bg, size = c.compose(pal, layout, deco, content, dur, BOX)
    js = [f'tl.fromTo("#word .ch", {{ opacity: 0, y: -160, scale: 1.4 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.28, '
          f'stagger: {step:.3f}, ease: "back.out(2.2)" }}, 0.05);',
          f'tl.fromTo("#mark", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.35, ease: "power3.out" }}, {c.fmt(land - 0.08)});',
          f'tl.fromTo("#word", {{ rotation: 0 }}, {{ rotation: -2, duration: 0.08, yoyo: true, repeat: 3, '
          f'ease: "sine.inOut", immediateRender: false }}, {c.fmt(land)});']
    if s["icon"]:
        js.append('tl.fromTo("#bicon", { opacity: 0, scale: 0.2, y: 60 }, { opacity: 1, scale: 1, y: 0, duration: 0.4, '
                  'ease: "back.out(2)" }, 0.0);')
        js.append(f'tl.to("#bicon", {{ y: -16, duration: 0.25, yoyo: true, repeat: 3, ease: "sine.inOut" }}, {c.fmt(land)});')
    if s["chip"]:
        js.append(f'tl.fromTo("#chip", {{ opacity: 0, scale: 0.4 }}, {{ opacity: 1, scale: 1, duration: 0.3, '
                  f'ease: "back.out(2.4)" }}, {c.fmt(land + 0.05)});')
        if steps:
            js.append(f'tl.fromTo("#strip", {{ y: 0 }}, {{ yPercent: -{100 * (len(steps) - 1) / len(steps):.2f}, duration: 0.6, '
                      f'ease: "power3.out", immediateRender: false }}, {c.fmt(land + 0.15)});')
        js.append(f'tl.fromTo("#cglow", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.18, yoyo: true, repeat: 3, '
                  f'ease: "sine.inOut", immediateRender: false }}, {c.fmt(land + 0.75)});')
        js.append(f'tl.to("#chip", {{ scale: 1.12, duration: 0.14, yoyo: true, repeat: 1, ease: "power2.out" }}, {c.fmt(land + 0.75)});')
    js += deco_js
    events = [c.ev(0.05, f"буквы «{word}» падают с отскоком"), c.ev(land, f"слово «{word}» видно целиком"),
              c.ev(land - 0.08, "маркер под словом")]
    if s["chip"]:
        events.append(c.ev(land + 0.05, f"чип «{s['chip']}»"))
    if s["icon"]:
        events.append(c.ev(0.0, "значок над словом выпрыгивает"))
    events.append(c.ev(dur - 0.25, f"«{word}» держится крупно"))
    describes = f"крупное слово «{word}» по буквам с отскоком, маркер" + (f", чип «{s['chip']}»" if s["chip"] else "")
    style = c.base_css(pal, layout) + css(pal, px, theme["accent"]["solid"])   # яркий акцент и на светлом: под тёмным словом
    return c.result(style, body, js, dur, events, pal, layout, bg, size, files, BASE_TAGS, describes,
                    preview_t=land + 0.4)
