"""Бренд в хуке: значок влетает с поворотом и вспышкой, имя печатается по буквам, по нему
проходит блик, потом сверху вниз идёт луч-скан («заглядывает внутрь»). Родная тема — тёмная.

Когда брать: первые секунды ролика про инструмент — назвать его громко и сразу дать движение.
Бренд — ровно тот, о котором речь (Claude Code — свой вордмарк, не значок Claude: урок 2026-10-17).
Значок приходит файлом; шрифт имени — serif (как вордмарки Anthropic) или display темы.
"""
import _common as c

NAME = "brand_reveal"
TITLE = "Бренд в хуке"
DEFAULT_KIND = "dark"
BOX = (520, 1400)
BASE_TAGS = ["бренд", "логотип", "хук", "инструмент"]
SLOTS = {
    "icon": {"about": "значок бренда: путь к SVG/PNG или эмодзи", "default": "✳"},
    "name": {"about": "имя бренда, печатается по буквам", "default": "Мой сервис"},
    "glow": {"about": "цвет вспышки и колец: accent | secondary | #hex (цвет значка бренда)", "default": "accent"},
    "font": {"about": "шрифт имени: serif | display", "default": "serif"},
    "sub": {"about": "строка под именем (чип), можно пусто", "default": ""},
    "scan": {"about": "луч-скан сверху вниз после имени: true | false", "default": True},
    "tags": {"about": "до 4 фоновых слов", "default": []},
}


def css(pal, font, glow):
    fam = "Georgia, 'Times New Roman', serif" if font == "serif" else "var(--display)"
    return f"""
.brand {{ position: absolute; left: 0; right: 0; top: 760px; text-align: center; }}
#logo {{ display: inline-block; vertical-align: middle; width: 160px; height: 160px; opacity: 0; filter: drop-shadow(0 0 40px {c.rgba(pal['acc'], 0.0)}); }}
#logo img, #logo span {{ width: 160px; height: 160px; font-size: 140px; line-height: 160px; object-fit: contain; }}
#glow {{ position: absolute; left: 540px; top: 840px; width: 520px; height: 300px; margin: -150px 0 0 -260px;
  border-radius: 50%; background: radial-gradient(circle, {c.rgba(glow, 0.55)} 0%, rgba(0,0,0,0) 70%); opacity: 0; }}
.ring {{ position: absolute; left: 540px; top: 840px; width: 260px; height: 260px; margin: -130px 0 0 -130px;
  border-radius: 50%; border: 3px solid {c.rgba(glow, 0.7)}; opacity: 0; }}
#name {{ position: relative; display: inline-block; vertical-align: middle; margin-left: 22px; font-family: {fam}; font-size: 128px; font-weight: 500;
  letter-spacing: -0.01em; color: {c.WHITE}; white-space: nowrap; overflow: hidden; }}
#name .ch {{ display: inline-block; opacity: 0; }}
#shine {{ position: absolute; top: 0; bottom: 0; width: 160px; left: -200px;
  background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.55) 50%, rgba(255,255,255,0) 100%);
  mix-blend-mode: overlay; }}
#sub {{ display: inline-block; margin-top: 34px; padding: 12px 30px; border-radius: 999px; font-size: 40px; font-weight: 700;
  background: {c.rgba(pal['acc'], 0.16)}; color: {pal['acc']}; opacity: 0; }}
#scan {{ position: absolute; left: 0; right: 0; top: 560px; height: 10px; opacity: 0;
  background: linear-gradient(90deg, rgba(0,0,0,0), {pal['acc']}, rgba(0,0,0,0));
  box-shadow: 0 0 40px 12px {c.rgba(pal['acc'], 0.45)}; }}
#grid {{ position: absolute; left: 0; right: 0; top: 560px; height: 840px; opacity: 0;
  background-image: linear-gradient({c.rgba(pal['acc'], 0.10)} 2px, transparent 2px),
                    linear-gradient(90deg, {c.rgba(pal['acc'], 0.10)} 2px, transparent 2px);
  background-size: 60px 60px; }}
"""


