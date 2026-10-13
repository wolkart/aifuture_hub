"""Табло: перелистывание числа «3 → 0» на ячейке-табло + всплывающие строки
«✓ … 09:00». Родная тема — светлая.

Перелистывание seek-safe: все значения лежат в ячейке стопкой, видна одна; смена —
поворот и прозрачность, без подмены текста (tl.call с подменой ломает перемотку рендера).
Когда брать: «было N — стало M» (часы, шаги, деньги, ошибки) и расписание результата.
"""
import _common as c

NAME = "flip_board"
TITLE = "Табло"
DEFAULT_KIND = "light"
BOX = (180, 1700)
BASE_TAGS = ["табло", "число", "счёт", "время", "расписание", "заголовок"]
SLOTS = {
    "context": {"about": "строка-контекст над заголовком, можно пусто",
                "default": "Сколько времени уходит на рутину"},
    "headline": {"about": "заголовок по словам (появляется после перелистывания); *слово* — акцент",
                 "default": "*0* часов в день"},
    "from": {"about": "число на табло в начале", "default": 3},
    "to": {"about": "число на табло в конце", "default": 0},
    "unit": {"about": "вторая ячейка табло (единица), можно пусто", "default": "Ч"},
    "subline": {"about": "подпись под табло, можно пусто", "default": "на рутину в день"},
    "notes": {"about": "0–4 строки [текст, время] — всплывают с галочкой",
              "default": [["Готово", "09:00"], ["Готово", "14:00"], ["Готово", "19:00"]]},
    "tags": {"about": "до 4 фоновых слов", "default": []},
}
MAX_FLIPS = 10
FLIP_AT, FLIP_STEP = 0.7, 0.3
BLOBS = [("left", -160, 900, 560, "sec"), ("right", -120, 240, 480, "acc")]


def steps(a, b, max_steps=MAX_FLIPS):
    """Значения табло от a до b: по одному, а при большой разнице — не больше max_steps
    перелистываний. Не числа — одно перелистывание a → b."""
    try:
        a, b = int(a), int(b)
    except (TypeError, ValueError):
        return [str(a), str(b)] if str(a) != str(b) else [str(a)]
    n = min(abs(b - a), max_steps)
    vals = [str(round(a + (b - a) * i / n)) for i in range(n + 1)] if n else [str(a)]
    return [v for i, v in enumerate(vals) if i == 0 or v != vals[i - 1]]


def unit_cell(unit):
    fs = 230 if len(unit) <= 1 else (150 if len(unit) == 2 else 110)
    return fs, max(190, int(0.6 * fs * len(unit)) + 70)


def css(pal):
    deep = pal["deep"]
    return f"""
#flip {{ position: absolute; left: 0; right: 0; top: 720px; display: flex; justify-content: center;
  gap: 22px; perspective: 1200px; }}
.cell {{ position: relative; height: 290px; border-radius: 28px; opacity: 0;
  background: linear-gradient(180deg, {c.mix(deep, c.WHITE, 0.06)} 0%, {c.mix(deep, c.BLACK, 0.15)} 50%,
  {c.mix(deep, c.BLACK, 0.3)} 50%, {deep} 100%);
  box-shadow: 0 24px 60px {c.rgba(deep, 0.35)}; font-family: var(--display); font-weight: 700;
  font-size: 230px; color: {c.WHITE}; line-height: 290px; text-align: center; }}
.cell .d {{ position: absolute; inset: 0; backface-visibility: hidden; }}
.cell::after {{ content: ""; position: absolute; left: 0; right: 0; top: 144px; height: 3px;
  background: rgba(0, 0, 0, 0.45); }}
#sub {{ position: absolute; left: 0; right: 0; top: 1050px; text-align: center; font-size: 46px;
  font-weight: 800; color: {pal['text']}; opacity: 0; }}
.note {{ position: absolute; left: 160px; right: 160px; padding: 26px 34px; border-radius: 28px;
  background: {c.WHITE}; box-shadow: 0 18px 50px {c.rgba(pal['ink'], 0.16)}; display: flex;
  align-items: center; gap: 22px; font-size: 36px; font-weight: 700; color: {pal['ink']}; opacity: 0; }}
.ok {{ width: 54px; height: 54px; border-radius: 50%; background: {pal['ok']}; color: {c.WHITE};
  display: flex; align-items: center; justify-content: center; font-size: 34px; flex: none; }}
.note .t {{ margin-left: auto; color: {pal['muted']}; font-family: Menlo, Consolas, monospace;
  font-size: 32px; }}
"""


