"""Ноутбук в 3D, два режима. Родная тема — тёмная.

  open    — ноутбук падает сверху и раскрывает крышку; на экране идёт видео из слота
            screen, а в углу экрана — ноутбук поменьше с тем же видео: ролик внутри ролика;
  to_file — открытый ноутбук захлопывается, сжимается и превращается в светящуюся
            3D-карточку-файл с подписью («всё это — один файл»).

Когда брать: open — «графику подбирает сам», «монтаж идёт прямо сейчас», показать
результат на экране; to_file — «и всё это делает один скилл / один файл». Видео на экран
приходит файлом (кусок ролика, запись экрана); без него экран светится пустым.
"""
from pathlib import Path

import _common as c

NAME = "laptop_3d"
TITLE = "Ноутбук в 3D"
DEFAULT_KIND = "dark"
BOX = (240, 1560)
BASE_TAGS = ["ноутбук", "компьютер", "экран", "3D", "графика"]
MODES = ("open", "to_file")
VIDEO_EXT = {".mp4", ".mov", ".webm", ".m4v"}
SLOTS = {
    "mode": {"about": "open — падает и открывается; to_file — закрывается и становится файлом",
             "default": "open"},
    "context": {"about": "строка-контекст над заголовком, можно пусто", "default": ""},
    "headline": {"about": "заголовок по словам, можно пусто", "default": ""},
    "screen": {"about": "видео на экран (MP4/MOV), можно пусто", "default": ""},
    "screen_start": {"about": "с какой секунды видео начать", "default": 0.0},
    "label": {"about": "подпись на карточке-файле (to_file)", "default": "скилл"},
    "sublabel": {"about": "строка под подписью (to_file), можно пусто", "default": "один файл"},
    "duration": {"about": "длина сцены, с", "default": 4.0},
    "tags": {"about": "до 4 фоновых слов", "default": ["экран", "монтаж", "ролик", "графика"]},
}
W, H, D = 700, 450, 440          # крышка (ширина × высота) и глубина корпуса
LAP_Y = 1030                     # линия петли по вертикали


def css(pal):
    alu0, alu1 = c.mix(pal["muted"], c.WHITE, 0.55), c.mix(pal["muted"], pal["deep"], 0.35)
    return f"""
.stage {{ position: absolute; inset: 0; perspective: 1700px; perspective-origin: 50% 900px; }}
#drop {{ position: absolute; left: {540 - W / 2}px; top: {LAP_Y}px; width: {W}px; height: 0;
  transform-style: preserve-3d; }}
#lap {{ position: absolute; left: 0; top: 0; width: {W}px; height: 0; transform-style: preserve-3d; }}
.lid {{ position: absolute; left: 0; top: -{H}px; width: {W}px; height: {H}px; transform-origin: 50% 100%;
  transform-style: preserve-3d; }}
.face {{ position: absolute; inset: 0; border-radius: 26px; backface-visibility: hidden; }}
.front {{ background: {c.mix(pal['deep_end'], c.BLACK, 0.4)}; border: 3px solid {c.rgba(alu0, 0.9)};
  box-shadow: 0 0 80px {c.rgba(pal['sec'], 0.35)}; }}
.back {{ transform: rotateY(180deg); background: linear-gradient(160deg, {alu0}, {alu1}); }}
.screen {{ position: absolute; inset: 18px 18px 30px; border-radius: 12px; overflow: hidden;
  background: radial-gradient(ellipse at 50% 40%, {c.mix(pal['deep'], pal['sec'], 0.35)}, {pal['deep_end']}); }}
.screen video {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
.glass {{ position: absolute; inset: 0; background: linear-gradient(125deg, rgba(255, 255, 255, 0.16) 0%,
  rgba(255, 255, 255, 0) 38%); pointer-events: none; }}
.mini {{ position: absolute; right: 22px; bottom: 22px; width: 210px; height: 150px; }}
.mini .mscr {{ position: absolute; left: 14px; right: 14px; top: 0; height: 120px; border-radius: 8px; overflow: hidden;
  background: {c.mix(pal['deep_end'], c.BLACK, 0.4)}; border: 3px solid {c.rgba(alu0, 0.9)}; }}
.mini .mscr video {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
.mini .mbase {{ position: absolute; left: 0; right: 0; bottom: 0; height: 18px; border-radius: 3px 3px 10px 10px;
  background: linear-gradient(180deg, {alu0}, {alu1}); clip-path: polygon(4% 0, 96% 0, 100% 100%, 0 100%); }}
.deck {{ position: absolute; left: 0; top: 0; width: {W}px; height: {D}px; transform-origin: 50% 0;
  transform: rotateX(90deg); border-radius: 8px 8px 28px 28px;
  background: linear-gradient(180deg, {alu1}, {alu0} 70%); box-shadow: inset 0 0 0 2px {c.rgba(c.WHITE, 0.25)}; }}
.keys {{ position: absolute; left: 50px; right: 50px; top: 40px; height: 210px; border-radius: 10px;
  background: repeating-linear-gradient(90deg, {c.rgba(pal['deep_end'], 0.75)} 0 36px, transparent 36px 44px),
  repeating-linear-gradient(0deg, transparent 0 34px, {c.rgba(alu1, 0.9)} 34px 42px); }}
.pad {{ position: absolute; left: 240px; right: 240px; top: 280px; height: 120px; border-radius: 14px;
  background: {c.rgba(c.WHITE, 0.18)}; box-shadow: inset 0 0 0 2px {c.rgba(c.WHITE, 0.25)}; }}
#shade {{ position: absolute; left: {540 - W * 0.45}px; top: {LAP_Y + 200}px; width: {W * 0.9}px; height: 90px;
  border-radius: 50%; background: rgba(0, 0, 0, 0.6); filter: blur(30px); opacity: 0; }}
.ring {{ position: absolute; left: 540px; top: {LAP_Y - 120}px; width: 560px; height: 560px; margin: -280px 0 0 -280px;
  border-radius: 50%; border: 3px solid {c.rgba(pal['sec'], 0.55)}; opacity: 0; }}
#file {{ position: absolute; left: 540px; top: {LAP_Y - 140}px; width: 400px; height: 500px; margin: -250px 0 0 -200px;
  opacity: 0; transform-style: preserve-3d; }}
#file .card {{ position: absolute; inset: 0; border-radius: 40px; overflow: hidden;
  background: linear-gradient(160deg, {c.mix(pal['deep'], pal['sec'], 0.45)}, {pal['deep_end']} 85%);
  border: 3px solid {c.rgba(pal['acc'], 0.85)};
  box-shadow: 0 0 90px {c.rgba(pal['acc'], 0.45)}, 0 40px 90px rgba(0, 0, 0, 0.6);
  clip-path: polygon(0 0, 72% 0, 100% 22%, 100% 100%, 0 100%); }}
#file .fold {{ position: absolute; right: 0; top: 0; width: 112px; height: 110px;
  background: linear-gradient(225deg, transparent 50%, {c.mix(pal['acc'], pal['deep'], 0.25)} 50%);
  border-radius: 0 0 0 24px; }}
#file .lines {{ position: absolute; left: 54px; right: 54px; top: 74px; }}
#file .ln {{ height: 16px; border-radius: 8px; margin-bottom: 18px; background: {c.rgba(c.WHITE, 0.22)}; }}
#file .lbl {{ position: absolute; left: 0; right: 0; bottom: 120px; text-align: center; font-size: 92px;
  font-weight: 900; letter-spacing: -0.02em; color: {c.WHITE}; }}
#file .sub {{ position: absolute; left: 0; right: 0; bottom: 70px; text-align: center; font-size: 34px;
  font-weight: 700; color: {pal['acc']}; }}
"""


