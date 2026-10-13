"""Пост в 3D: наклонённая карточка поста, полоса сканирования, серые строки-заглушки
сменяются печатающимся текстом, бейдж. Родная тема — тёмная.

Когда брать: «нейросеть/сервис переписывает, генерирует, проверяет текст» — показать
превращение черновика в готовый пост.
"""
import _common as c

NAME = "post_3d"
TITLE = "Пост в 3D"
DEFAULT_KIND = "dark"
BOX = (180, 1540)
BASE_TAGS = ["пост", "текст", "генерация", "печать", "карточка", "заголовок"]
SLOTS = {
    "context": {"about": "строка-контекст над заголовком, можно пусто", "default": "Каждый пост"},
    "headline": {"about": "заголовок по словам; *слово* — акцент, _слово_ — второй цвет",
                 "default": "Нейросеть переписывает под *твой стиль*"},
    "name": {"about": "имя в шапке карточки", "default": "Мой канал"},
    "time": {"about": "подпись под именем", "default": "сегодня, 09:00"},
    "text": {"about": "текст, который печатается в карточке",
             "default": "Свежая новость — коротко, по делу и твоим голосом."},
    "badge": {"about": "бейдж над карточкой", "default": "✦ ИИ"},
    "tags": {"about": "до 4 фоновых слов", "default": ["стиль", "ИИ", "текст", "голос"]},
}
BARS = (94, 82, 90, 66, 78)
TYPE_AT = 1.5


def css(pal, text_px):
    return f"""
#card {{ position: absolute; left: 110px; top: 760px; width: 860px; height: 760px; border-radius: 40px;
  padding: 50px 54px; overflow: hidden; opacity: 0;
  background: {c.rgba(c.mix(pal['deep'], pal['deep_end'], 0.35), 0.92)};
  border: 2px solid {c.rgba(pal['sec'], 0.35)}; box-shadow: 0 40px 120px rgba(0, 0, 0, 0.6); }}
.hd {{ display: flex; align-items: center; gap: 20px; margin-bottom: 34px; }}
.av {{ width: 80px; height: 80px; border-radius: 50%;
  background: linear-gradient(135deg, {pal['sec']}, {pal['acc']}); }}
.nm {{ font-size: 36px; font-weight: 800; color: {c.WHITE}; }}
.tm {{ font-size: 26px; color: {pal['muted']}; }}
.bar {{ height: 30px; border-radius: 15px; background: rgba(255, 255, 255, 0.14); margin-bottom: 26px; }}
#txt {{ position: absolute; left: 54px; right: 54px; top: 190px; font-size: {text_px}px; font-weight: 700;
  line-height: 1.32; color: {c.WHITE}; }}
.ch {{ opacity: 0; }}
#scan {{ position: absolute; left: 0; right: 0; height: 140px; top: -160px;
  background: linear-gradient(180deg, {c.rgba(pal['acc'], 0)} 0%, {c.rgba(pal['acc'], 0.35)} 50%,
  {c.rgba(pal['acc'], 0)} 100%); }}
#badge {{ position: absolute; right: 70px; top: 700px; padding: 18px 34px; border-radius: 999px;
  font-size: 38px; font-weight: 800; color: {c.WHITE}; opacity: 0;
  background: linear-gradient(90deg, {pal['sec']}, {c.mix(pal['sec'], pal['acc'], 0.5)});
  box-shadow: 0 0 60px {c.rgba(pal['sec'], 0.6)}; }}
"""


def typed(text):
    """Каждая буква — span (появляется по одной); пробелы — обычный текст, по ним перенос."""
    return " ".join("".join(f'<span class="ch">{c.esc(ch)}</span>' for ch in word)
                    for word in str(text).split())


