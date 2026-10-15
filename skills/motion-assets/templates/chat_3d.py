"""Окно чата в 3D: просьба печатается в пузыре, ассистент отвечает строками с галочками.
Родная тема — тёмная.

Когда брать: «я просто попросил нейросеть…», «одна просьба — и она делает всё» — показать
сам разговор: короткая просьба и что из неё вышло. Имя ассистента и строки — слотами.
"""
import _common as c

NAME = "chat_3d"
TITLE = "Чат в 3D"
DEFAULT_KIND = "dark"
BOX = (220, 1560)
BASE_TAGS = ["чат", "нейросеть", "просьба", "ответ", "ассистент", "печать"]
SLOTS = {
    "context": {"about": "строка-контекст над заголовком, можно пусто", "default": ""},
    "headline": {"about": "заголовок по словам, можно пусто", "default": ""},
    "name": {"about": "имя ассистента в шапке окна", "default": "Ассистент"},
    "request": {"about": "просьба, которая печатается", "default": "Сделай, как я говорю"},
    "replies": {"about": "строки ответа (1–5), появляются по одной с галочкой",
                "default": ["Готово", "Проверил", "Отправил"]},
    "type_s": {"about": "сколько секунд печатается просьба", "default": 1.0},
    "duration": {"about": "длина сцены, с", "default": 3.5},
    "tags": {"about": "до 4 фоновых слов", "default": ["чат", "просьба", "ответ", "готово"]},
}


def css(pal):
    win = c.mix(pal["deep"], c.BLACK, 0.2)
    return f"""
.stage {{ position: absolute; inset: 0; perspective: 1500px; }}
#win {{ position: absolute; left: 80px; right: 80px; top: 600px; height: 900px; border-radius: 40px; opacity: 0;
  background: linear-gradient(180deg, {c.rgba(c.mix(win, c.WHITE, 0.06), 0.97)}, {c.rgba(win, 0.97)});
  border: 2px solid {c.rgba(pal['sec'], 0.4)}; box-shadow: 0 50px 120px rgba(0, 0, 0, 0.6); }}
#hd {{ position: absolute; left: 0; right: 0; top: 0; height: 120px; border-bottom: 2px solid {c.rgba(c.WHITE, 0.08)};
  display: flex; align-items: center; gap: 22px; padding: 0 40px; }}
.av {{ width: 70px; height: 70px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 40px; color: {c.WHITE}; background: linear-gradient(135deg, {pal['sec']}, {pal['acc']}); }}
.nm {{ font-size: 40px; font-weight: 800; color: {c.WHITE}; }}
.st {{ font-size: 26px; color: {pal['muted']}; }}
#req {{ position: absolute; right: 40px; top: 170px; max-width: 760px; padding: 28px 34px; border-radius: 34px 34px 8px 34px;
  font-size: 44px; font-weight: 700; line-height: 1.25; color: {pal['deep']}; background: {pal['acc']}; opacity: 0; }}
#req .ch {{ opacity: 0; }}
.rep {{ position: absolute; left: 40px; right: 120px; padding: 22px 30px; border-radius: 30px 30px 30px 8px;
  font-size: 38px; font-weight: 700; color: {c.WHITE}; background: {c.rgba(c.WHITE, 0.08)};
  border: 2px solid {c.rgba(pal['ok'], 0.35)}; opacity: 0; display: flex; align-items: center; gap: 18px; }}
.ok {{ width: 46px; height: 46px; flex: none; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 30px; color: {pal['deep']}; background: {pal['ok']}; }}
"""


def build(slots, theme, kind=None, layout="full"):
    s = c.merge_slots(SLOTS, slots)
    pal = c.palette(theme, kind or DEFAULT_KIND)
    reps = [str(x) for x in (s["replies"] or [])][:5]
    type_s = max(0.3, float(s["type_s"]))
    t_type = 0.45
    t_rep = t_type + type_s + 0.25
    step = 0.32
    dur = max(float(s["duration"]), t_rep + step * len(reps) + 0.6)
    h = c.headline(s["headline"], s["context"], prefix="h", top=300) if s["headline"] else None
    js, times = (c.headline_js(h, 0.1, 0.8) if h else ([], []))
    req_chars = "".join(f'<span class="ch">{c.esc(ch)}</span>' for ch in str(s["request"]))
    lines = "".join(f'<div class="rep" id="rp{i}" style="top:{420 + i * 112}px"><span class="ok">✓</span>'
                    f'<span>{c.esc(r)}</span></div>' for i, r in enumerate(reps))
    content = ((h["html"] if h else "") + '<div class="stage"><div id="win"><div id="hd"><div class="av">✦</div>'
               f'<div><div class="nm">{c.esc(s["name"])}</div><div class="st">в сети</div></div></div>'
               f'<div id="req">{req_chars}</div>{lines}</div></div>')
    deco, deco_js = c.decor(pal, layout, s["tags"], dur)
    box = BOX if h else (560, 1520)
    body, bg, size = c.compose(pal, layout, deco, content, dur, box)
    n = max(1, len(str(s["request"])))
    js += [
        'tl.fromTo("#win", { opacity: 0, y: 90, rotationX: 28, rotationY: -14, scale: 0.9 }, { opacity: 1, y: 0, '
        'rotationX: 10, rotationY: -8, scale: 1, duration: 0.45, ease: "power3.out" }, 0);',
        f'tl.fromTo("#win", {{ rotationY: -8 }}, {{ rotationY: 4, duration: {c.fmt(dur - 0.4)}, ease: "sine.inOut", '
        f'immediateRender: false }}, 0.45);',
        f'tl.fromTo("#req", {{ opacity: 0, scale: 0.9 }}, {{ opacity: 1, scale: 1, duration: 0.2, ease: "back.out(2)" }}, '
        f'{c.fmt(t_type - 0.1)});',
        f'tl.fromTo("#req .ch", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.01, stagger: {type_s / n:.4f} }}, '
        f'{c.fmt(t_type)});',
    ]
    js += [f'tl.fromTo("#rp{i}", {{ opacity: 0, x: -60, scale: 0.94 }}, {{ opacity: 1, x: 0, scale: 1, duration: 0.25, '
           f'ease: "back.out(1.8)" }}, {c.fmt(t_rep + i * step)});' for i in range(len(reps))]
    js += deco_js
    events = [c.ev(0.0, f"окно чата «{s['name']}» влетает в 3D"),
              c.ev(t_type, f"печатается просьба «{s['request']}»"),
              c.ev(t_type + type_s, "просьба напечатана целиком")]
    events += [c.ev(t_rep + i * step, f"ответ: ✓ {r}") for i, r in enumerate(reps)]
    if reps:
        events.append(c.ev(t_rep + step * (len(reps) - 1) + 0.25, "ответ виден целиком"))
    if h:
        events += c.headline_events(h, times)
    describes = f"чат в 3D: печатается «{s['request']}», ответ строками с галочками: {'; '.join(reps)}"
    return c.result(c.base_css(pal, layout) + css(pal), body, js, dur, events, pal, layout, bg, size, [],
                    BASE_TAGS, describes, preview_t=min(dur - 0.1, t_rep + step * len(reps) + 0.2))
