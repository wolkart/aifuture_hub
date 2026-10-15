"""Лента канала: шапка канала, посты всплывают один за другим с кнопкой, по первой — тап,
потом лента прокручивается дальше: «там ещё много». Родная тема — тёмная.

Когда брать: «забрать можно у меня в канале», «там ещё много полезного» — показать канал
как место, где лежат вещи, а не просто сказать «подпишись». Посты и кнопка — слотами.
"""
import _common as c

NAME = "channel_feed"
TITLE = "Лента канала"
DEFAULT_KIND = "dark"
BOX = (220, 1560)
BASE_TAGS = ["канал", "лента", "посты", "забрать", "подписка"]
SLOTS = {
    "context": {"about": "строка-контекст над заголовком, можно пусто", "default": ""},
    "headline": {"about": "заголовок по словам, можно пусто", "default": ""},
    "channel": {"about": "имя канала в шапке", "default": "Мой канал"},
    "subtitle": {"about": "строка под именем", "default": "канал"},
    "posts": {"about": "заголовки постов (2–8): первые всплывают по одному, остальные — прокруткой",
              "default": ["Пост 1", "Пост 2", "Пост 3", "Пост 4", "Пост 5", "Пост 6"]},
    "button": {"about": "кнопка у поста", "default": "Забрать"},
    "scroll_at": {"about": "секунда, когда лента прокручивается дальше", "default": 2.4},
    "duration": {"about": "длина сцены, с", "default": 4.5},
    "tags": {"about": "до 4 фоновых слов", "default": ["канал", "посты", "забрать", "ещё"]},
}
POST_H, GAP, FIRST_Y = 200, 26, 170
SHOWN = 3


def css(pal):
    win = c.mix(pal["deep"], c.BLACK, 0.2)
    return f"""
.stage {{ position: absolute; inset: 0; perspective: 1500px; }}
#ph {{ position: absolute; left: 110px; right: 110px; top: 560px; height: 980px; border-radius: 54px; overflow: hidden;
  opacity: 0; background: linear-gradient(180deg, {c.rgba(c.mix(win, c.WHITE, 0.05), 0.98)}, {c.rgba(win, 0.98)});
  border: 3px solid {c.rgba(pal['sec'], 0.45)}; box-shadow: 0 50px 120px rgba(0, 0, 0, 0.6); }}
#hd {{ position: absolute; left: 0; right: 0; top: 0; height: 130px; z-index: 2; display: flex; align-items: center;
  gap: 22px; padding: 0 36px; background: {c.rgba(win, 0.98)}; border-bottom: 2px solid {c.rgba(c.WHITE, 0.08)}; }}
.av {{ width: 78px; height: 78px; border-radius: 50%; background: linear-gradient(135deg, {pal['sec']}, {pal['acc']}); }}
.nm {{ font-size: 40px; font-weight: 800; color: {c.WHITE}; }}
.st {{ font-size: 26px; color: {pal['muted']}; }}
#feed {{ position: absolute; left: 0; right: 0; top: 0; }}
.post {{ position: absolute; left: 30px; right: 30px; height: {POST_H}px; border-radius: 30px; padding: 26px 30px;
  background: {c.rgba(c.WHITE, 0.07)}; border: 2px solid {c.rgba(c.WHITE, 0.1)}; opacity: 0; }}
.pt {{ font-size: 40px; font-weight: 800; color: {c.WHITE}; }}
.pl {{ height: 16px; border-radius: 8px; margin-top: 18px; width: 70%; background: {c.rgba(c.WHITE, 0.16)}; }}
.btn {{ position: absolute; right: 30px; bottom: 24px; padding: 14px 34px; border-radius: 999px; font-size: 32px;
  font-weight: 800; color: {pal['deep']}; background: {pal['acc']}; }}
#tap {{ position: absolute; width: 90px; height: 90px; border-radius: 50%; opacity: 0;
  border: 5px solid {c.WHITE}; background: {c.rgba(c.WHITE, 0.25)}; }}
"""


