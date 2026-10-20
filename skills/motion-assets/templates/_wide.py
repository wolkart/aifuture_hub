"""Общее для горизонтальных шаблонов 16:9 (1920×1080): куски «говорящая голова» в длинных
роликах. Только stdlib, поверх _common (палитра, экранирование, события, иконки).

Шаблон 16:9 объявляет FORMAT = "16:9"; раскладки — overlay (прозрачная, кладётся на дорожку
над видео) и full (на светлом фоне темы — вставка на весь экран). half у горизонтали нет.

Система (снята с референсов 2026-10-18, `_референсы/voronkov-claude-montage`, `labada-popups`):
белые карточки с мягкой тенью, синий градиент — из `secondary` темы и тёмного текста;
каждый элемент проявляется из размытия с подъёмом за ~0,25 с на 0,1–0,2 с раньше своего
слова; группа уходит общим выходом (размытие 0,18 с); пока висит — едва заметно покачивается;
лицо не перекрывается — графика в своей стороне кадра.
"""
import _common as c

WW, WH = 1920, 1080
FORMAT = "16:9"
LAYOUTS = ("full", "overlay")
SIDES = ("right", "left")
EXIT = 0.18          # групповой выход, с
TAIL = 0.25          # запас после выхода
# Звуки появления (синтез reel/scripts/sfx.py или свои WAV из папки звуков): [t, звук, dB].
POP, WHOOSH, SWISH = ("pop", -15.0), ("whoosh", -11.0), ("swish", -17.0)
SELECT, REWARD = ("select", -12.0), ("reward", -13.0)   # выбран вариант; крупная цифра / итог


def blues(pal):
    """Синий градиент карточек и пилюль — из второго цвета темы и тёмного текста."""
    return pal["sec"], c.mix(pal["sec"], pal["ink"], 0.42)


def css(pal, layout):
    b0, b1 = blues(pal)
    glow = "0 6px 30px rgba(0, 0, 0, 0.55), 0 0 2px rgba(0, 0, 0, 0.35)"
    big_shadow = f"text-shadow: {glow};" if layout == "overlay" else ""
    big_color = c.WHITE if layout == "overlay" else pal["ink"]
    return f"""
#scene {{ position: absolute; inset: 0; overflow: hidden; font-family: "ReelMain", sans-serif; }}
.bgfill {{ position: absolute; inset: 0; background: {c.background(pal)}; }}
#content {{ position: absolute; left: 0; top: 0; width: {WW}px; height: {WH}px; }}
.card {{ position: absolute; background: {c.WHITE}; border-radius: 26px; color: {pal['ink']};
  box-shadow: 0 22px 60px rgba(0, 0, 0, 0.22), 0 2px 6px rgba(0, 0, 0, 0.08); opacity: 0; }}
.pill {{ position: absolute; display: inline-flex; align-items: center; gap: 12px; padding: 12px 24px 12px 14px;
  border-radius: 999px; background: {c.WHITE}; color: {b0}; font-size: 28px; font-weight: 700; white-space: nowrap;
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.2); opacity: 0; }}
.pill .dot {{ width: 38px; height: 38px; border-radius: 50%; background: linear-gradient(135deg, {b0}, {b1});
  color: {c.WHITE}; display: flex; align-items: center; justify-content: center; font-size: 20px; }}
.ico {{ flex: none; border-radius: 22%; background: linear-gradient(135deg, {b0}, {b1}); color: {c.WHITE};
  display: flex; align-items: center; justify-content: center; box-shadow: 0 8px 22px {c.rgba(b0, 0.35)}; }}
.ico img {{ width: 64%; height: 64%; object-fit: contain; }}
.ico.round {{ border-radius: 50%; overflow: hidden; border: none !important; }}
.ico.round img {{ width: 100%; height: 100%; object-fit: cover; transform: scale(1.06); }}
.ttl {{ font-weight: 800; letter-spacing: -0.01em; line-height: 1.12; }}
.sub {{ color: {pal['muted']}; font-weight: 600; line-height: 1.2; }}
.big {{ position: absolute; font-family: "ReelDisplay", "ReelMain", sans-serif; font-weight: 800; color: {big_color};
  letter-spacing: -0.03em; line-height: 1; white-space: nowrap; opacity: 0; {big_shadow} }}
.blue {{ color: {b0}; }}
.big .blue {{ color: {c.mix(b0, c.WHITE, 0.45) if layout == "overlay" else b0}; }}
"""


