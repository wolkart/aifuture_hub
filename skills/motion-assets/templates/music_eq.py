"""Эквалайзер и ползунок громкости: столбики пляшут, на «музыку» всё взлетает до максимума,
на «громкость» ползунок съезжает на нужный уровень и столбики садятся. Родная тема — тёмная.

Когда брать: «музыку подобрал сам», «громкость выставил сам» — показать, что звук живой и
громкость меняется по слову. Моменты up_at / down_at — секунды от начала сцены.
"""
import random

import _common as c

NAME = "music_eq"
TITLE = "Эквалайзер и громкость"
DEFAULT_KIND = "dark"
BOX = (220, 1500)
BASE_TAGS = ["музыка", "звук", "громкость", "эквалайзер", "трек"]
SLOTS = {
    "context": {"about": "строка-контекст над заголовком, можно пусто", "default": ""},
    "headline": {"about": "заголовок по словам, можно пусто", "default": ""},
    "label": {"about": "подпись у ползунка", "default": "ГРОМКОСТЬ"},
    "up_at": {"about": "секунда, когда музыка взлетает", "default": 0.1},
    "down_at": {"about": "секунда, когда громкость встаёт на уровень", "default": 1.6},
    "level": {"about": "итоговый уровень ползунка 0…1", "default": 0.55},
    "duration": {"about": "длина сцены, с", "default": 3.0},
    "tags": {"about": "до 4 фоновых слов", "default": ["бит", "трек", "звук", "громче"]},
}
N_BARS = 26
QUIET = 0.22


def css(pal):
    panel = c.mix(pal["deep"], c.BLACK, 0.25)
    return f"""
.stage {{ position: absolute; inset: 0; perspective: 1500px; }}
#eq {{ position: absolute; left: 90px; right: 90px; top: 640px; height: 760px; transform-style: preserve-3d; opacity: 0; }}
#panel {{ position: absolute; inset: 0; border-radius: 40px;
  background: linear-gradient(180deg, {c.rgba(c.mix(panel, c.WHITE, 0.06), 0.96)}, {c.rgba(panel, 0.96)});
  border: 2px solid {c.rgba(pal['sec'], 0.35)}; box-shadow: 0 50px 120px rgba(0, 0, 0, 0.6); }}
#bars {{ position: absolute; left: 60px; right: 60px; top: 70px; height: 400px; display: flex; align-items: flex-end;
  gap: 10px; transform-origin: 50% 100%; }}
.b {{ flex: 1 1 0; height: 100%; border-radius: 10px 10px 4px 4px; transform-origin: 50% 100%;
  background: linear-gradient(0deg, {pal['sec']}, {pal['acc']}); box-shadow: 0 0 24px {c.rgba(pal['acc'], 0.35)}; }}
#lbl {{ position: absolute; left: 60px; top: 520px; font-family: var(--display); font-size: 54px; font-weight: 700;
  letter-spacing: 0.04em; color: {c.WHITE}; }}
#track {{ position: absolute; left: 60px; right: 60px; top: 620px; height: 26px; border-radius: 13px;
  background: {c.rgba(c.WHITE, 0.1)}; }}
#fill {{ position: absolute; left: 0; top: 0; width: 100%; height: 100%; border-radius: 13px; transform-origin: 0 50%;
  background: linear-gradient(90deg, {pal['sec']}, {pal['acc']}); }}
#knob {{ position: absolute; left: -28px; top: -15px; width: 56px; height: 56px; border-radius: 50%; background: {c.WHITE};
  box-shadow: 0 0 0 6px {c.rgba(pal['acc'], 0.45)}, 0 10px 24px rgba(0, 0, 0, 0.5); }}
.wave {{ position: absolute; left: 540px; top: 1020px; width: 700px; height: 700px; margin: -350px 0 0 -350px;
  border-radius: 50%; border: 4px solid {c.rgba(pal['acc'], 0.5)}; opacity: 0; }}
"""


