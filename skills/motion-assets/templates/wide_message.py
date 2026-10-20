"""Акцент вокруг головы (основа — `wide_drawer`). Карточка-сообщение у головы (16:9): белая карточка «аватар · имя · время + текст» проявляется
сбоку, ниже может выскочить синий ответ. Подходит и под комментарий, и под переписку с ботом.
Родная тема — светлая; раскладка — overlay поверх кадра с говорящей головой.

Когда брать: «написал агенту — он ответил», вопрос подписчика, сообщение клиента — показать прямо
рядом с лицом, не уходя на запись экрана. Референсы: `labada-popups` (чат), `voronkov-claude-montage`
(комментарий, пуш).
"""
import _common as c
import _wide as w

NAME = "wide_message"
TITLE = "Сообщение у головы (16:9)"
DEFAULT_KIND = "light"
FORMAT = w.FORMAT
DEFAULT_LAYOUT = "overlay"
BASE_TAGS = ["сообщение", "чат", "комментарий", "ответ"]
SLOTS = {
    "name": {"about": "кто пишет", "default": "Подписчик"},
    "avatar": {"about": "значок аватара: эмодзи/буква или путь к картинке", "default": "П"},
    "time": {"about": "время/подпись мелко, можно пусто", "default": "сейчас"},
    "text": {"about": "текст сообщения", "default": "А можно так же, но для моего бизнеса?"},
    "reply": {"about": "ответ синим пузырём, можно пусто", "default": "Можно. Показываю как"},
    "at": {"about": "секунда появления карточки", "default": 0.2},
    "reply_at": {"about": "секунда ответа (0 — через 1,2 с)", "default": 0},
    "side": {"about": "right | left", "default": "right"},
    "duration": {"about": "длина, с (0 — последнее + 2 с)", "default": 0},
    "tags": {"about": "доп. теги", "default": []},
}


def build(slots, theme, kind=None, layout=None):
    layout = layout or DEFAULT_LAYOUT
    s = c.merge_slots(SLOTS, slots)
    if s["side"] not in w.SIDES:
        raise ValueError(f"side {s['side']!r}: одна из {', '.join(w.SIDES)}")
    pal = c.palette(theme, kind or DEFAULT_KIND)
    b0, b1 = w.blues(pal)
    av, files = c.icon_html(s["avatar"], "", name="avatar")
    tm = f'<span class="tm">{c.esc(s["time"])}</span>' if s["time"] else ""
    reply = f'<div class="rep" id="rep">{c.esc(s["reply"])}</div>' if s["reply"] else ""
    side = "right:120px" if s["side"] == "right" else "left:120px"
    content = (f'<div id="grp" style="position:absolute; {side}; top:{int(w.WH * 0.26)}px; width:640px">'
               f'<div class="msg" id="msg"><div class="hd"><div class="av">{av}</div><b>{c.esc(s["name"])}</b>{tm}</div>'
               f'<div class="tx">{c.esc(s["text"])}</div></div>{reply}</div>')
    at = float(s["at"])
    rat = float(s["reply_at"]) or (at + 1.2)
    last = rat if s["reply"] else at
    end = float(s["duration"]) or (last + 2.0)
    dur = end + w.EXIT + w.TAIL
    body, bg, size = w.compose(pal, layout, content)
    js = [f'popIn("#msg", {c.fmt(max(0.0, at - 0.12))});']
    events = [c.ev(max(0.0, at - 0.12), f"карточка сообщения от «{s['name']}» проявляется"),
              c.ev(at + 0.2, f"текст виден: «{s['text']}»")]
    sfx = [w.cue(at - 0.12, w.POP)]
    if s["reply"]:
        js.append(f'popIn("#rep", {c.fmt(max(0.0, rat - 0.12))}, 0.22);')
        events.append(c.ev(max(0.0, rat - 0.12), f"ответ «{s['reply']}» выскакивает"))
        sfx.append(w.cue(rat - 0.12, w.POP))
    js.append(f'sway("#grp", {c.fmt(at)}, {c.fmt(max(0.5, end - at))}, 2);')
    js.append(f'groupOut("#grp", {c.fmt(end)});')
    events.append(c.ev(end, "сообщение уходит размытием"))
    style = w.css(pal, layout) + f"""
.msg {{ background: {c.WHITE}; border-radius: 26px; padding: 24px 30px 28px; color: {pal['ink']}; opacity: 0;
  box-shadow: 0 22px 60px rgba(0, 0, 0, 0.22), 0 2px 6px rgba(0, 0, 0, 0.08); }}
.hd {{ display: flex; align-items: center; gap: 14px; font-size: 28px; margin-bottom: 12px; }}
.av {{ width: 54px; height: 54px; border-radius: 50%; background: linear-gradient(135deg, {b0}, {b1}); color: {c.WHITE};
  display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: 800; overflow: hidden; }}
.av img {{ width: 100%; height: 100%; object-fit: cover; }}
.tm {{ margin-left: auto; font-size: 22px; color: {pal['muted']}; font-weight: 600; }}
.tx {{ font-size: 34px; font-weight: 600; line-height: 1.28; }}
.rep {{ margin: 16px 0 0 auto; width: fit-content; max-width: 520px; padding: 18px 26px; border-radius: 24px 24px 6px 24px;
  background: linear-gradient(135deg, {b0}, {b1}); color: {c.WHITE}; font-size: 32px; font-weight: 700; line-height: 1.25; opacity: 0;
  box-shadow: 0 16px 44px {c.rgba(b0, 0.4)}; }}
"""
    describes = f"сообщение у головы от «{s['name']}»: «{s['text']}»" + (f" → ответ «{s['reply']}»" if s["reply"] else "")
    return w.result(style, body, js, dur, events, pal, layout, bg, size, files, BASE_TAGS + list(s["tags"]),
                    describes, preview_t=last + 0.4, sfx=sfx)
