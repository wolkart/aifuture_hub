"""Субтитры по словам для переднего слоя. Только stdlib.

Три стиля (настройка «субтитры.стиль», переопределяется в плане на один ролик):
  • lines («строки») — страницы по две строки ≤ 21 символа на тёмной плашке, текущее
    слово подсвечивается акцентом (караоке);
  • word («по_слову») — одно крупное слово по центру; короткие служебные слова клеятся
    к следующему; акцентом красятся только ударные слова; под словом — размытая тёмная
    подложка шире слова (ореол по буквам автор не замечает, а пятно читается).
  • caps («капс») — 1–3 слова крупным шрифтом цифр капсом с тёмной обводкой; текущее
    слово загорается акцентом и чуть подрастает;
  • title («заголовок») — крупные слова в начале ролика: строки друг над другом, верхняя
    белая, нижнее слово крупнее градиентом акцента, без обводки (обводка читается колхозом),
    кегль нижнего слова ужат под ширину кадра — слово не уходит за край.
Появление слова: pop (с 80% за 0,18 с, лёгкая пружина) / none / wave (буквы волной).

Ключи по ходу ролика (plan.json → "captions_keys", время уже в секундах): с момента t
меняется стиль и/или высота. {"t", "style"?, "top"?, "slide"?, "px"?, "enter"?}: стиль без
высоты — высота по умолчанию для стиля; "slide" — текущая строка не прыгает, а переезжает на
новую высоту за slide секунд (под жест рукой); "px" — кегль капса (крупный заголовок в
начале ролика); "enter": left | right — первая строка нового стиля влетает с этого края
(смахнул рукой). Без ключей всё как раньше: один стиль на ролик.
Подмена текста (plan.json → "captions_replace"): {"Аху...": "АХУ***[[!]]"} — [[…]] красится
огненным цветом темы (danger).

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
    """На стык — только то, что окно half закрывает большей частью показа. Слово, которое лишь
    задевает край окна, остаётся на своей высоте: иначе оно висит на стыке поверх лица там, где
    кадр ещё полный (автор, 2026-10-18: «получается» на глазах за 0,06 с до вставки)."""
    d = max(1e-6, b - a)
    return any(min(b, hb) - max(a, ha) > 0.5 * d for ha, hb in half_windows)


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:.2f})"


STYLE_TOP = {"lines": 1385, "word": 1250, "caps": 1300, "title": 300}
TITLE_W = 960       # ширина, в которую ужимается нижнее слово заголовка
CAPS_WORDS, CAPS_MAXC = 3, 16


def fire(text):
    """Экранированный текст с [[…]] → кусок огненного цвета (class fire)."""
    out = html.escape(text)
    while "[[" in out and "]]" in out.split("[[", 1)[1]:
        pre, rest = out.split("[[", 1)
        mid, post = rest.split("]]", 1)
        out = f'{pre}<span class="fire">{mid}</span>{post}'
    return out


def insert_words(words, inserts):
    """Вставки в субтитры текста, которого не говорили («новый стиль» на взмахе):
    [{"t", "text", "dur"}] → слова, отсортированные по времени."""
    extra = [{"text": i["text"], "start": round(i["t"], 3), "end": round(i["t"] + float(i.get("dur", 0.5)), 3),
              "inserted": True} for i in inserts]
    return sorted(list(words) + extra, key=lambda w: w["start"])


def plain_text(text):
    return text.replace("[[", "").replace("]]", "")


def replace_words(words, mapping):
    """Подмена текста слов для субтитров (якоря плана считаются по исходным словам)."""
    if not mapping:
        return words
    return [dict(w, text=mapping.get(w["text"], w["text"])) for w in words]


def style_top(style, opts):
    """Высота стиля: из настроек, если это стиль настроек, иначе по умолчанию для стиля."""
    return opts["top_px"] if style == opts["style"] else STYLE_TOP[style]


def render_lines(pages, opts, theme, half_windows=(), track=3, prefix="r", top_of=None):
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
        pid = f"{prefix}{i}"
        lines = "".join('<div class="ln"><span class="box">'
                        + " ".join(f'<span class="w">{fire(w["text"])}</span>' for w in ln)
                        + "</span></div>" for ln in pg["lines"])
        if in_half(pg["a"], pg["b"], half_windows):
            style = f' style="top:{opts["top_half_px"]}px"'
        else:
            style = f' style="top:{top_of(pg)}px"' if top_of else ""
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


def render_words(beats, opts, theme, accent_words=(), half_windows=(), track=3, prefix="r", top_of=None):
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
        bid = f"{prefix}{i}"
        text = plain_text(" ".join(w["text"] for w in bt["ws"])).rstrip(",.")
        fs = font_px(text, opts["word_px"])
        parts = []
        for j, w in enumerate(bt["ws"]):  # акцентом красится только ударное слово, не связка
            t = plain_text(w["text"].rstrip(",.") if j == len(bt["ws"]) - 1 else w["text"])
            attr = acc_attr if norm(w["text"]) in accents else ""
            parts.append(f"<span{attr}>" + "".join(   # пробел внутри вставки — nbsp, иначе схлопнется
                f'<span class="lm"><span class="lt">{"&nbsp;" if c == " " else html.escape(c)}</span></span>'
                for c in t) + "</span>")
        top = (opts["top_half_px"] + 20 if in_half(bt["a"], bt["b"], half_windows)
               else (top_of(bt) if top_of else opts["top_px"]))
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


def caps_pages(segs, dur, edges=(), px=104):
    """Страницы капса: одна строка ≤ 3 слов и ≤ 16 символов (крупнее кегль — короче строка)."""
    pages = []
    maxc = max(8, int(CAPS_MAXC * 104 / max(60, px)))
    for pg in line_pages(segs, dur, edges, maxc=maxc):
        for ln in pg["lines"]:
            for k in range(0, len(ln), CAPS_WORDS):
                pages.append(ln[k:k + CAPS_WORDS])
    out = []
    for i, ws in enumerate(pages):
        out.append({"ws": ws, "lines": [ws], "a": max(0.0, round(ws[0]["start"] - 0.05, 3))})
    for i, pg in enumerate(out):
        nxt = out[i + 1] if i + 1 < len(out) else None
        end = pg["ws"][-1]["end"]
        if nxt is None or nxt["a"] - end > PAUSE:
            pg["b"] = round(_cut_at_edges(pg["a"], min(dur, end + 0.3), edges), 3)
        else:
            pg["b"] = nxt["a"]
    return out


def render_caps(pages, opts, theme, half_windows=(), track=3, prefix="k", top_of=None, px=None):
    """→ (css, body[], js[])"""
    acc = theme["accent"]["solid"]
    px = px or opts.get("caps_px", 104)
    ink = opts["backing"]["color"]
    stroke = ", ".join(f"{x}px {y}px 0 {ink}" for x, y in
                       ((-5, 0), (5, 0), (0, -5), (0, 5), (-4, -4), (4, -4), (-4, 4), (4, 4)))
    css = f"""
