"""Субтитры по словам для переднего слоя. Только stdlib.

Два стиля (настройка «субтитры.стиль», переопределяется в плане на один ролик):
  • lines («строки») — страницы по две строки ≤ 21 символа на тёмной плашке, текущее
    слово подсвечивается акцентом (караоке);
  • word («по_слову») — одно крупное слово по центру; короткие служебные слова клеятся
    к следующему; акцентом красятся только ударные слова; под словом — размытая тёмная
    подложка шире слова (ореол по буквам автор не замечает, а пятно читается).
Появление слова: pop (с 80% за 0,18 с, лёгкая пружина) / none / wave (буквы волной).

Субтитры не показываются там, где тот же текст стоит крупно за головой (hidden), и
поднимаются на стык, когда верх кадра занят б-роллом half (half_windows).
"""
import html

from words import norm

MAXC = 21          # символов в строке стиля lines
PAUSE = 0.45       # пауза, после которой страница кончается
GLUE = {"в", "и", "а", "на", "по", "не", "под", "о", "у", "к", "с", "из", "за", "эту", "все",
        "как", "ты", "он", "она"}


def visible_segments(words, hidden=()):
    """Слова, не попавшие в скрытые окна, — непрерывными кусками."""
    segs, cur = [], []
    for w in words:
        if any(a <= w["start"] < b for a, b in hidden):
            if cur:
                segs.append(cur)
                cur = []
        else:
            cur.append(w)
    if cur:
        segs.append(cur)
    return segs


def _cut_at_edges(a, b, edges):
    for e in edges:
        if a < e < b:
            b = e - 0.02
    return b


def line_pages(segs, dur, edges=(), maxc=MAXC, pause=PAUSE):
    """Страницы по ≤ 2 строки. Страница кончается на точке, паузе > pause или конце куска."""
    pages = []
    for seg in segs:
        pg, line = [], []
        for i, w in enumerate(seg):
            cand = " ".join(x["text"] for x in line + [w])
            if line and len(cand) > maxc:
                pg.append(line)
                line = []
                if len(pg) == 2:
                    pages.append({"lines": pg})
                    pg = []
            line.append(w)
            nxt = seg[i + 1] if i + 1 < len(seg) else None
            if w["text"][-1:] in ".?!" or nxt is None or nxt["start"] - w["end"] > pause:
                if line:
                    pg.append(line)
                    line = []
                if pg:
                    pages.append({"lines": pg})
                    pg = []
        if pages:
            pages[-1]["last_in_seg"] = True
    for pg in pages:
        pg["ws"] = [w for ln in pg["lines"] for w in ln]
        pg["a"] = max(0.0, round(pg["ws"][0]["start"] - 0.06, 3))
    for i, pg in enumerate(pages):
        nxt = pages[i + 1] if i + 1 < len(pages) else None
        if pg.get("last_in_seg") or nxt is None:
            pg["b"] = round(_cut_at_edges(pg["a"], min(pg["ws"][-1]["end"] + 0.35, dur), edges), 3)
        else:
            pg["b"] = nxt["a"]
    return pages


def word_beats(segs, dur, edges=(), glue=GLUE):
    """Удары стиля word: слово или «служебное + слово». Держится до следующего удара,
    а после паузы > 0,5 с или в конце куска — 0,3 с после слова."""
    beats = []
    for seg in segs:
        cur = []
        for i, w in enumerate(seg):
            cur.append(w)
            nxt = seg[i + 1] if i + 1 < len(seg) else None
            sticky = (norm(w["text"]) in glue and nxt is not None
                      and nxt["start"] - w["end"] < 0.3 and len(cur) < 2)
            if not sticky:
                beats.append({"ws": cur, "lines": [cur], "last_in_seg": nxt is None})
                cur = []
        if cur:
            beats.append({"ws": cur, "lines": [cur], "last_in_seg": True})
    for bt in beats:
        bt["a"] = round(max(0.0, bt["ws"][0]["start"] - 0.04), 3)
    for i, bt in enumerate(beats):
        nxt = beats[i + 1] if i + 1 < len(beats) else None
        end = bt["ws"][-1]["end"]
        if nxt is None or bt["last_in_seg"] or nxt["a"] - end > 0.5:
            b = _cut_at_edges(bt["a"], min(dur, end + 0.3), edges)
        else:
            b = nxt["a"]
        bt["b"] = round(b, 3)
    return beats