def build(slots, theme, kind=None, layout="full"):
    s = c.merge_slots(SLOTS, slots)
    pal = c.palette(theme, kind or DEFAULT_KIND)
    vals = steps(s["from"], s["to"])
    unit = str(s["unit"] or "")
    notes = [list(n) + [""] * (2 - len(n)) for n in (s["notes"] or [])][:4]

    digits = max(len(v) for v in vals)
    hidden = ' style="opacity:0"'      # видно только первое значение стопки
    layers = "".join(f'<div class="d" id="d{i}"{hidden if i else ""}>{c.esc(v)}</div>'
                     for i, v in enumerate(vals))
    cells = f'<div class="cell" id="c1" style="width:{110 + 100 * digits}px">{layers}</div>'
    if unit:
        fs, width = unit_cell(unit)
        cells += (f'<div class="cell" id="c2" style="width:{width}px; font-size:{fs}px">'
                  f'<div class="d">{c.esc(unit)}</div></div>')
    flips = [FLIP_AT + i * FLIP_STEP for i in range(len(vals) - 1)]
    flips_end = (flips[-1] + 0.24) if flips else FLIP_AT

    h = c.headline(s["headline"], s["context"], prefix="h")
    js, times = c.headline_js(h, flips_end + 0.2, 0.45)
    words_end = times[-1] + 0.32 if times else flips_end
    note_ts = [words_end + 0.1 + i * 0.25 for i in range(len(notes))]
    dur = (note_ts[-1] + 0.8) if notes else words_end + 0.6
    exit_t = dur - 0.15

    note_html = "".join(f'<div class="note" id="n{i}" style="top:{1230 + i * 150}px">'
                        f'<div class="ok">✓</div>{c.esc(text)}<span class="t">{c.esc(tm)}</span></div>'
                        for i, (text, tm) in enumerate(notes))
    sub = f'<div id="sub">{c.esc(s["subline"])}</div>' if s["subline"] else ""
    content = h["html"] + f'<div id="flip">{cells}</div>' + sub + note_html
    deco, deco_js = c.decor(pal, layout, s["tags"], dur, BLOBS)
    body, bg, size = c.compose(pal, layout, deco, content, dur, BOX)

    if h["ctx_id"]:
        js.append(f'fadeIn("#{h["ctx_id"]}", 0.02);')
    for i, cid in enumerate(["#c1"] + (["#c2"] if unit else [])):
        js.append(f'tl.fromTo("{cid}", {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 0, duration: 0.35, '
                  f'ease: "back.out(1.6)" }}, {c.fmt(0.1 + i * 0.08)});')
    if sub:
        js.append('fadeIn("#sub", 0.5, 0.3);')
    for i, at in enumerate(flips):
        old, new = f"#d{i}", f"#d{i + 1}"
        js += [
            f'tl.fromTo("{old}", {{ rotationX: 0 }}, {{ rotationX: -90, transformPerspective: 800, '
            f'duration: 0.11, ease: "power2.in", immediateRender: false }}, {c.fmt(at)});',
            f'tl.set("{old}", {{ opacity: 0 }}, {c.fmt(at + 0.11)});',
            f'tl.fromTo("{new}", {{ rotationX: 90, opacity: 1 }}, {{ rotationX: 0, opacity: 1, '
            f'transformPerspective: 800, duration: 0.13, ease: "power2.out", immediateRender: false }}, '
            f'{c.fmt(at + 0.11)});',
        ]
    for i, t in enumerate(note_ts):
        js.append(f'tl.fromTo("#n{i}", {{ opacity: 0, x: 80 }}, {{ opacity: 1, x: 0, duration: 0.3, '
                  f'ease: "back.out(1.6)" }}, {c.fmt(t)});')
    js += deco_js
    outs = ["#hhead", "#flip"] + (["#sub"] if sub else []) + [f"#n{i}" for i in range(len(notes))]
    js += [f'blurOut("{sel}", {c.fmt(exit_t)});' for sel in outs]

    shown = f"{vals[0]}{' ' + unit if unit else ''}"
    events = [c.ev(0.1, f"табло «{shown}» появляется")]
    if s["context"]:
        events.append(c.ev(0.02, f"строка-контекст «{s['context']}»"))
    if sub:
        events.append(c.ev(0.5, f"подпись «{s['subline']}»"))
    events += [c.ev(at, f"перелистывание {vals[i]} → {vals[i + 1]}") for i, at in enumerate(flips)]
    if flips:
        events.append(c.ev(flips_end, f"на табло итог «{vals[-1]}{' ' + unit if unit else ''}»"))
    events += c.headline_events(h, times)
    events += [c.ev(t, f"строка «✓ {text} {tm}»".replace("  ", " ")) for t, (text, tm) in zip(note_ts, notes)]
    events.append(c.ev(exit_t, "уход: всё размывается"))
    describes = (f"табло: перелистывание {vals[0]} → {vals[-1]}{' ' + unit if unit else ''}"
                 + (f", строки с галочкой ({len(notes)})" if notes else "")
                 + f"; заголовок «{h['plain']}»")
    preview = (note_ts[-1] + 0.4) if notes else words_end + 0.1
    return c.result(c.base_css(pal, layout) + css(pal), body, js, dur, events, pal, layout, bg,
                    size, [], BASE_TAGS, describes, preview_t=min(preview, exit_t - 0.1))