def build(slots, theme, kind=None, layout="full"):
    s = c.merge_slots(SLOTS, slots)
    pal = c.palette(theme, kind or DEFAULT_KIND)
    dur = max(1.5, float(s["duration"]))
    up, down = float(s["up_at"]), float(s["down_at"])
    level = min(1.0, max(0.05, float(s["level"])))
    h = c.headline(s["headline"], s["context"], prefix="h", top=300) if s["headline"] else None
    js, times = (c.headline_js(h, 0.1, 0.8) if h else ([], []))
    track_w = 1080 - 180 - 120
    rnd = random.Random(7)
    bars = "".join(f'<div class="b" id="b{i}"></div>' for i in range(N_BARS))
    waves = "".join(f'<div class="wave" id="wv{i}"></div>' for i in range(3))
    content = ((h["html"] if h else "") + f'<div class="stage">{waves}<div id="eq"><div id="panel"></div>'
               f'<div id="bars">{bars}</div><div id="lbl">{c.esc(s["label"])}</div>'
               f'<div id="track"><div id="fill"></div><div id="knob"></div></div></div></div>')
    deco, deco_js = c.decor(pal, layout, s["tags"], dur)
    box = BOX if h else (560, 1480)
    body, bg, size = c.compose(pal, layout, deco, content, dur, box)

    js += [
        'tl.fromTo("#eq", { opacity: 0, y: 80, rotationX: 30, scale: 0.9 }, { opacity: 1, y: 0, rotationX: 14, '
        'scale: 1, duration: 0.4, ease: "power3.out" }, 0);',
        f'tl.fromTo("#eq", {{ rotationY: -10 }}, {{ rotationY: 6, duration: {c.fmt(dur)}, ease: "sine.inOut", '
        f'immediateRender: false }}, 0);',
    ]
    for i in range(N_BARS):   # каждый столбик качается со своим шагом: детерминированно, без Math.random
        lo, hi = round(rnd.uniform(0.15, 0.45), 2), round(rnd.uniform(0.6, 1.0), 2)
        d = round(rnd.uniform(0.12, 0.24), 3)
        reps = int(dur / d) + 1
        js.append(f'tl.fromTo("#b{i}", {{ scaleY: {lo} }}, {{ scaleY: {hi}, duration: {d}, repeat: {reps}, yoyo: true, '
                  f'ease: "sine.inOut" }}, {c.fmt(rnd.uniform(0, 0.1))});')
    js += [
        f'tl.fromTo("#bars", {{ scaleY: {QUIET} }}, {{ scaleY: 1, duration: 0.25, ease: "back.out(1.6)" }}, {c.fmt(up)});',
        f'tl.fromTo("#bars", {{ scaleY: 1 }}, {{ scaleY: {level}, duration: 0.6, ease: "power2.inOut", '
        f'immediateRender: false }}, {c.fmt(down)});',
        f'tl.fromTo("#fill", {{ scaleX: {QUIET} }}, {{ scaleX: 1, duration: 0.25, ease: "power3.out" }}, {c.fmt(up)});',
        f'tl.fromTo("#fill", {{ scaleX: 1 }}, {{ scaleX: {level}, duration: 0.6, ease: "power2.inOut", '
        f'immediateRender: false }}, {c.fmt(down)});',
        f'tl.fromTo("#knob", {{ x: {track_w * QUIET:.0f} }}, {{ x: {track_w:.0f}, duration: 0.25, ease: "power3.out" }}, '
        f'{c.fmt(up)});',
        f'tl.fromTo("#knob", {{ x: {track_w:.0f} }}, {{ x: {track_w * level:.0f}, duration: 0.6, ease: "power2.inOut", '
        f'immediateRender: false }}, {c.fmt(down)});',
    ]
    js += [f'tl.fromTo("#wv{i}", {{ scale: 0.4, opacity: 0.9 }}, {{ scale: 1.6, opacity: 0, duration: 0.9, '
           f'ease: "power2.out" }}, {c.fmt(up + 0.05 + i * 0.15)});' for i in range(3)]
    js += deco_js

    events = [c.ev(0.0, "панель эквалайзера влетает в 3D, музыка тихая"),
              c.ev(up, "музыка взлетает: столбики и ползунок на максимум, волны"),
              c.ev(down, f"громкость встаёт на уровень {int(level * 100)}%"),
              c.ev(min(dur - 0.05, down + 0.6), "эквалайзер на нужной громкости")]
    if h:
        events += c.headline_events(h, times)
    describes = f"эквалайзер с ползунком «{s['label']}»: тихо → максимум → уровень {int(level * 100)}%"
    return c.result(c.base_css(pal, layout) + css(pal), body, js, dur, events, pal, layout, bg, size, [],
                    BASE_TAGS, describes, preview_t=min(up + 0.4, dur - 0.1))