def build(slots, theme, kind=None, layout="full"):
    s = c.merge_slots(SLOTS, slots)
    pal = c.palette(theme, kind or DEFAULT_KIND)
    posts = [str(p) for p in (s["posts"] or [])][:8]
    dur = max(2.0, float(s["duration"]))
    scroll_at = float(s["scroll_at"])
    h = c.headline(s["headline"], s["context"], prefix="h", top=300) if s["headline"] else None
    js, times = (c.headline_js(h, 0.1, 0.8) if h else ([], []))
    items = []
    for i, p in enumerate(posts):
        y = FIRST_Y + i * (POST_H + GAP)
        btn = f'<div class="btn">{c.esc(s["button"])}</div>' if s["button"] else ""
        items.append(f'<div class="post" id="po{i}" style="top:{y}px"><div class="pt">{c.esc(p)}</div>'
                     f'<div class="pl"></div>{btn}</div>')
    tap_x = 860 - 110 - 30 - 120
    tap_y = FIRST_Y + POST_H - 24 - 40
    content = ((h["html"] if h else "") + '<div class="stage"><div id="ph">'
               f'<div id="feed">{"".join(items)}<div id="tap" style="left:{tap_x}px; top:{tap_y}px"></div></div>'
               f'<div id="hd"><div class="av"></div><div><div class="nm">{c.esc(s["channel"])}</div>'
               f'<div class="st">{c.esc(s["subtitle"])}</div></div></div></div></div>')
    deco, deco_js = c.decor(pal, layout, s["tags"], dur)
    box = BOX if h else (540, 1560)
    body, bg, size = c.compose(pal, layout, deco, content, dur, box)
    js += [
        'tl.fromTo("#ph", { opacity: 0, y: 120, rotationX: 24, rotationY: 12, scale: 0.9 }, { opacity: 1, y: 0, '
        'rotationX: 8, rotationY: 6, scale: 1, duration: 0.45, ease: "power3.out" }, 0);',
        f'tl.fromTo("#ph", {{ rotationY: 6 }}, {{ rotationY: -4, duration: {c.fmt(dur - 0.45)}, ease: "sine.inOut", '
        f'immediateRender: false }}, 0.45);',
    ]
    shown = min(SHOWN, len(posts))
    for i in range(len(posts)):   # первые — по одному, остальные — уже стоят ниже и приедут прокруткой
        t = 0.35 + i * 0.3 if i < shown else 0.35 + shown * 0.3
        js.append(f'tl.fromTo("#po{i}", {{ opacity: 0, y: 60 }}, {{ opacity: 1, y: 0, duration: 0.28, '
                  f'ease: "back.out(1.6)" }}, {c.fmt(t)});')
    t_tap = 0.35 + shown * 0.3 + 0.15
    js += [
        f'tl.fromTo("#tap", {{ opacity: 0, scale: 1.6 }}, {{ opacity: 1, scale: 1, duration: 0.2 }}, {c.fmt(t_tap)});',
        f'tl.fromTo("#po0 .btn", {{ scale: 1 }}, {{ scale: 0.88, duration: 0.09, yoyo: true, repeat: 1 }}, '
        f'{c.fmt(t_tap + 0.2)});',
        f'tl.fromTo("#tap", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.25, immediateRender: false }}, {c.fmt(t_tap + 0.45)});',
    ]
    if len(posts) > shown:
        dist = (len(posts) - shown) * (POST_H + GAP)
        js.append(f'tl.fromTo("#feed", {{ y: 0 }}, {{ y: {-dist}, duration: {c.fmt(min(1.2, max(0.5, dur - scroll_at - 0.4)))}, '
                  f'ease: "power2.inOut" }}, {c.fmt(scroll_at)});')
    js += deco_js
    events = [c.ev(0.0, f"лента канала «{s['channel']}» влетает в 3D")]
    events += [c.ev(0.35 + i * 0.3, f"пост «{p}» всплывает") for i, p in enumerate(posts[:shown])]
    events.append(c.ev(t_tap + 0.2, f"тап по кнопке «{s['button']}» у первого поста"))
    if len(posts) > shown:
        events.append(c.ev(scroll_at, "лента прокручивается: ещё посты — " + ", ".join(posts[shown:])))
    if h:
        events += c.headline_events(h, times)
    describes = f"лента канала «{s['channel']}»: посты {', '.join(posts)}, кнопка «{s['button']}», прокрутка"
    return c.result(c.base_css(pal, layout) + css(pal), body, js, dur, events, pal, layout, bg, size, [],
                    BASE_TAGS, describes, preview_t=min(dur - 0.1, t_tap + 0.3))