def screen_html(name, start, dur):
    if not name:
        return '<div class="glass"></div>'
    v = lambda vid: (f'<video id="{vid}" src="{name}" data-start="0" data-duration="{dur:.3f}" '  # noqa: E731
                     f'data-media-start="{float(start):.3f}" data-track-index="{1 if vid == "sv" else 2}" '
                     f'muted playsinline></video>')
    return (v("sv") + '<div class="mini"><div class="mscr">' + v("sv2") + '</div><div class="mbase"></div></div>'
            '<div class="glass"></div>')


def build(slots, theme, kind=None, layout="full"):
    s = c.merge_slots(SLOTS, slots)
    if s["mode"] not in MODES:
        raise ValueError(f"mode {s['mode']!r}: один из {', '.join(MODES)}")
    pal = c.palette(theme, kind or DEFAULT_KIND)
    dur = max(2.4, float(s["duration"]))
    files, name = [], ""
    if s["screen"]:
        p = Path(str(s["screen"])).expanduser()
        if not p.exists():
            raise ValueError(f"видео для экрана не найдено: {s['screen']}")
        if p.suffix.lower() not in VIDEO_EXT:
            raise ValueError(f"screen: видео MP4/MOV/WEBM, а не {p.suffix}")
        name = f"screen{p.suffix.lower()}"
        files.append((str(p), name))
    h = c.headline(s["headline"], s["context"], prefix="h", top=300) if s["headline"] else None
    js, times = (c.headline_js(h, 0.1, 0.8) if h else ([], []))
    to_file = s["mode"] == "to_file"

    lid = (f'<div class="lid" id="lid"><div class="face front"><div class="screen">'
           f'{screen_html(name, s["screen_start"], dur)}</div></div><div class="face back"></div></div>')
    deck = '<div class="deck"><div class="keys"></div><div class="pad"></div></div>'
    rings = "".join(f'<div class="ring" id="rg{i}"></div>' for i in range(3))
    fcard = ""
    if to_file:
        sub = f'<div class="sub">{c.esc(s["sublabel"])}</div>' if s["sublabel"] else ""
        fcard = (f'<div id="file"><div class="card"><div class="lines">'
                 + "".join(f'<div class="ln" style="width:{w}%"></div>' for w in (70, 92, 58))
                 + f'</div><div class="lbl">{c.esc(s["label"])}</div>{sub}</div><div class="fold"></div></div>')
    content = ((h["html"] if h else "") + f'<div class="stage" id="stage"><div id="shade"></div>{rings}'
               f'<div id="drop"><div id="lap">{deck}{lid}</div></div>{fcard}</div>')
    deco, deco_js = c.decor(pal, layout, s["tags"], dur)
    box = BOX if h else (470, 1440)   # без заголовка половина кадра — под сам ноутбук, он крупнее
    body, bg, size = c.compose(pal, layout, deco, content, dur, box)

    view = 'rotationX: -24, rotationY: -20'
    if not to_file:
        js += [
            f'tl.fromTo("#drop", {{ y: -1500, rotationZ: -8 }}, {{ y: 0, rotationZ: 0, duration: 0.6, '
            f'ease: "bounce.out" }}, 0.05);',
            f'tl.fromTo("#lap", {{ {view}, scale: 0.92 }}, {{ rotationX: -24, rotationY: -14, scale: 1, '
            f'duration: 0.6, ease: "power2.out" }}, 0.05);',
            'tl.fromTo("#shade", { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.5 }, 0.2);',
            'tl.fromTo("#lid", { rotationX: -90 }, { rotationX: 10, duration: 0.6, ease: "back.out(1.5)" }, 0.6);',
            f'tl.fromTo("#lap", {{ rotationY: -14 }}, {{ rotationY: -4, duration: {c.fmt(dur - 1.2)}, '
            f'ease: "sine.inOut", immediateRender: false }}, 1.2);',
        ]
        js += [f'tl.fromTo("#rg{i}", {{ scale: 0.5, opacity: 0.8 }}, {{ scale: 1.7, opacity: 0, duration: 1.1, '
               f'ease: "power2.out" }}, {c.fmt(0.62 + i * 0.18)});' for i in range(3)]
        events = [c.ev(0.05, "ноутбук падает сверху"), c.ev(0.6, "ноутбук приземлился, крышка открывается"),
                  c.ev(1.2, "экран открыт: на нём видео, в углу ноутбук поменьше с тем же видео"),
                  c.ev(0.62, "кольца от удара")]
        describes = "3D-ноутбук падает сверху и раскрывается; на экране видео, в углу — ноутбук в ноутбуке"
        preview = min(2.0, dur - 0.1)
    else:
        js += [
            f'tl.fromTo("#lap", {{ {view}, scale: 0.6, opacity: 0, y: -120 }}, {{ rotationX: -24, rotationY: -8, '
            f'scale: 1, opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }}, 0.0);',
            'tl.set("#lid", { rotationX: 10 }, 0);',
            'tl.fromTo("#shade", { opacity: 0 }, { opacity: 1, duration: 0.3 }, 0.0);',
            'tl.fromTo("#lid", { rotationX: 10 }, { rotationX: -90, duration: 0.4, ease: "power3.in", '
            'immediateRender: false }, 0.55);',
            'tl.fromTo("#lap", { scale: 1, rotationZ: 0, opacity: 1 }, { scale: 0.15, rotationZ: 30, opacity: 0, '
            'duration: 0.35, ease: "power3.in", immediateRender: false }, 0.98);',
            'tl.fromTo("#shade", { opacity: 1 }, { opacity: 0, duration: 0.3, immediateRender: false }, 0.98);',
            'tl.fromTo("#file", { opacity: 0, scale: 0.2, rotationY: 200 }, { opacity: 1, scale: 1, rotationY: 0, '
            'duration: 0.7, ease: "back.out(1.5)" }, 1.2);',
            f'tl.fromTo("#file", {{ y: 0 }}, {{ y: -20, duration: {c.fmt(max(0.5, dur - 2.0))}, ease: "sine.inOut", '
            f'immediateRender: false }}, 1.9);',
        ]
        js += [f'tl.fromTo("#rg{i}", {{ scale: 0.5, opacity: 0.8 }}, {{ scale: 1.8, opacity: 0, duration: 1.1, '
               f'ease: "power2.out" }}, {c.fmt(1.35 + i * 0.18)});' for i in range(3)]
        events = [c.ev(0.0, "открытый ноутбук появляется"), c.ev(0.55, "крышка захлопывается"),
                  c.ev(0.98, "ноутбук сжимается и исчезает"),
                  c.ev(1.2, f"появляется светящаяся карточка-файл «{s['label']}»"),
                  c.ev(1.9, f"карточка-файл «{s['label']}» видна целиком"), c.ev(1.35, "кольца от карточки")]
        describes = f"3D-ноутбук захлопывается и превращается в светящийся файл «{s['label']}»"
        preview = min(2.3, dur - 0.1)
    js += deco_js
    if h:
        events += c.headline_events(h, times)
    if files:
        events.append(c.ev(0.0, f"на экране видео {Path(files[0][0]).name} с {float(s['screen_start']):.1f} с"))
    return c.result(c.base_css(pal, layout) + css(pal), body, js, dur, events, pal, layout, bg, size, files,
                    BASE_TAGS + (["файл", "скилл"] if to_file else []), describes, preview_t=preview)