def font_px(text, word_px):
    """Верхняя граница — word_px для слов до ~9 букв; длинные уменьшаются пропорционально."""
    n = max(1, len(text))
    return int(min(word_px, word_px * 9.4 / max(n, 9.4)))


def in_half(a, b, half_windows):
    return any(a < hb - 0.05 and b > ha + 0.05 for ha, hb in half_windows)


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:.2f})"


def render_lines(pages, opts, theme, half_windows=(), track=3):
    """→ (css, body[], js[])"""
    acc = theme["accent"]["solid"]
    css = f"""
.rail {{ position: absolute; left: 70px; right: 70px; top: {opts['top_px']}px; text-align: center; opacity: 0; }}
.rail .ln {{ display: block; margin-bottom: 10px; }}
.rail .box {{ display: inline; font-weight: 700; font-size: {opts['line_px']}px; line-height: 1.32; padding: 4px 18px;
  background: {_rgba(opts['backing']['color'], 0.62)}; border-radius: 14px;
  -webkit-box-decoration-break: clone; box-decoration-break: clone; }}
.rail .w {{ color: #fff; }}
"""
    body, js = [], []
    for i, pg in enumerate(pages):
        pid = f"r{i}"
        lines = "".join('<div class="ln"><span class="box">'
                        + " ".join(f'<span class="w">{html.escape(w["text"])}</span>' for w in ln)
                        + "</span></div>" for ln in pg["lines"])
        style = f' style="top:{opts["top_half_px"]}px"' if in_half(pg["a"], pg["b"], half_windows) else ""
        body.append(f'<div id="{pid}" class="clip" data-start="{pg["a"]:.3f}" '
                    f'data-duration="{pg["b"] - pg["a"]:.3f}" data-track-index="{track}">'
                    f'<div class="rail"{style}>{lines}</div></div>')
        js.append(f'tl.fromTo("#{pid} .rail", {{opacity: 0, y: 10}}, {{opacity: 1, y: 0, duration: 0.1, '
                  f'ease: "power2.out"}}, {pg["a"]:.3f});')
        for k, w in enumerate(pg["ws"]):
            js.append(f'tl.set(document.querySelectorAll("#{pid} .w")[{k}], {{color: "{acc}"}}, {w["start"]:.3f});')
            off = pg["ws"][k + 1]["start"] if k + 1 < len(pg["ws"]) else pg["b"]
            js.append(f'tl.set(document.querySelectorAll("#{pid} .w")[{k}], {{color: "#FFFFFF"}}, '
                      f'{min(off, w["end"] + 0.25):.3f});')
    return css, body, js


def accent_style(theme):
    a = theme["accent"]
    if a.get("gradient"):  # градиент: тень фильтром, иначе text-shadow ложится поверх заливки
        return (f' style="background:linear-gradient(90deg,{",".join(a["gradient"])}); '
                f'-webkit-background-clip:text; background-clip:text; color:transparent; '
                f'text-shadow:none; filter:saturate(1.15)"')
    return f' style="color:{a["solid"]}"'


