"""Общее для шаблонов сцен: палитра из темы, фон, плавающие слова, заголовок по словам,
раскладки full/half/overlay. Только stdlib.

Шаблон — модуль с NAME, TITLE, DEFAULT_KIND, SLOTS и build(slots, theme, kind=None,
layout="full") → dict(css, body, js, duration, events, theme_kind, layout, bg, size,
files, tags, describes, preview_t). events — опись сцены для index.json.

Цвета и шрифты — только из темы автора (settings.py). Здесь нет ни одного цвета автора:
белый и чёрный — для смешивания, теней и бликов.
Анимация seek-safe (рендер перематывает покадрово): только transform/opacity/filter,
fromTo, селекторы по id, ни случайности, ни текущего времени.
"""
import html
from pathlib import Path

W, H, HALF_H = 1080, 1920, 960
KINDS = ("dark", "light")
LAYOUTS = ("full", "half", "overlay")
IMAGE_EXT = {".svg", ".png", ".jpg", ".jpeg", ".webp"}
MARKS = {"*": "acc", "_": "sec"}       # *слово* — акцент, _слово_ — второй цвет
WHITE, BLACK = "#FFFFFF", "#000000"

# Места фоновых слов: (сторона, отступ, top) — по краям, мимо заголовка и центра.
TAG_SPOTS = (("left", 90, 160), ("right", 110, 640), ("left", 130, 1580), ("right", 150, 1700))


# ── цвета ────────────────────────────────────────────────────────────────────

def _rgb(hex_color):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, w):
    """Смесь двух hex-цветов: w — доля b (0 → a, 1 → b)."""
    ra, rb = _rgb(a), _rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * w):02X}" for x, y in zip(ra, rb))


def rgba(hex_color, alpha):
    r, g, b = _rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def palette(theme, kind):
    """Цвета сцены из темы: фон, текст, акценты под тёмный или светлый фон."""
    dark = kind == "dark"
    a = theme["accent"]
    bg0, bg1 = theme["bg_dark"] if dark else theme["bg_light"]
    return {
        "kind": kind, "dark": dark, "bg0": bg0, "bg1": bg1,
        "text": WHITE if dark else theme["text_dark"],
        "ink": theme["text_dark"],                 # текст на белых плашках
        "muted": theme["muted"],
        "acc": a["solid"] if dark else a["on_light"],
        "sec": theme["secondary"],
        "ok": theme["success"],
        "deep": theme["bg_dark"][0], "deep_end": theme["bg_dark"][1],
    }


def color_key(value, pal):
    """Слот цвета: secondary | accent | #hex."""
    if isinstance(value, str) and value.startswith("#"):
        return value
    return {"secondary": pal["sec"], "accent": pal["acc"]}.get(value, pal["sec"])


def background(pal):
    if pal["dark"]:
        return (f"radial-gradient(ellipse 80% 55% at 50% 52%, {mix(pal['bg0'], WHITE, 0.07)} 0%, "
                f"{mix(pal['bg0'], pal['bg1'], 0.35)} 38%, {pal['bg1']} 85%)")
    return (f"radial-gradient(ellipse 90% 70% at 50% 40%, {pal['bg0']} 0%, "
            f"{mix(pal['bg0'], pal['bg1'], 0.5)} 55%, {pal['bg1']} 100%)")


# ── мелочи ───────────────────────────────────────────────────────────────────

def esc(text):
    return html.escape(str(text), quote=True)


def fmt(t):
    return f"{t:.3f}".rstrip("0").rstrip(".") or "0"


def ev(t, what):
    return {"t": round(t, 2), "what": what}


def finish_events(events, dur):
    out = [dict(e, t=round(min(max(e["t"], 0.0), dur), 2)) for e in events]
    return sorted(out, key=lambda e: e["t"])


def merge_slots(slots_spec, slots):
    """Дефолты шаблона + переданные слоты. Лишний ключ — ошибка (опечатка в слоте)."""
    slots = dict(slots or {})
    extra = sorted(set(slots) - set(slots_spec))
    if extra:
        raise ValueError(f"неизвестные слоты: {', '.join(extra)}; есть: {', '.join(slots_spec)}")
    out = {k: v["default"] for k, v in slots_spec.items()}
    out.update({k: v for k, v in slots.items() if v is not None})
    return out


def is_image(value):
    return isinstance(value, str) and Path(value).suffix.lower() in IMAGE_EXT


def icon_html(value, cls, name="icon"):
    """Иконка из слота: эмодзи/символ → span; путь к SVG/PNG → img + файл в проект.
    → (html, files [(src, имя)])."""
    if is_image(value):
        p = Path(value).expanduser()
        if not p.exists():
            raise ValueError(f"иконка не найдена: {value}")
        fname = f"{name}{p.suffix.lower()}"
        return f'<img class="{cls}" src="{fname}" alt="" />', [(str(p), fname)]
    return f'<span class="{cls}">{esc(value)}</span>', []


