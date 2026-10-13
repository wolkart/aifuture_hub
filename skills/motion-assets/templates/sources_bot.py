"""Источники → бот: плашки-источники слетаются, «бот» всасывает их с пульсом, итог
«+N …». Родная тема — светлая.

Когда брать: «даёшь на вход несколько вещей — система их переваривает» (каналы, ссылки,
документы, заявки). Плашки — текст, эмодзи в начале по желанию; бот — эмодзи или SVG/PNG.
"""
import _common as c

NAME = "sources_bot"
TITLE = "Источники → бот"
DEFAULT_KIND = "light"
BOX = (180, 1680)
BASE_TAGS = ["источники", "бот", "сбор", "вход", "заголовок"]
SLOTS = {
    "context": {"about": "строка-контекст над заголовком, можно пусто", "default": "Как это работает:"},
    "headline": {"about": "заголовок по словам; *слово* — акцент, _слово_ — второй цвет",
                 "default": "Ты даёшь _источники_"},
    "sources": {"about": "1–4 плашки-источника", "default": ["📰 Источник 1", "📢 Источник 2",
                                                         "🔗 Источник 3"]},
    "bot": {"about": "иконка бота: эмодзи или путь к SVG/PNG", "default": "🤖"},
    "result": {"about": "итог под ботом; пусто — «+N источников»", "default": ""},
    "tags": {"about": "до 4 фоновых слов", "default": ["RSS", "ссылки", "данные", "поток"]},
}
ROWS = {1: [930], 2: [820, 1010], 3: [760, 930, 1090], 4: [720, 860, 1000, 1140]}
DX = {1: [0], 2: [-150, 150], 3: [-210, 0, 180], 4: [-210, 0, 180, -100]}
ROT = [-4, 3, -2, 4]
FROM = [(-260, 0), (300, 0), (-200, 120), (260, 80)]
BOT_CX, BOT_CY = 540, 1390
BLOBS = [("left", -120, 300, 520, "sec"), ("right", -140, 1100, 560, "acc")]


def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def chip_width(text):
    """Оценка ширины плашки (40 px, жирный): эмодзи шире буквы."""
    units = sum(2 if ord(ch) > 0x2000 else 1 for ch in text)
    return 0.62 * 40 * units + 80


def css(pal):
    deep = pal["deep"]
    return f"""
.row {{ position: absolute; left: 0; right: 0; display: flex; justify-content: center; }}
.chip {{ padding: 26px 40px; border-radius: 999px; font-size: 40px; font-weight: 700; line-height: 1.2;
  background: {c.WHITE}; color: {pal['ink']}; white-space: nowrap; opacity: 0;
  box-shadow: 0 18px 50px {c.rgba(pal['ink'], 0.18)}; border: 2px solid {c.rgba(pal['sec'], 0.25)}; }}
#bot {{ position: absolute; left: {BOT_CX - 150}px; top: {BOT_CY - 150}px; width: 300px; height: 300px;
  border-radius: 80px; background: linear-gradient(140deg, {c.mix(deep, c.WHITE, 0.12)}, {deep});
  box-shadow: 0 30px 70px {c.rgba(deep, 0.45)}; display: flex; align-items: center;
  justify-content: center; opacity: 0; }}
.em {{ font-size: 150px; line-height: 1; }}
img.em {{ width: 170px; height: 170px; object-fit: contain; }}
#result {{ position: absolute; left: 0; right: 0; top: 1600px; text-align: center; font-size: 44px;
  font-weight: 800; color: {pal['sec']}; opacity: 0; }}
"""