def build(slots, theme, kind=None, layout="full"):
    s = c.merge_slots(SLOTS, slots)
    pal = c.palette(theme, kind or DEFAULT_KIND)
    icon, files = c.icon_html(s["icon"], "", name="logo")
    letters = "".join(f'<span class="ch">{c.esc(ch) if ch != " " else "&nbsp;"}</span>' for ch in s["name"])
    sub = f'<div><span id="sub">{c.esc(s["sub"])}</span></div>' if s["sub"] else ""
    content = ('<div id="grid"></div><div id="glow"></div><div class="ring" id="r1"></div><div class="ring" id="r2"></div>'
               f'<div class="brand"><div id="logo">{icon}</div><div id="name">{letters}<div id="shine"></div></div>{sub}</div>'
               '<div id="scan"></div>')
    n = len(s["name"])
    type0, step = 0.3, min(0.045, 0.55 / max(1, n))
    type_end = type0 + step * n
    shine = type_end + 0.05
    scan0 = shine + 0.25
    dur = (scan0 + 0.75) if s["scan"] else shine + 0.7
    deco, deco_js = c.decor(pal, layout, s["tags"], dur)
    body, bg, size = c.compose(pal, layout, deco, content, dur, BOX)
    js = [
        'tl.fromTo("#logo", { opacity: 0, scale: 0.3, rotation: -180 }, '
        '{ opacity: 1, scale: 1, rotation: 0, duration: 0.42, ease: "back.out(1.8)" }, 0.0);',
        'tl.fromTo("#glow", { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1.6, duration: 0.5, ease: "power2.out" }, 0.12);',
        'tl.to("#glow", { opacity: 0.35, duration: 0.6 }, 0.62);',
    ]
    for i, rid in enumerate(("#r1", "#r2")):
        js.append(f'tl.fromTo("{rid}", {{ scale: 0.8, opacity: 0.8 }}, {{ scale: 2.2, opacity: 0, duration: 0.8, '
                  f'ease: "power2.out", immediateRender: false }}, {c.fmt(0.3 + i * 0.18)});')
    js.append(f'tl.fromTo("#name .ch", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.12, '
              f'stagger: {step:.3f}, ease: "power2.out" }}, {c.fmt(type0)});')
    js.append(f'tl.fromTo("#shine", {{ x: 0 }}, {{ x: 1250, duration: 0.5, ease: "power2.inOut" }}, {c.fmt(shine)});')
    if s["sub"]:
        js.append(f'tl.fromTo("#sub", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.3, '
                  f'ease: "back.out(2)" }}, {c.fmt(shine + 0.1)});')
    if s["scan"]:
        js += [f'tl.fromTo("#grid", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2 }}, {c.fmt(scan0)});',
               f'tl.fromTo("#scan", {{ opacity: 0, y: 0 }}, {{ opacity: 1, y: 820, duration: 0.7, ease: "power1.inOut" }}, '
               f'{c.fmt(scan0)});']
    js += deco_js
    events = [c.ev(0.0, "значок влетает с поворотом, вспышка и кольца"),
              c.ev(type0, f"имя «{s['name']}» печатается по буквам"),
              c.ev(type_end, f"имя «{s['name']}» видно целиком"),
              c.ev(shine, "блик по имени")]
    if s["sub"]:
        events.append(c.ev(shine + 0.1, f"чип «{s['sub']}»"))
    if s["scan"]:
        events.append(c.ev(scan0, "луч-скан идёт сверху вниз по сетке"))
    describes = f"бренд «{s['name']}»: значок с поворотом и вспышкой, имя по буквам, блик" + (", луч-скан" if s["scan"] else "")
    style = c.base_css(pal, layout) + css(pal, s["font"], c.color_key(s["glow"], pal))
    return c.result(style, body, js, dur, events, pal, layout, bg, size, files, BASE_TAGS, describes,
                    preview_t=type_end + 0.1)