def fit_px(text, base, fits, floor):
    """Кегль: base, пока текст не длиннее fits символов; дальше уменьшается к floor."""
    n = len(text)
    if n <= fits:
        return base
    return max(floor, int(base * (fits / n) ** 0.5))


# ── заголовок по словам ──────────────────────────────────────────────────────

def parse_headline(text):
    """«Свой _сервис,_ который работает *сам*» → строки → слова → куски [(текст, класс)].
    *…* — акцент, _…_ — второй цвет (можно на несколько слов), \\n — перенос строки."""
    lines = []
    for raw in str(text).split("\n"):
        chars, style = [], None
        for ch in raw:
            if ch in MARKS:
                style = None if style == MARKS[ch] else MARKS[ch]
                continue
            chars.append((ch, style))
        words, cur = [], []
        for ch, st in chars + [(" ", None)]:
            if ch.isspace():
                if cur:
                    words.append(_runs(cur))
                    cur = []
            else:
                cur.append((ch, st))
        if words:
            lines.append(words)
    return lines


def _runs(chars):
    runs = []
    for ch, st in chars:
        if runs and runs[-1][1] == st:
            runs[-1] = (runs[-1][0] + ch, st)
        else:
            runs.append((ch, st))
    return runs


def plain(lines):
    return " ".join("".join(t for t, _ in w) for line in lines for w in line)


def word_times(n, start, span, step_min=0.12, step_max=0.28):
    """Моменты появления n слов: равный шаг, вписанный в span, но не быстрее step_min
    и не медленнее step_max."""
    if n <= 0:
        return []
    step = min(step_max, max(step_min, span / max(1, n - 1))) if n > 1 else 0
    return [round(start + i * step, 3) for i in range(n)]


def headline(text, context="", prefix="h", top=250, base_px=82, ctx_id=None):
    """HTML заголовка (+ строка-контекст) и список слов. → dict(html, ids, words, styles,
    size, plain). ids — по одному на слово, для поштучного появления."""
    lines = parse_headline(text)
    words_plain = plain(lines)
    size = fit_px(words_plain, base_px, 36, 54)
    ids, words, styles, rows = [], [], [], []
    for li, line in enumerate(lines):
        spans = []
        for w in line:
            wid = f"{prefix}w{len(ids)}"
            inner = "".join(f'<span class="{st}">{esc(t)}</span>' if st else esc(t)
                            for t, st in w)
            spans.append(f'<span class="w" id="{wid}">{inner}</span>')
            ids.append(wid)
            words.append("".join(t for t, _ in w))
            styles.append(next((st for _, st in w if st), None))
        gap = ' style="margin-top:10px"' if li else ""
        rows.append(f'<div class="ln" style="font-size:{size}px"{gap}>{" ".join(spans)}</div>')
    ctx = ""
    if context:
        ctx = f'<div class="ctx" id="{ctx_id or prefix + "ctx"}">{esc(context)}</div>'
    body = f'<div class="head" id="{prefix}head" style="top:{top}px">{ctx}{"".join(rows)}</div>'
    return {"html": body, "ids": ids, "words": words, "styles": styles, "size": size,
            "plain": words_plain, "ctx_id": (ctx_id or prefix + "ctx") if context else None}


def headline_js(h, start, span):
    """Слова влетают по одному (blur → резкость). → (js-строки, времена слов)."""
    times = word_times(len(h["ids"]), start, span)
    js = [f'blurIn("#{wid}", {fmt(t)});' for wid, t in zip(h["ids"], times)]
    return js, times


def headline_events(h, times, label="заголовок"):
    """События заголовка: начало, каждое акцентное слово, заголовок целиком."""
    if not times:
        return []
    out = [ev(times[0], f"{label}: слова по одному")]
    for w, st, t in zip(h["words"], h["styles"], times):
        if st:
            out.append(ev(t, f"акцент «{w.strip(',.!?:;')}»"))
    out.append(ev(times[-1] + 0.32, f"{label} целиком: «{h['plain']}»"))
    return out


# ── фон, теги, раскладка ─────────────────────────────────────────────────────

def tags_html(words, pal):
    out = []
    for i, (word, (side, off, top)) in enumerate(zip(words or [], TAG_SPOTS)):
        out.append(f'<div class="tag" id="tg{i}" style="{side}:{off}px; top:{top}px">'
                   f'{esc(word)}</div>')
    return "".join(out)


