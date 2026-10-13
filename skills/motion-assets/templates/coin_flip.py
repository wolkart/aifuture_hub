"""Монета-иконка: глянцевая иконка-«монета» с 3D-переворотом, толщиной ребра и
волнами-кольцами + кинетический заголовок по словам с акцентом. Родная тема — тёмная.

Когда брать: представить один объект крупно — инструмент, сервис, канал, площадку.
Иконка приходит слотом (эмодзи или свой SVG/PNG): чужих логотипов в шаблоне нет.
"""
import _common as c

NAME = "coin_flip"
TITLE = "Монета-иконка"
DEFAULT_KIND = "dark"
BOX = (180, 1420)
BASE_TAGS = ["иконка", "монета", "переворот", "заголовок"]
SLOTS = {
    "headline": {"about": "заголовок по словам; *слово* — акцент, _слово_ — второй цвет, \\n — перенос",
                 "default": "Свой _сервис,_ который работает *сам*"},
    "context": {"about": "строка-контекст над заголовком, можно пусто", "default": ""},
    "icon": {"about": "иконка на монете: эмодзи/символ или путь к SVG/PNG", "default": "⚡"},
    "coin": {"about": "цвет монеты: secondary | accent | #hex", "default": "secondary"},
    "tags": {"about": "до 4 фоновых слов", "default": ["идея", "24/7", "авто", "старт"]},
}


def css(pal, base):
    light, dark, edge = c.mix(base, c.WHITE, 0.45), c.mix(base, c.BLACK, 0.3), c.mix(base, c.BLACK, 0.4)
    return f"""
.stage {{ position: absolute; left: 0; right: 0; top: 760px; height: 700px; perspective: 1400px; }}
#coin {{ position: absolute; left: 340px; top: 120px; width: 400px; height: 400px;
  transform-style: preserve-3d; opacity: 0; }}
.face {{ position: absolute; inset: 0; border-radius: 50%; backface-visibility: visible;
  background: radial-gradient(circle at 35% 30%, {light} 0%, {base} 45%, {dark} 100%);
  box-shadow: inset 0 -18px 40px rgba(0, 0, 0, 0.25), inset 0 14px 30px rgba(255, 255, 255, 0.35);
  display: flex; align-items: center; justify-content: center; }}
.edge {{ position: absolute; inset: 0; border-radius: 50%; background: {edge}; }}
.glyph {{ font-family: var(--display); font-size: 190px; line-height: 1; color: {c.WHITE}; }}
img.glyph {{ width: 210px; height: 210px; object-fit: contain; }}
#shadow {{ position: absolute; left: 380px; top: 560px; width: 320px; height: 50px; border-radius: 50%;
  background: rgba(0, 0, 0, 0.55); filter: blur(22px); opacity: 0; }}
.ring {{ position: absolute; left: 540px; top: 320px; width: 400px; height: 400px; margin: -200px 0 0 -200px;
  border-radius: 50%; border: 3px solid {c.rgba(pal['sec'], 0.6)}; opacity: 0; }}
"""


def build(slots, theme, kind=None, layout="full"):
    s = c.merge_slots(SLOTS, slots)
    pal = c.palette(theme, kind or DEFAULT_KIND)
    h = c.headline(s["headline"], s["context"], prefix="h")
    head_start = 0.15 if s["context"] else 0.1
    js, times = c.headline_js(h, head_start, 1.6)
    words_end = times[-1] + 0.32 if times else 0.5
    flip = max(1.75, words_end - 0.05)
    dur = flip + 1.55
    exit_t = dur - 0.15
    icon, files = c.icon_html(s["icon"], "glyph")
    icon_name = "из файла" if files else s["icon"]

    content = (h["html"] + '<div class="stage" id="stage"><div id="shadow"></div>'
               '<div class="ring" id="r1"></div><div class="ring" id="r2"></div>'
               '<div id="coin"><div class="edge" style="transform: translateZ(-14px)"></div>'
               '<div class="edge" style="transform: translateZ(-7px)"></div>'
               f'<div class="face" style="transform: translateZ(0)">{icon}</div></div></div>')
    deco, deco_js = c.decor(pal, layout, s["tags"], dur)
    body, bg, size = c.compose(pal, layout, deco, content, dur, BOX)

    if h["ctx_id"]:
        js.append(f'fadeIn("#{h["ctx_id"]}", 0.02);')
    js += [
        'tl.fromTo("#coin", { rotationY: -90, scale: 0.4, opacity: 0 }, '
        '{ rotationY: 0, scale: 1, opacity: 1, duration: 0.6, ease: "back.out(1.6)" }, 0.15);',
        'tl.fromTo("#shadow", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.6 }, 0.15);',
        'tl.fromTo("#coin", { y: 0 }, { y: -18, duration: 0.6, ease: "sine.inOut", yoyo: true, '
        'repeat: 1, immediateRender: false }, 0.8);',
        f'tl.fromTo("#coin", {{ rotationY: 0 }}, {{ rotationY: 360, duration: 0.9, '
        f'ease: "power2.inOut", immediateRender: false }}, {c.fmt(flip)});',
    ]
    for i, rid in enumerate(("#r1", "#r2")):
        js.append(f'tl.fromTo("{rid}", {{ scale: 1, opacity: 0.7 }}, {{ scale: 1.9, opacity: 0, '
                  f'duration: 1.0, ease: "power2.out", immediateRender: false }}, '
                  f'{c.fmt(flip + 0.05 + i * 0.35)});')
    js += deco_js
    js += [f'blurOut("#hhead", {c.fmt(exit_t)});', f'blurOut("#stage", {c.fmt(exit_t)});']

    events = c.headline_events(h, times)
    if s["context"]:
        events.append(c.ev(0.02, f"строка-контекст «{s['context']}»"))
    events += [
        c.ev(0.15, f"иконка {icon_name} влетает с поворотом"),
        c.ev(0.75, "иконка видна целиком"),
        c.ev(flip, "переворот иконки"),
        c.ev(flip + 0.05, "волны-кольца от иконки"),
        c.ev(exit_t, "уход: всё размывается"),
    ]
    describes = (f"монета-иконка {icon_name}: влетает, переворачивается, волны-кольца; "
                 f"заголовок по словам «{h['plain']}»")
    style = c.base_css(pal, layout) + css(pal, c.color_key(s["coin"], pal))
    return c.result(style, body, js, dur, events, pal, layout, bg, size, files, BASE_TAGS,
                    describes, preview_t=min(flip + 1.2, exit_t - 0.1))