def render_words(beats, opts, theme, accent_words=(), half_windows=(), track=3):
    """→ (css, body[], js[])"""
    bk = opts["backing"]
    o = bk["opacity"]
    stops = (f"{_rgba(bk['color'], o + 0.02)} 0%, {_rgba(bk['color'], o - 0.05)} 62%, "
             f"{_rgba(bk['color'], o * 0.42)} 86%, {_rgba(bk['color'], 0)} 100%")
    css = f"""
.wcap {{ position: absolute; left: 40px; right: 40px; top: {opts['top_px']}px; text-align: center; }}
.wd {{ position: relative; isolation: isolate; display: inline-block; font-weight: 900; letter-spacing: -0.02em;
  line-height: 1.05; color: #fff; text-shadow: 0 0 4px {_rgba(bk['color'], 0.35)}; }}
.wd::before {{ content: ""; position: absolute; inset: -{bk['tall_em']}em -{bk['wide_em']}em; z-index: -1;
  border-radius: 999px; background: radial-gradient(ellipse closest-side at center, {stops});
  filter: blur({bk['blur_px']}px); }}
.lm {{ display: inline-block; overflow: hidden; vertical-align: bottom; padding: 0 0.01em 0.08em; }}
.lt {{ display: inline-block; }}
"""
    accents = {norm(x) for x in accent_words}
    acc_attr = accent_style(theme)
    body, js = [], []
    for i, bt in enumerate(beats):
        bid = f"r{i}"
        text = " ".join(w["text"] for w in bt["ws"]).rstrip(",.")
        fs = font_px(text, opts["word_px"])
        parts = []
        for j, w in enumerate(bt["ws"]):  # акцентом красится только ударное слово, не связка
            t = w["text"].rstrip(",.") if j == len(bt["ws"]) - 1 else w["text"]
            attr = acc_attr if norm(w["text"]) in accents else ""
            parts.append(f"<span{attr}>" + "".join(
                f'<span class="lm"><span class="lt">{html.escape(c)}</span></span>' for c in t) + "</span>")
        top = opts["top_half_px"] + 20 if in_half(bt["a"], bt["b"], half_windows) else opts["top_px"]
        body.append(f'<div id="{bid}" class="clip" data-start="{bt["a"]:.3f}" '
                    f'data-duration="{bt["b"] - bt["a"]:.3f}" data-track-index="{track}">'
                    f'<div class="wcap" style="top:{top}px"><span class="wd" style="font-size:{fs}px">'
                    f'{" ".join(parts)}</span></div></div>')
        if opts["anim"] == "wave":
            st = min(0.022, 0.16 / max(1, len(text)))
            js.append(f'tl.fromTo("#{bid} .lt", {{yPercent: 115, rotation: 7, opacity: 0}}, {{yPercent: 0, '
                      f'rotation: 0, opacity: 1, duration: 0.26, ease: "back.out(2.2)", stagger: {st:.4f}}}, '
                      f'{bt["a"]:.3f});')
            js.append(f'tl.fromTo("#{bid} .wd", {{scale: 0.88}}, {{scale: 1, duration: 0.32, '
                      f'ease: "power3.out"}}, {bt["a"]:.3f});')
        elif opts["anim"] == "pop":
            js.append(f'tl.fromTo("#{bid} .wd", {{scale: {opts["pop_from"]}, opacity: 0}}, {{scale: 1, '
                      f'opacity: 1, duration: 0.18, ease: "back.out(1.5)"}}, {bt["a"]:.3f});')
    return css, body, js


def build(words, dur, opts, theme, hidden=(), edges=(), half_windows=(), accent_words=()):
    """Субтитры целиком → (css, body[], js[], units) — units для отчёта."""
    segs = visible_segments(words, hidden)
    if opts["style"] == "word":
        units = word_beats(segs, dur, edges)
        css, body, js = render_words(units, opts, theme, accent_words, half_windows)
    else:
        units = line_pages(segs, dur, edges)
        css, body, js = render_lines(units, opts, theme, half_windows)
    return css, body, js, units


def summary(units):
    return [f'{u["a"]:6.2f}–{u["b"]:6.2f}  ' + " / ".join(" ".join(w["text"] for w in ln) for ln in u["lines"])
            for u in units]