.cap {{ position: absolute; left: 40px; right: 40px; text-align: center; opacity: 0; }}
.fire {{ color: {theme.get("danger", "#FF3B1F")} !important; }}
.cap .cw {{ display: inline-block; margin: 0 0.24em; font-family: var(--display); font-weight: 700;
  font-size: var(--cpx, {opts.get("caps_px", 104)}px); line-height: 1.05; text-transform: uppercase; letter-spacing: 0.01em;
  color: #fff; text-shadow: {stroke}, 0 10px 26px {_rgba(ink, 0.55)}; }}
"""
    body, js = [], []
    for i, pg in enumerate(pages):
        pid = f"{prefix}{i}"
        top = opts["top_half_px"] if in_half(pg["a"], pg["b"], half_windows) else (
            top_of(pg) if top_of else STYLE_TOP["caps"])
        words = " ".join(f'<span class="cw">{fire(w["text"].rstrip(",."))}</span>' for w in pg["ws"])
        body.append(f'<div id="{pid}" class="clip" data-start="{pg["a"]:.3f}" '
                    f'data-duration="{pg["b"] - pg["a"]:.3f}" data-track-index="{track}">'
                    f'<div class="cap" style="top:{top}px; --cpx:{px}px">{words}</div></div>')
        js.append(f'tl.fromTo("#{pid} .cap", {{opacity: 0, y: 18, scale: 0.94}}, {{opacity: 1, y: 0, scale: 1, '
                  f'duration: 0.12, ease: "back.out(1.6)"}}, {pg["a"]:.3f});')
        for k, w in enumerate(pg["ws"]):
            sel = f'document.querySelectorAll("#{pid} .cw")[{k}]'
            js.append(f'tl.set({sel}, {{color: "{acc}", scale: 1.1}}, {w["start"]:.3f});')
            off = pg["ws"][k + 1]["start"] if k + 1 < len(pg["ws"]) else pg["b"]
            js.append(f'tl.set({sel}, {{color: "#FFFFFF", scale: 1}}, {min(off, w["end"] + 0.25):.3f});')
    return css, body, js


CONTAINER = {"lines": ".rail", "word": ".wcap", "caps": ".cap", "title": ".tt"}
STYLE_NAMES = {"строки": "lines", "по_слову": "word", "капс": "caps", "заголовок": "title",
               "lines": "lines", "word": "word", "caps": "caps", "title": "title"}


def title_pages(segs, dur, edges=()):
    """Страницы заголовка: до 3 слов, конец на знаке препинания (и на запятой) или паузе."""
    pages = []
    for seg in segs:
        cur = []
        for i, w in enumerate(seg):
            cur.append(w)
            nxt = seg[i + 1] if i + 1 < len(seg) else None
            if (len(cur) >= 3 or plain_text(w["text"])[-1:] in ".,?!…" or nxt is None
                    or nxt["start"] - w["end"] > PAUSE
                    or w.get("inserted") or (nxt and nxt.get("inserted"))):
                pages.append(cur)
                cur = []
    out = [{"ws": ws, "lines": [ws], "a": max(0.0, round(ws[0]["start"] - 0.05, 3))} for ws in pages]
    for i, pg in enumerate(out):
        nxt = out[i + 1] if i + 1 < len(out) else None
        end = pg["ws"][-1]["end"]
        if nxt is None or nxt["a"] - end > PAUSE:
            pg["b"] = round(_cut_at_edges(pg["a"], min(dur, end + 0.3), edges), 3)
        else:
            pg["b"] = nxt["a"]
    return out


TITLE_EM = 0.9      # ширина буквы Montserrat Black капсом, em (с запасом на Ю, Щ, Ж)


def title_px(text, base=150, width=TITLE_W):
    """Кегль нижнего слова: base, но не шире кадра."""
    n = max(1, len(plain_text(text)))
    return int(min(base, width / (TITLE_EM * n)))


def render_title(pages, opts, theme, half_windows=(), track=3, prefix="t", top_of=None, px=None):
    """Заголовок: верхние слова белые, последнее — крупнее градиентом акцента. → (css, body[], js[])"""
    base = px or 150
    css = f"""
.tt {{ position: absolute; left: 50px; right: 50px; text-align: center; opacity: 0; }}
.tt .l1 {{ display: block; font-weight: 800; font-size: {int(base * 0.56)}px; line-height: 1.05; color: #fff;
  letter-spacing: -0.01em; text-shadow: 0 6px 26px rgba(0,0,0,0.35); }}
.tt .l2 {{ display: block; font-weight: 900; line-height: 1.0; letter-spacing: -0.02em; text-transform: uppercase;
  filter: drop-shadow(0 8px 24px rgba(0,0,0,0.35)); }}
.tt .fire {{ color: {theme.get("danger", "#FF3B1F")}; -webkit-text-fill-color: {theme.get("danger", "#FF3B1F")}; }}
"""
    grad = accent_style(theme)
    body, js = [], []
    for i, pg in enumerate(pages):
        pid = f"{prefix}{i}"
        ws = pg["ws"]
        top_txt = " ".join(fire(w["text"].rstrip(",.")) for w in ws[:-1])
        last = ws[-1]["text"].rstrip(",.") if not ws[-1]["text"].endswith("...") else ws[-1]["text"]
        l2px = title_px(last, base)
        top = opts["top_half_px"] if in_half(pg["a"], pg["b"], half_windows) else (
            top_of(pg) if top_of else STYLE_TOP["title"])
        l1 = f'<span class="l1">{top_txt}</span>' if top_txt else ""
        fire_only = "[[" in last
        style2 = "" if fire_only else grad
        body.append(f'<div id="{pid}" class="clip" data-start="{pg["a"]:.3f}" data-duration="{pg["b"] - pg["a"]:.3f}" '
                    f'data-track-index="{track}"><div class="tt" style="top:{top}px">{l1}'
                    f'<span class="l2" style="font-size:{l2px}px"><span{style2}>{fire(last)}</span></span></div></div>')
        js.append(f'tl.fromTo("#{pid} .tt", {{opacity: 0, y: 24, scale: 0.92}}, {{opacity: 1, y: 0, scale: 1, '
                  f'duration: 0.16, ease: "back.out(1.6)"}}, {pg["a"]:.3f});')
    return css, body, js


def plan_keys(plan, at, dur):
    """plan.json → (скрытые окна, ключи). Ключи плана:
    "captions_from": <якорь>                 — до этого слова субтитров нет;
    "captions_hide": [{"from", "to"|"end"}]  — окна без субтитров (концовка на весь экран);
    "captions_keys": [{"at", "style"?, "top"?, "slide"?}] — смены по ходу ролика."""
    hidden = []
    if plan.get("captions_from") is not None:
        hidden.append((0.0, at(plan["captions_from"]) - 0.06))
    for h in plan.get("captions_hide", []):
        hidden.append((at(h["from"]) - 0.06, dur + 1 if h.get("to") in (None, "end") else at(h["to"])))
    keys = []
    for k in plan.get("captions_keys", []):
        if k.get("style") and k["style"] not in STYLE_NAMES:
            raise ValueError(f"captions_keys: стиль {k['style']!r}, есть: строки, по_слову, капс, заголовок")
        keys.append({"t": round(at(k["at"]), 3), "style": STYLE_NAMES.get(k.get("style")) if k.get("style") else None,
                     "top": k.get("top"), "slide": k.get("slide"), "px": k.get("px"), "enter": k.get("enter")})
    return hidden, keys


def plan_inserts(plan, at):
    """plan.json "captions_insert": [{"at", "text", "dur"?}] → [{"t", "text", "dur"}]."""
    return [{"t": round(at(i["at"]), 3), "text": i["text"], "dur": i.get("dur", 0.5)}
            for i in plan.get("captions_insert", [])]


def key_states(style, keys):
    """Ключи → [(t, style, top|None, slide|None, px|None, enter|None)] по времени, с накопленным
    состоянием (px держится до следующей смены стиля)."""
    out, top, px = [], None, None
    for k in sorted(keys, key=lambda k: k["t"]):
        if k.get("style") and k["style"] != style:
            style, top, px = k["style"], None, None
        if k.get("top") is not None:
            top = int(k["top"])
        if k.get("px"):
            px = int(k["px"])
        out.append((k["t"], style, top, k.get("slide"), px, k.get("enter")))
    return out


def state_at(t, style0, states):
    """Стиль и высота (None — по умолчанию стиля) в момент t."""
    style, top = style0, None
    for kt, st, tp, *_ in states:
        if kt <= t + 1e-6:
            style, top = st, tp
    return style, top


def px_at(t, states):
    px = None
    for kt, _st, _tp, _sl, kpx, _en in states:
        if kt <= t + 1e-6:
            px = kpx
    return px


def keyed_units(words, dur, opts, hidden=(), edges=(), keys=()):
    """Слова → куски по стилям: [{style, prefix, units}]. Граница куска — смена стиля."""
    style0 = opts["style"]
    states = key_states(style0, keys)
    cuts = [0.0] + [t for t, st, *_ in states
                    if st != state_at(t - 1e-3, style0, states)[0]] + [dur + 1]
    parts = []
    for n, (t0, t1) in enumerate(zip(cuts, cuts[1:])):
        style = state_at(t0, style0, states)[0]
        ws = [w for w in words if t0 - 1e-6 <= w["start"] < t1 - 1e-6]
        if not ws:
            continue
        segs = visible_segments(ws, hidden)
        e = list(edges) + [t1 - 0.02]
        px = px_at(t0, states)
        units = (word_beats(segs, dur, e) if style == "word" else
                 caps_pages(segs, dur, e, px or opts.get("caps_px", 104)) if style == "caps" else
                 title_pages(segs, dur, e) if style == "title" else line_pages(segs, dur, e))
        for u in units:   # строка не переживает окно без субтитров и смену стиля
            u["b"] = round(_cut_at_edges(u["a"], u["b"], e), 3)
        enter = next((en for kt, *_r, en in states if abs(kt - t0) < 1e-6 and en), None)
        parts.append({"style": style, "prefix": f"c{n}u" if keys else "r", "units": units, "px": px,
                      "enter": enter, "t0": t0})
    return parts, states


def build(words, dur, opts, theme, hidden=(), edges=(), half_windows=(), accent_words=(), keys=()):
    """Субтитры целиком → (css, body[], js[], units) — units для отчёта. Строка обрывается там,
    где начинается окно без субтитров (иначе висит поверх плёнки или логотипов)."""
    edges = list(edges) + [a for a, _b in hidden if a > 0]
    parts, states = keyed_units(words, dur, opts, hidden, edges, keys)
    style0 = opts["style"]
    css_by, body, js, units = {}, [], [], []

    def top_of(u):
        style, top = state_at(u["a"], style0, states)
        return top if top is not None else style_top(style, opts)

    for part in parts:
        st, us, pre = part["style"], part["units"], part["prefix"]
        # слово показывается чуть раньше, чем звучит (u["a"] < начала куска): высота — по куску,
        # иначе первое слово нового стиля берёт высоту старого (крупные слова уезжали вниз,
        # а следующее обычное слово — наверх; автор, 2026-10-17)
        tf = (lambda u, t0=part["t0"]: top_of({"a": max(u["a"], t0 + 1e-3)})) if keys else None
        if st == "word":
            c, b, j = render_words(us, opts, theme, accent_words, half_windows, prefix=pre, top_of=tf)
        elif st == "caps":
            c, b, j = render_caps(us, opts, theme, half_windows, prefix=pre, top_of=tf, px=part["px"])
        elif st == "title":
            c, b, j = render_title(us, opts, theme, half_windows, prefix=pre, top_of=tf, px=part["px"])
        else:
            c, b, j = render_lines(us, opts, theme, half_windows, prefix=pre, top_of=tf)
        css_by[st] = c
        body += b
        js += j
        if part["enter"] in ("left", "right") and us:   # смахнул: строка влетает с края
            dx = -1150 if part["enter"] == "left" else 1150
            js.append(f'tl.fromTo("#{pre}0 {CONTAINER[st]}", {{x: {dx}}}, {{x: 0, duration: 0.32, '
                      f'ease: "back.out(1.3)"}}, {us[0]["a"]:.3f});')
        for i, u in enumerate(us):   # переезд под жест: строка едет, а не прыгает
            for kt, _st, _tp, slide, *_r in states:
                if slide and u["a"] < kt < u["b"]:
                    old, new = tf(u), top_of({"a": kt})
                    js.append(f'tl.fromTo("#{pre}{i} {CONTAINER[st]}", {{y: 0}}, {{y: {new - old}, '
                              f'duration: {float(slide):.2f}, ease: "power2.inOut", immediateRender: false}}, '
                              f'{kt:.3f});')
        units += us
    return "".join(css_by.values()), body, js, units


def summary_parts(words, dur, opts, hidden=(), edges=(), keys=()):
    """Для PLAN.md: строки «время  текст», со сменой стиля заголовком."""
    names = {"lines": "строки", "word": "по слову", "caps": "капс", "title": "заголовок"}
    edges = list(edges) + [a for a, _b in hidden if a > 0]   # как в build: отчёт = то, что на экране
    parts, _ = keyed_units(words, dur, opts, hidden, edges, keys)
    out = []
    for part in parts:
        if keys:
            out.append(f"— {names[part['style']]} —")
        out += summary(part["units"])
    return out


def summary(units):
    return [f'{u["a"]:6.2f}–{u["b"]:6.2f}  ' + " / ".join(" ".join(w["text"] for w in ln) for ln in u["lines"])
            for u in units]