def build(slots, theme, kind=None, layout="full"):
    s = c.merge_slots(SLOTS, slots)
    sources = list(s["sources"])[:4] or ["Источник"]
    n = len(sources)
    result = s["result"] or f"+{n} {plural(n, 'источник', 'источника', 'источников')}"
    pal = c.palette(theme, kind or DEFAULT_KIND)
    h = c.headline(s["headline"], s["context"], prefix="h")
    js, times = c.headline_js(h, 0.15 if s["context"] else 0.1, 0.6)
    c0 = max(0.7, times[-1] if times else 0.7)
    bot_t = c0 + n * 0.22 + 0.04
    s0 = bot_t + 0.6
    res_t = s0 + 0.35 + (n - 1) * 0.15 + 0.2
    dur = res_t + 0.8
    exit_t = dur - 0.15
    bot, files = c.icon_html(s["bot"], "em", name="bot")

    rows = []
    for i, text in enumerate(sources):
        room = max(0.0, (1000 - chip_width(text)) / 2)
        dx = DX[n][i]
        dx = int(min(abs(dx), room)) * (1 if dx >= 0 else -1)
        margin = f"margin-left:{2 * dx}px" if dx >= 0 else f"margin-right:{-2 * dx}px"
        top = ROWS[n][i]
        rows.append(f'<div class="row" style="top:{top}px"><div class="chip" id="ch{i}" '
                    f'style="{margin}">{c.esc(text)}</div></div>')
        fx, fy = FROM[i]
        js.append(f'tl.fromTo("#ch{i}", {{ opacity: 0, x: {fx}, y: {fy}, rotation: {ROT[i] * 2} }}, '
                  f'{{ opacity: 1, x: 0, y: 0, rotation: {ROT[i]}, duration: 0.45, '
                  f'ease: "back.out(1.5)" }}, {c.fmt(c0 + i * 0.22)});')
        js.append(f'tl.fromTo("#ch{i}", {{ x: 0, y: 0, scale: 1, opacity: 1 }}, '
                  f'{{ x: {-dx}, y: {BOT_CY - top - 50}, scale: 0.2, opacity: 0, duration: 0.4, '
                  f'ease: "power2.in", immediateRender: false }}, {c.fmt(s0 + i * 0.15)});')
    js.append('tl.fromTo("#bot", { opacity: 0, scale: 0.6 }, '
              f'{{ opacity: 1, scale: 1, duration: 0.4, ease: "back.out(2)" }}, {c.fmt(bot_t)});')
    for i in range(n):
        js.append(f'tl.fromTo("#bot", {{ scale: 1 }}, {{ scale: 1.12, duration: 0.07, yoyo: true, '
                  f'repeat: 1, immediateRender: false }}, {c.fmt(s0 + 0.35 + i * 0.15)});')
    js.append(f'tl.fromTo("#result", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.3 }}, '
              f'{c.fmt(res_t)});')
    if h["ctx_id"]:
        js.append(f'fadeIn("#{h["ctx_id"]}", 0.02);')

    content = (h["html"] + "".join(rows) + f'<div id="bot">{bot}</div>'
               f'<div id="result">{c.esc(result)}</div>')
    deco, deco_js = c.decor(pal, layout, s["tags"], dur, BLOBS)
    body, bg, size = c.compose(pal, layout, deco, content, dur, BOX)
    js += deco_js
    js += [f'blurOut("{sel}", {c.fmt(exit_t)});' for sel in ("#hhead", "#bot", "#result")]

    bot_name = "из файла" if files else s["bot"]
    events = c.headline_events(h, times)
    if s["context"]:
        events.append(c.ev(0.02, f"строка-контекст «{s['context']}»"))
    events += [
        c.ev(c0, "плашки-источники слетаются: " + ", ".join(f"«{x}»" for x in sources)),
        c.ev(c0 + (n - 1) * 0.22 + 0.45, "все источники видны целиком"),
        c.ev(bot_t, f"бот {bot_name} появляется"),
        c.ev(s0, "бот всасывает источники"),
        c.ev(s0 + 0.35, "бот пульсирует на каждом источнике"),
        c.ev(res_t, f"итог «{result}»"),
        c.ev(exit_t, "уход: всё размывается"),
    ]
    describes = (f"источники → бот: {n} плашки слетаются, бот {bot_name} их всасывает с пульсом, "
                 f"итог «{result}»; заголовок «{h['plain']}»")
    return c.result(c.base_css(pal, layout) + css(pal), body, js, dur, events, pal, layout, bg,
                    size, files, BASE_TAGS, describes, preview_t=bot_t + 0.45)