def js_helpers():
    return """const popIn = (sel, at, d = 0.26) => tl.fromTo(sel,
  { opacity: 0, y: 16, scale: 0.96, filter: "blur(12px)" },
  { opacity: 1, y: 0, scale: 1, filter: "blur(0px)", duration: d, ease: "power3.out" }, at);
const groupOut = (sel, at, d = 0.18) => tl.fromTo(sel,
  { opacity: 1, filter: "blur(0px)" },
  { opacity: 0, filter: "blur(10px)", duration: d, ease: "power2.in", immediateRender: false }, at);
const sway = (sel, at, d, amp = 3) => tl.fromTo(sel, { y: 0, rotation: 0 },
  { y: -amp, rotation: 0.4, duration: d, ease: "sine.inOut", immediateRender: false }, at);"""


def compose(pal, layout, content):
    """Сцена 16:9. overlay — прозрачная страница; full — светлый фон темы. → (body, bg, size)."""
    if layout not in LAYOUTS:
        raise ValueError(f"раскладка {layout!r}: у горизонтальных шаблонов {', '.join(LAYOUTS)}")
    fill = "" if layout == "overlay" else '<div class="bgfill"></div>'
    body = f'<div id="scene">{fill}<div id="content">{content}</div></div>'
    bg = "transparent" if layout == "overlay" else pal["bg1"]
    return body, bg, [WW, WH]


def cue(t, kind):
    """Звук к событию: kind — POP / WHOOSH / SWISH. → [t, звук, dB]."""
    return [round(max(0.0, t), 3), kind[0], kind[1]]


def result(css_, body, js, dur, events, pal, layout, bg, size, files, tags, describes, preview_t, sfx=()):
    r = c.result(css_, body, [js_helpers()] + js, dur, events, pal, layout, bg, size, files, tags,
                 describes, preview_t)
    r["format"] = FORMAT
    r["sfx"] = sorted([q for q in sfx if 0 <= q[0] < dur], key=lambda q: q[0])
    return r


def times_of(items, start=0.15, step=0.7):
    """Моменты пунктов: свой at или равный шаг."""
    return [round(float(it.get("at", start + step * i)), 3) for i, it in enumerate(items)]


def end_time(times, duration, hold=1.6):
    """Когда группа уходит: заданная длина или последний пункт + hold."""
    return float(duration) if duration else (max(times) + hold if times else hold)


def item_html(i, it, size, prefix="it"):
    """Карточка-пункт: иконка в синем квадрате + заголовок + подпись. → (html, files)."""
    ic, files = c.icon_html(it.get("icon", "•"), "", name=f"{prefix}{i}")
    sub = f'<div class="sub" style="font-size:{int(size * 0.68)}px">{c.esc(it["sub"])}</div>' if it.get("sub") else ""
    box = int(size * 2.1)
    logo_bg = "background:#FFFFFF; border:2px solid rgba(0,0,0,0.08); box-shadow:none;" if c.is_image(it.get("icon", "")) else ""
    rnd = " round" if it.get("round") and c.is_image(it.get("icon", "")) else ""     # аватар: круг во всю плитку
    html = (f'<div class="row" id="{prefix}{i}"><div class="ico{rnd}" style="width:{box}px;height:{box}px;{logo_bg}'
            f'font-size:{int(box * 0.5)}px">{ic}</div><div class="tx"><div class="ttl" style="font-size:{size}px">'
            f'{c.esc(it.get("title", ""))}</div>{sub}</div></div>')
    return html, files