def tags_js(words, dur):
    return [f'tl.fromTo("#tg{i}", {{ y: 0 }}, {{ y: {-60 if i % 2 else 60}, '
            f'duration: {fmt(dur)}, ease: "none" }}, 0);'
            for i in range(min(len(words or []), len(TAG_SPOTS)))]


def blobs_html(pal, spots):
    """Мягкие цветные пятна светлого фона. spots: [(сторона, отступ, top, размер, ключ
    палитры)]."""
    return "".join(f'<div class="blob" style="{side}:{off}px; top:{top}px; width:{size}px; '
                   f'height:{size}px; background:{mix(pal[key], WHITE, 0.6)}"></div>'
                   for side, off, top, size, key in spots)


def decor(pal, layout, tags, dur, blob_spots=()):
    """Фоновые слова (+ пятна на светлом). В overlay декора нет — и его анимации тоже,
    иначе GSAP ищет несуществующие id. → (html, js-строки)."""
    if layout == "overlay":
        return "", []
    blobs = "" if pal["dark"] else blobs_html(pal, blob_spots)
    return blobs + tags_html(tags, pal), tags_js(tags, dur)


def base_css(pal, layout):
    shadow = "text-shadow: 0 4px 28px rgba(0, 0, 0, 0.45);" if layout == "overlay" else ""
    return f"""
#scene {{ position: absolute; inset: 0; overflow: hidden; color: {pal['text']}; }}
.bgfill {{ position: absolute; inset: 0; background: {background(pal)}; }}
#content {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; }}
.blob {{ position: absolute; border-radius: 50%; filter: blur(90px); opacity: 0.55; }}
.tag {{ position: absolute; font-weight: 700; font-size: 34px; filter: blur(3px); opacity: 0.18;
  letter-spacing: 0.02em; color: {pal['sec']}; white-space: nowrap; }}
.head {{ position: absolute; left: 70px; right: 70px; text-align: center; {shadow} }}
.ctx {{ font-size: 34px; font-weight: 600; opacity: 0; margin-bottom: 14px; color: {pal['muted']}; }}
.ln {{ font-weight: 800; line-height: 1.08; letter-spacing: -0.02em; }}
.w {{ display: inline-block; opacity: 0; }}
.acc {{ color: {pal['acc']}; }}
.sec {{ color: {pal['sec']}; }}
"""


JS_HELPERS = """const blurIn = (sel, at, d = 0.32) => tl.fromTo(sel,
  { opacity: 0, y: 26, filter: "blur(14px)" },
  { opacity: 1, y: 0, filter: "blur(0px)", duration: d, ease: "power3.out" }, at);
const fadeIn = (sel, at, d = 0.25) => tl.fromTo(sel, { opacity: 0 }, { opacity: 1, duration: d }, at);
const blurOut = (sel, at, d = 0.15) => tl.fromTo(sel,
  { opacity: 1, filter: "blur(0px)" },
  { opacity: 0, filter: "blur(10px)", duration: d, immediateRender: false }, at);"""


def compose(pal, layout, decor, content, dur, box):
    """Сцена целиком под раскладку. full — 1080×1920 с фоном; half — 1080×960, содержимое
    ужато в верхнюю половину (box — его вертикальные границы в координатах full);
    overlay — без фона и декора, прозрачная страница. → (body, bg, size)."""
    if layout not in LAYOUTS:
        raise ValueError(f"раскладка {layout!r}: одна из {', '.join(LAYOUTS)}")
    h = HALF_H if layout == "half" else H
    style = ""
    if layout == "half":
        y0, y1 = box
        k = min(1.0, (HALF_H - 60) / (y1 - y0))
        style = (f' style="transform-origin: 50% 0; '
                 f'transform: translateY({30 - y0 * k:.1f}px) scale({k:.3f})"')
    fill, deco = ("", "") if layout == "overlay" else ('<div class="bgfill"></div>', decor)
    inner = f'{fill}<div id="content"{style}>{deco}{content}</div>'
    # #scene — простой контейнер, не клип таймлайна: вложенный клип линтер HyperFrames
    # просит выносить в под-композицию, а сцене таймлайн по клипам не нужен.
    body = f'<div id="scene" class="{pal["kind"]}">{inner}</div>'
    bg = "transparent" if layout == "overlay" else pal["bg1"]
    return body, bg, [W, h]


def result(css, body, js, dur, events, pal, layout, bg, size, files, tags, describes, preview_t):
    return {"css": css, "body": body, "js": "\n".join([JS_HELPERS] + js), "duration": round(dur, 2),
            "events": finish_events(events, dur), "theme_kind": pal["kind"], "layout": layout,
            "bg": bg, "size": size, "files": files, "tags": tags, "describes": describes,
            "preview_t": round(min(preview_t, dur - 0.05), 2)}