def build(slots, theme, kind=None, layout="full"):
    s = c.merge_slots(SLOTS, slots)
    pal = c.palette(theme, kind or DEFAULT_KIND)
    h = c.headline(s["headline"], s["context"], prefix="h")
    js, times = c.headline_js(h, 0.15 if s["context"] else 0.1, 1.0)
    words_end = times[-1] + 0.32 if times else 0.5
    text = " ".join(str(s["text"]).split())
    type_d = min(2.2, max(0.8, len(text) / 45))
    type_end = TYPE_AT + type_d
    dur = max(3.6, type_end + 0.7, words_end + 0.6)
    exit_t = dur - 0.15

    bars = "".join(f'<div class="bar" id="b{i}" style="width:{w}%"></div>' for i, w in enumerate(BARS))
    content = (h["html"] + '<div id="card"><div class="hd"><div class="av"></div><div>'
               f'<div class="nm">{c.esc(s["name"])}</div><div class="tm">{c.esc(s["time"])}</div>'
               f'</div></div><div id="bars">{bars}</div><div id="txt">{typed(text)}</div>'
               f'<div id="scan"></div></div><div id="badge">{c.esc(s["badge"])}</div>')
    deco, deco_js = c.decor(pal, layout, s["tags"], dur)
    body, bg, size = c.compose(pal, layout, deco, content, dur, BOX)

    if h["ctx_id"]:
        js.append(f'fadeIn("#{h["ctx_id"]}", 0.02);')
    js += [
        'tl.fromTo("#card", { opacity: 0, y: 80, rotationX: 25, rotationY: -14, transformPerspective: 1600 }, '
        '{ opacity: 1, y: 0, rotationX: 10, rotationY: -14, transformPerspective: 1600, duration: 0.5, '
        'ease: "power3.out" }, 0.2);',
        f'tl.fromTo("#card", {{ rotationY: -14 }}, {{ rotationY: -6, duration: {c.fmt(dur - 1.0)}, '
        f'ease: "sine.inOut", immediateRender: false }}, 0.7);',
        'tl.fromTo("#badge", { opacity: 0, scale: 0.6 }, '
        '{ opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)" }, 0.7);',
        'tl.fromTo("#scan", { y: 0 }, { y: 940, duration: 1.1, ease: "power1.inOut" }, 1.1);',
    ]
    js += [f'tl.fromTo("#b{i}", {{ opacity: 1, x: 0 }}, {{ opacity: 0, x: 40, duration: 0.18, '
           f'immediateRender: false }}, {c.fmt(1.25 + i * 0.18)});' for i in range(len(BARS))]
    n_chars = max(1, len(text.replace(" ", "")))
    js.append(f'tl.fromTo("#txt .ch", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.01, '
              f'stagger: {type_d / n_chars:.4f} }}, {c.fmt(TYPE_AT)});')
    js += deco_js
    js += [f'blurOut("{sel}", {c.fmt(exit_t)});' for sel in ("#hhead", "#card", "#badge")]

    events = c.headline_events(h, times)
    if s["context"]:
        events.append(c.ev(0.02, f"строка-контекст «{s['context']}»"))
    events += [
        c.ev(0.2, "карточка поста влетает в 3D"),
        c.ev(0.7, f"карточка «{s['name']}» видна целиком, серые строки-заглушки"),
        c.ev(0.7, f"бейдж «{s['badge']}»"),
        c.ev(1.1, "полоса сканирования идёт по карточке"),
        c.ev(1.25, "серые строки исчезают"),
        c.ev(TYPE_AT, "печатается текст поста"),
        c.ev(type_end, f"текст напечатан целиком: «{text}»"),
        c.ev(exit_t, "уход: всё размывается"),
    ]
    describes = (f"пост в 3D: наклонённая карточка «{s['name']}», полоса сканирования, серые строки "
                 f"сменяются печатью «{text}», бейдж «{s['badge']}»; заголовок «{h['plain']}»")
    style = c.base_css(pal, layout) + css(pal, c.fit_px(text, 48, 70, 34))
    return c.result(style, body, js, dur, events, pal, layout, bg, size, [], BASE_TAGS, describes,
                    preview_t=min(type_end + 0.3, exit_t - 0.1))
