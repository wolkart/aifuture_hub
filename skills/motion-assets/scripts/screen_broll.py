#!/usr/bin/env python3
"""Б-ролл «экран»: страница сайта в окне браузера на фоне, с камерой и выделением сказанного.

Автор (2026-10-17): скриншот на весь кадр «в лоб» не годится — экран лежит в скруглённом окне
с полями и тенью; фон чередуется (светлый, тёмный, размытая копия того же кадра — blur fill);
в окне выделено то, что звучит, и приёмы чередуются (маркер, рамка со стрелкой, метка,
всплывающая плашка с цифрой, наезд к элементу).

Как устроено: Playwright снимает регион страницы (DPR 3, после загрузки картинок) — по снимку на
каждое состояние (эффекты DOM копятся: маркер, рамка, метка). Кадры собирает PIL: камера —
дробная рамка `resize(box=…)` без дрожания, переходы состояний — маркер волной слева направо
внутри выделения или растворение; стрелка и плашка рисуются поверх. Сырые кадры → ffmpeg.

spec.json:
{
 "id": "rea-gh-repo", "url": "https://github.com/morluto/rea",
 "scheme": "light",                 # тема страницы: light | dark
 "width": 540,                      # ширина окна браузера, CSS-px (мобильная вёрстка)
 "region": {"text": "morluto", "pad": 40, "height": 1100},   # или {"y": 0, "height": 1100}
 "layout": "full",                  # full 1080×1920 (окно сверху, место под субтитры) | half 1080×960
 "bg": "blur",                      # light | dark | blur
 "duration": 3.6,
 "camera": [{"t": 0, "text": "About", "w": 540}, {"t": 2.6, "text": "stars", "w": 330}],
 "effects": [
   {"t": 0.3, "type": "mark", "text": "inspect the app without its source code"},
   {"t": 1.0, "type": "box", "text": "NabilRFG12/Reverse-Engineer-anything", "arrow": "below"},
   {"t": 0.6, "type": "badge", "text": "копия", "after": "NabilRFG12/Reverse-Engineer-anything", "color": "danger"},
   {"t": 2.6, "type": "pop", "text": "250 000+", "sub": "звёзд на GitHub", "near": "stars", "star": true}],
 "tags": ["GitHub", "звёзды"], "describes": "…"
}
Координаты камеры — центр текста на странице; "w" — ширина видимой части, CSS-px.
По умолчанию камера только прокручивает вверх-вниз во всю ширину (автор 2026-10-18: наезд с
одновременным сдвигом «гуляет» вбок); наезд и "w" работают только с "zoom": true в спеке.
Текст можно задать шаблоном: "re:[\\d.,]+k stars" — живые цифры (звёзды растут) не хардкодить.

  screen_broll.py <spec.json> [--settings <reel.settings.json>] [--library <папка>] [--no-index]
"""
import argparse
import asyncio
import json
import math
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "reel" / "scripts"))
sys.path.insert(0, str(HERE))

DPR, FPS = 3, 50
CANVAS = {"full": (1080, 1920), "half": (1080, 960)}
MARGIN = 40          # поля окна; сверху тоже 40 — пустоты над окном нет (урок 2026-10-17)
FULL_WIN_H = 1300    # окно на full: 40…1340, ниже — место под субтитры (верх_px 1450)
BAR = 66             # шапка окна браузера
RADIUS = 30
ENTER = 0.3          # окно влетает
WIPE, FADE, ARROW, POP = 0.4, 0.22, 0.28, 0.35


# ── геометрия (чистые функции — тесты) ────────────────────────────────────────

def smooth(t, t0, t1):
    p = min(1.0, max(0.0, (t - t0) / max(1e-6, t1 - t0)))
    return p * p * (3 - 2 * p)


def window_rect(layout):
    """Окно на холсте: (x, y, w, h). Сверху поле MARGIN — без пустоты над окном."""
    cw, ch = CANVAS[layout]
    h = FULL_WIN_H if layout == "full" else ch - 2 * MARGIN
    return MARGIN, MARGIN, cw - 2 * MARGIN, h


def inner_size(layout):
    _, _, w, h = window_rect(layout)
    return w, h - BAR


def camera_at(keys, t, aspect, region_w, region_h):
    """keys: [{t, cx, cy, w}] (CSS-px региона) → рамка (x, y, w, h) в CSS-px, внутри региона.
    aspect = высота/ширина окна. Между ключами — smoothstep."""
    keys = sorted(keys, key=lambda k: k["t"])
    if t <= keys[0]["t"]:
        k = dict(keys[0])
    elif t >= keys[-1]["t"]:
        k = dict(keys[-1])
    else:
        a, b = next((a, b) for a, b in zip(keys, keys[1:]) if a["t"] <= t <= b["t"])
        e = smooth(t, a["t"], b["t"])
        k = {f: a[f] + (b[f] - a[f]) * e for f in ("cx", "cy", "w")}
    w = min(k["w"], region_w, region_h / aspect)
    h = w * aspect
    x = min(max(0.0, k["cx"] - w / 2), region_w - w)
    y = min(max(0.0, k["cy"] - h / 2), region_h - h)
    return x, y, w, h


def pop_scale(p):
    """Плашка выскакивает: 0,6 → 1,08 (70 % времени) → 1,0."""
    if p >= 1:
        return 1.0
    if p < 0.7:
        return 0.6 + 0.48 * smooth(p, 0, 0.7)
    return 1.08 - 0.08 * smooth(p, 0.7, 1.0)


def to_window(box, cam, inner_w):
    """Прямоугольник региона (CSS-px) → координаты внутри области окна под шапкой (px холста)."""
    x, y, w, h = box
    cx, cy, cw, _ = cam
    s = inner_w / cw
    return (x - cx) * s, (y - cy) * s, w * s, h * s


# ── съёмка ───────────────────────────────────────────────────────────────────

MARK = "background:#C8F560;color:#020105;border-radius:6px;padding:1px 3px;box-decoration-break:clone;-webkit-box-decoration-break:clone"
BOX = "border:4px solid #FF3B1F;border-radius:10px"
# Поиск текста через границы элементов («<strong>290.0k</strong> stars»): видимые текстовые узлы
# сшиваются в одну строку, пробелы схлопываются; находка → куски по узлам.
SEG_JS = r"""(needle) => {
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {acceptNode: (t) => {
    const pe = t.parentElement; if (!pe || pe.closest('script,style,template,noscript')) return NodeFilter.FILTER_REJECT;
    const r = pe.getBoundingClientRect(); return (r.width > 0 && r.height > 0) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT; }});
  const BLK = 'p,div,li,h1,h2,h3,h4,h5,h6,section,article,td,th,pre,blockquote,header,footer,main,nav,ul,ol,tr,figcaption';
  const blk = (t) => t.parentElement.closest(BLK);
  let text = '', map = [], n, prevSpace = true, prev = null;
  while ((n = w.nextNode())) { const v = n.nodeValue;
    // перенос <br> или переход в другой блок — это пробел, хотя в DOM его нет («копирует<br>текст»)
    if (prev && !prevSpace && (blk(n) !== blk(prev) || (n.previousSibling && n.previousSibling.nodeName === 'BR'))) {
      text += ' '; map.push(null); prevSpace = true; }
    prev = n;
    for (let i = 0; i < v.length; i++) { const sp = /\s/.test(v[i]);
      if (sp && prevSpace) continue; text += sp ? ' ' : v[i]; map.push([n, i]); prevSpace = sp; } }
  let at, len;
  if (needle.startsWith('re:')) { const m = new RegExp(needle.slice(3)).exec(text); if (!m) return null; at = m.index; len = m[0].length; }
  else { const norm = needle.replace(/\s+/g, ' ').trim(); at = text.indexOf(norm); len = norm.length; }
  if (at < 0) return null;
  const segs = []; let cur = null;
  for (let k = at; k < at + len; k++) { if (!map[k]) continue; const [node, off] = map[k];
    if (!cur || cur.node !== node) { cur = {node, start: off, end: off + 1}; segs.push(cur); } else cur.end = off + 1; }
  return segs; }"""
BBOX_JS = "(needle) => { const segs = (" + SEG_JS + ")(needle); if (!segs) return null;" \
          " let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; for (const s of segs) { const r = document.createRange();" \
          " r.setStart(s.node, s.start); r.setEnd(s.node, s.end); for (const b of r.getClientRects()) {" \
          " if (!b.width) continue; x0 = Math.min(x0, b.left); y0 = Math.min(y0, b.top); x1 = Math.max(x1, b.right); y1 = Math.max(y1, b.bottom); } }" \
          " return x1 < x0 ? null : [x0 + scrollX, y0 + scrollY, x1 - x0, y1 - y0]; }"
MARK_JS = "([needle, style]) => { const segs = (" + SEG_JS + ")(needle); if (!segs) return null;" \
          " for (const s of segs.reverse()) { const r = document.createRange(); r.setStart(s.node, s.start); r.setEnd(s.node, s.end);" \
          " const m = document.createElement('span'); m.setAttribute('style', style); r.surroundContents(m); }" \
          " return (" + BBOX_JS + ")(needle); }"
BOXDIV_JS = "([needle, style]) => { const b = (" + BBOX_JS + ")(needle); if (!b) return null; const d = document.createElement('div');" \
            " const pad = 6; d.setAttribute('style', `position:absolute;left:${b[0]-pad}px;top:${b[1]-pad}px;width:${b[2]+2*pad}px;" \
            "height:${b[3]+2*pad}px;pointer-events:none;z-index:99999;box-sizing:border-box;${style}`); document.body.appendChild(d);" \
            " return [b[0]-pad, b[1]-pad, b[2]+2*pad, b[3]+2*pad]; }"
BADGE_JS = """([needle, text, bg, fg]) => { const segs = (SEG)(needle); if (!segs) return null;
  const host = segs[segs.length - 1].node.parentElement; const s = document.createElement('span'); s.textContent = text;
  s.setAttribute('style', `margin-left:8px;padding:3px 10px;border-radius:999px;font:700 13px/1.4 -apple-system,sans-serif;background:${bg};color:${fg};vertical-align:middle;white-space:nowrap`);
  host.after(s); const b = s.getBoundingClientRect(); return [b.x + scrollX, b.y + scrollY, b.width, b.height]; }""".replace("(SEG)", "(" + SEG_JS + ")")


READY_CSS_JS = """() => [...document.querySelectorAll('link[rel=stylesheet][href]')]
  .filter(l => l.getAttribute('href')).every(l => l.sheet)
  && !/^"?(Times|serif)/i.test(getComputedStyle(document.body).fontFamily)"""   # шрифт браузера = стили не легли


async def _shoot(spec, out_dir, colors):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome")
        ctx = await b.new_context(viewport={"width": spec.get("width", 540), "height": 960}, device_scale_factor=DPR,
                                  color_scheme=spec.get("scheme", "light"), locale="ru-RU")
        pg = await ctx.new_page()
        for attempt in range(4):                   # сеть рвётся: стили/картинки не догрузились — перезагрузить
            await pg.goto(spec["url"], wait_until="load", timeout=60000)
            try:
                await pg.wait_for_load_state("networkidle", timeout=6000)
            except Exception:
                pass                                # GitHub держит соединения — не ждём бесконечно
            css_ok = await pg.evaluate(READY_CSS_JS)
            if css_ok:
                break
            print(f"  стили не догрузились, перезагрузка {attempt + 1}/3", file=sys.stderr)
            await pg.wait_for_timeout(2000)
        else:
            raise SystemExit("страница без стилей после 4 попыток (сеть?) — сломанный кадр не снимаю")
        reg = spec.get("region", {})
        if reg.get("text"):
            bb = await pg.evaluate(BBOX_JS, reg["text"])
            if not bb:
                raise SystemExit(f"регион: текст «{reg['text']}» не найден на странице")
            y0 = max(0, bb[1] - reg.get("pad", 40))
        else:
            y0 = reg.get("y", 0)
        h = reg.get("height", 960)
        await pg.evaluate(f"window.scrollTo(0, {y0})")
        await pg.wait_for_timeout(600)
        images_ok = True
        img_js = ("(() => { const y0 = %d, y1 = %d; return Array.from(document.images).filter(i => {"
                  " const r = i.getBoundingClientRect(); const top = r.top + scrollY;"
                  " return r.height > 0 && top < y1 && top + r.height > y0; })"
                  ".every(i => i.complete && i.naturalWidth > 0); })()") % (y0, y0 + h)
        for attempt in range(3):                   # битая картинка (аватар, логотип) — перезагрузить её
            try:
                await pg.wait_for_function(img_js, timeout=6000)
                break
            except Exception:
                images_ok = False
                await pg.evaluate("Array.from(document.images).filter(i => !(i.complete && i.naturalWidth))"
                                  ".forEach(i => { const s = i.src; i.src = ''; i.src = s; })")
        else:
            pass
        if not images_ok:
            images_ok = await pg.evaluate(img_js)
        await pg.evaluate("window.scrollTo(0, 0)")
        width = spec.get("width", 540)
        clip = {"x": 0, "y": y0, "width": width, "height": h}
        rel = lambda bx: [bx[0], bx[1] - y0, bx[2], bx[3]] if bx else None
        focus = {}
        for k in spec.get("camera", []):
            if k.get("text") and k["text"] not in focus:
                focus[k["text"]] = rel(await pg.evaluate(BBOX_JS, k["text"]))
        for e in spec.get("effects", []):
            for key in ("near",):
                if e.get(key) and e[key] not in focus:
                    focus[e[key]] = rel(await pg.evaluate(BBOX_JS, e[key]))
        states = [str(out_dir / "state-0.png")]
        await pg.screenshot(path=states[0], full_page=True, clip=clip)
        boxes = []
        for i, e in enumerate(sorted(spec.get("effects", []), key=lambda e: e["t"]), 1):
            if e["type"] == "mark":
                bx = await pg.evaluate(MARK_JS, [e["text"], MARK])
            elif e["type"] == "box":
                bx = await pg.evaluate(BOXDIV_JS, [e["text"], BOX])
            elif e["type"] == "badge":
                bg, fg = {"danger": (colors["danger"], "#FFFFFF"), "accent": (colors["accent"], "#020105"),
                          "success": (colors["success"], "#020105")}[e.get("color", "accent")]
                bx = await pg.evaluate(BADGE_JS, [e.get("after", e.get("text")), e["text"], bg, fg])
            else:                                       # pop — рисуется поверх, DOM не меняется
                boxes.append({"effect": e, "state": len(states) - 1, "box": focus.get(e.get("near"))})
                continue
            if bx is None:
                raise SystemExit(f"эффект {e['type']}: текст «{e.get('text') or e.get('after')}» не найден")
            await pg.wait_for_timeout(120)
            path = str(out_dir / f"state-{len(states)}.png")
            await pg.screenshot(path=path, full_page=True, clip=clip)
            states.append(path)
            boxes.append({"effect": e, "state": len(states) - 1, "box": rel(bx)})
        await b.close()
    return {"states": states, "focus": focus, "effects": boxes, "region": [width, h], "images_ok": images_ok,
            "url_text": (urlparse(spec["url"]).netloc + urlparse(spec["url"]).path).rstrip("/")}


# ── кадры ────────────────────────────────────────────────────────────────────

def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _font(path, size, bold=True):
    from PIL import ImageFont
    f = ImageFont.truetype(str(path), size)
    if bold:
        try:
            f.set_variation_by_name("Bold")
        except Exception:
            pass
    return f


def _gradient(size, top, bottom):
    from PIL import Image
    w, h = size
    g = Image.new("RGB", (1, h))
    t, b = _rgb(top), _rgb(bottom)
    for y in range(h):
        k = y / max(1, h - 1)
        g.putpixel((0, y), tuple(int(t[i] + (b[i] - t[i]) * k) for i in range(3)))
    return g.resize((w, h))


def _background(kind, size, state0, theme):
    from PIL import Image, ImageEnhance, ImageFilter
    if kind == "light":
        return _gradient(size, *theme["bg_light"])
    if kind == "dark":
        return _gradient(size, *theme["bg_dark"])
    w, h = size                                     # blur fill: та же картинка, крупнее, размыта, темнее
    im = state0.copy()
    s = max(w / im.width, h / im.height) * 1.15
    im = im.resize((int(im.width * s), int(im.height * s)))
    x, y = (im.width - w) // 2, (im.height - h) // 2
    im = im.crop((x, y, x + w, y + h)).filter(ImageFilter.GaussianBlur(40))
    return ImageEnhance.Brightness(im).enhance(0.55)


def _window_chrome(win_w, win_h, scheme, url_text, theme):
    """Рамка окна (RGBA): шапка с точками и адресом, скругление. Возвращает (рамка, маска области контента)."""
    from PIL import Image, ImageDraw
    dark = scheme == "dark"
    frame = Image.new("RGBA", (win_w, win_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle([0, 0, win_w - 1, win_h - 1], RADIUS, fill=(28, 28, 40, 255) if dark else (238, 239, 244, 255),
                        outline=(80, 80, 110, 255) if dark else (205, 210, 228, 255), width=2)
    for i, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        d.ellipse([30 + i * 30 - 9, BAR // 2 - 9, 30 + i * 30 + 9, BAR // 2 + 9], fill=_rgb(c))
    pill = [130, 14, win_w - 40, BAR - 14]
    d.rounded_rectangle(pill, (BAR - 28) // 2, fill=(48, 48, 66, 255) if dark else (255, 255, 255, 255))
    f = _font(theme["font_main"], 24, bold=False)
    txt = url_text if len(url_text) < 48 else url_text[:46] + "…"
    d.text((pill[0] + 22, (pill[1] + pill[3]) // 2), txt, font=f, anchor="lm",
           fill=(170, 170, 195, 255) if dark else (110, 112, 130, 255))
    mask = Image.new("L", (win_w, win_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([2, BAR, win_w - 3, win_h - 3], RADIUS - 2, fill=255)
    ImageDraw.Draw(mask).rectangle([2, BAR, win_w - 3, BAR + RADIUS], fill=255)
    return frame, mask


def _shadow(size, rect):
    from PIL import Image, ImageDraw, ImageFilter
    sh = Image.new("RGBA", size, (0, 0, 0, 0))
    x, y, w, h = rect
    ImageDraw.Draw(sh).rounded_rectangle([x + 6, y + 22, x + w - 6, y + h + 22], RADIUS, fill=(0, 0, 0, 120))
    return sh.filter(ImageFilter.GaussianBlur(26))


def _arrow(draw, tip, side, length, color, width=10):
    tx, ty = tip
    dx, dy = {"below": (0.55, 1), "above": (0.55, -1), "left": (-1, 0.45), "right": (1, 0.45)}[side]
    n = math.hypot(dx, dy)
    sx, sy = tx + dx / n * length, ty + dy / n * length
    draw.line([(sx, sy), (tx, ty)], fill=color, width=width)
    ang = math.atan2(ty - sy, tx - sx)
    head = 30
    pts = [(tx, ty), (tx - head * math.cos(ang - 0.45), ty - head * math.sin(ang - 0.45)),
           (tx - head * math.cos(ang + 0.45), ty - head * math.sin(ang + 0.45))]
    draw.polygon(pts, fill=color)


def _star(draw, cx, cy, r, angle, color):
    pts = []
    for k in range(10):
        rr = r if k % 2 == 0 else r * 0.45
        a = angle + k * math.pi / 5 - math.pi / 2
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    draw.polygon(pts, fill=color)


def _pop_card(text, sub, theme, scheme):
    from PIL import Image, ImageDraw
    f1, f2 = _font(theme["font_display"], 110), _font(theme["font_main"], 34)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    w1 = tmp.textbbox((0, 0), text, font=f1)[2]
    w2 = tmp.textbbox((0, 0), sub, font=f2)[2] if sub else 0
    w, h = max(w1, w2) + 120, 200 + (56 if sub else 0)
    card = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([30, 30, 30 + w, 30 + h], 34, fill=(255, 255, 255, 250) if scheme != "dark" else (24, 24, 40, 250),
                        outline=_rgb(theme["secondary"]) + (255,), width=4)
    d.text((30 + w // 2, 30 + 105), text, font=f1, anchor="mm", fill=_rgb(theme["secondary"]))
    if sub:
        d.text((30 + w // 2, 30 + 205), sub, font=f2, anchor="mm",
               fill=_rgb(theme["text_dark"]) if scheme != "dark" else (220, 220, 235))
    return card


def render(spec, shot, out_mp4, theme):
    from PIL import Image, ImageDraw
    layout = spec.get("layout", "half")
    cw, ch = CANVAS[layout]
    wx, wy, ww, wh = window_rect(layout)
    iw, ih = inner_size(layout)
    states = [Image.open(s).convert("RGB") for s in shot["states"]]
    rw, rh = shot["region"]
    bg = _background(spec.get("bg", "light"), (cw, ch), states[0], theme)
    frame, mask = _window_chrome(ww, wh, spec.get("scheme", "light"), shot["url_text"], theme)
    shadow = _shadow((cw, ch), (wx, wy, ww, wh))
    keys = []
    for k in spec.get("camera", [{"t": 0, "w": rw}]):
        if k.get("text"):
            b = shot["focus"].get(k["text"])
            if not b:
                raise SystemExit(f"камера: текст «{k['text']}» не найден")
            cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
        else:
            cx, cy = k.get("x", rw / 2), k.get("y", rh / 2)
        if spec.get("zoom"):
            keys.append({"t": k["t"], "cx": cx, "cy": cy, "w": k.get("w", rw)})
        else:   # автор 2026-10-18: наезд «гуляет» вбок — по умолчанию статика и прокрутка вверх-вниз
            keys.append({"t": k["t"], "cx": rw / 2, "cy": cy, "w": rw})
    effects = shot["effects"]
    danger = _rgb(theme["danger"])
    pops = {id(e): _pop_card(e["effect"]["text"], e["effect"].get("sub", ""), theme, spec.get("scheme", "light"))
            for e in effects if e["effect"]["type"] == "pop"}
    D = float(spec["duration"])
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{cw}x{ch}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_mp4)], stdin=subprocess.PIPE)
    last = None
    for n in range(int(round(D * FPS))):
        t = n / FPS
        cam = camera_at(keys, t, ih / iw, rw, rh)
        box = (cam[0] * DPR, cam[1] * DPR, (cam[0] + cam[2]) * DPR, (cam[1] + cam[3]) * DPR)
        cur = states[0].resize((iw, ih), Image.LANCZOS, box=box)
        overlay = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for e in effects:
            ef, st = e["effect"], e["state"]
            if ef["type"] == "pop":
                continue
            if t < ef["t"]:
                continue
            nxt = states[st].resize((iw, ih), Image.LANCZOS, box=box)
            if ef["type"] == "mark":
                p = smooth(t, ef["t"], ef["t"] + WIPE)
                bx, by, bw, bh = to_window(e["box"], cam, iw)
                edge = int(max(0, min(iw, bx - 6 + (bw + 12) * p)))
                if p >= 1:
                    cur = nxt
                elif edge > 0:
                    cur.paste(nxt.crop((0, 0, edge, ih)), (0, 0))
            else:
                p = smooth(t, ef["t"], ef["t"] + FADE)
                cur = nxt if p >= 1 else Image.blend(cur, nxt, p)
            if ef["type"] == "box" and ef.get("arrow"):
                p = smooth(t, ef["t"] + 0.1, ef["t"] + 0.1 + ARROW)
                if p > 0:
                    bx, by, bw, bh = to_window(e["box"], cam, iw)
                    side = ef["arrow"] if isinstance(ef["arrow"], str) else "below"
                    tip = {"below": (bx + bw * 0.5, by + bh + 12), "above": (bx + bw * 0.5, by - 12),
                           "left": (bx - 12, by + bh / 2), "right": (bx + bw + 12, by + bh / 2)}[side]
                    _arrow(od, tip, side, 40 + 150 * p, danger)
        win = Image.new("RGBA", (ww, wh), (0, 0, 0, 0))
        win.paste(frame, (0, 0))
        content = Image.new("RGBA", (ww, wh), (0, 0, 0, 0))
        content.paste(cur, (2, BAR))
        content.alpha_composite(overlay, (2, BAR))
        win.paste(content, (0, 0), mask)
        canvas = bg.copy().convert("RGBA")
        e_in = smooth(t, 0, ENTER)
        if e_in < 1:                                   # окно влетает: снизу, из 94 % и прозрачности
            s = 0.94 + 0.06 * e_in
            ws = win.resize((int(ww * s), int(wh * s)), Image.BILINEAR)
            a = ws.getchannel("A").point(lambda v: int(v * e_in))
            ws.putalpha(a)
            sh = shadow.copy()
            sh.putalpha(sh.getchannel("A").point(lambda v: int(v * e_in)))
            canvas.alpha_composite(sh)
            canvas.alpha_composite(ws, (int(wx + ww * (1 - s) / 2), int(wy + wh * (1 - s) / 2 + 40 * (1 - e_in))))
        else:
            canvas.alpha_composite(shadow)
            canvas.alpha_composite(win, (wx, wy))
        for e in effects:
            ef = e["effect"]
            if ef["type"] != "pop" or t < ef["t"]:
                continue
            s = pop_scale((t - ef["t"]) / POP)
            card = pops[id(e)]
            cs = card.resize((max(1, int(card.width * s)), max(1, int(card.height * s))), Image.BILINEAR)
            if e["box"]:
                bx, by, bw, bh = to_window(e["box"], cam, iw)
                cxp, cyp = wx + 2 + bx + bw / 2, wy + BAR + by + bh + 130
            else:
                cxp, cyp = cw / 2, wy + wh / 2
            cxp = min(max(cs.width / 2 + 20, cxp), cw - cs.width / 2 - 20)
            cyp = min(max(cs.height / 2 + 20, cyp), wy + wh - cs.height / 2)
            canvas.alpha_composite(cs, (int(cxp - cs.width / 2), int(cyp - cs.height / 2)))
            if ef.get("star"):                         # звёздочка влетает с поворотом, искры разлетаются
                sd = ImageDraw.Draw(canvas)
                q = smooth(t, ef["t"] + 0.1, ef["t"] + 0.5)
                sx, sy = cxp + card.width / 2 - 50, cyp - card.height / 2 + 30   # правый верхний угол плашки
                r = 70 * (0.3 + 0.7 * q) * (1 + 0.12 * math.sin(max(0.0, t - ef["t"] - 0.5) * 9))
                gold = (255, 196, 46, 255)
                if q > 0:
                    _star(sd, sx, sy, r, (1 - q) * -math.pi, gold)
                k = smooth(t, ef["t"] + 0.35, ef["t"] + 0.95)
                if 0 < k < 1:
                    for j in range(8):
                        a = j * math.pi / 4 + 0.3
                        d = 60 + 120 * k
                        rr = 9 * (1 - k)
                        sd.ellipse([sx + d * math.cos(a) - rr, sy + d * math.sin(a) - rr,
                                    sx + d * math.cos(a) + rr, sy + d * math.sin(a) + rr], fill=gold)
        last = canvas.convert("RGB")
        ff.stdin.write(last.tobytes())
    ff.stdin.close()
    ff.wait()
    return last


def events_for(spec, shot):
    ev = [{"t": 0.0, "what": f"окно браузера «{shot['url_text']}» влетает"},
          {"t": ENTER, "what": "окно видно целиком"}]
    for k in spec.get("camera", [])[1:]:
        ev.append({"t": float(k["t"]), "what": f"камера у «{k.get('text', 'точки')}»"})
    for e in spec.get("effects", []):
        what = {"mark": f"маркер по «{e.get('text')}»", "box": f"красная рамка «{e.get('text')}»"
                + (" со стрелкой" if e.get("arrow") else ""), "badge": f"метка «{e.get('text')}»",
                "pop": f"плашка «{e.get('text')}»"}[e["type"]]
        ev.append({"t": float(e["t"]), "what": what})
    return sorted(ev, key=lambda e: e["t"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--settings")
    ap.add_argument("--library")
    ap.add_argument("--no-index", action="store_true")
    args = ap.parse_args(argv)
    import settings as st
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    s = st.load(args.settings) or st.default()
    theme = s["theme"]
    lib = Path(args.library) if args.library else s["folders"]["library"]
    out_dir = lib / spec["id"]
    shots = out_dir / "_shots"
    shots.mkdir(parents=True, exist_ok=True)
    colors = {"danger": theme.get("danger", "#FF3B1F"), "accent": theme["accent"]["solid"], "success": theme["success"]}
    shot = asyncio.run(_shoot(spec, shots, colors))
    if not shot["images_ok"]:
        print("⚠ не все картинки на странице загрузились — проверь кадр (аватар, логотип)", file=sys.stderr)
    mp4 = out_dir / f"{spec['id']}.mp4"
    last = render(spec, shot, mp4, theme)
    last.save(out_dir / f"{spec['id']}-preview.png")
    entry = {"id": spec["id"], "kind": "broll", "layout": spec.get("layout", "half"), "duration": float(spec["duration"]),
             "theme": "light" if spec.get("bg", "light") == "light" else "dark",
             "tags": spec.get("tags", []), "describes": spec.get("describes", f"экран {shot['url_text']} в окне"),
             "events": events_for(spec, shot), "transitions": [], "private": [],
             "files": {"mp4": f"{spec['id']}/{spec['id']}.mp4", "preview": f"{spec['id']}/{spec['id']}-preview.png"},
             "source": spec["url"]}
    (out_dir / f"{spec['id']}.entry.json").write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8")
    if not args.no_index:
        subprocess.run([sys.executable, str(HERE / "library.py"), "add", str(out_dir / f"{spec['id']}.entry.json")]
                       + (["--library", str(lib)] if args.library else []), check=True)
    print(f"✓ {mp4} · {spec['duration']} с · {spec.get('layout', 'half')} · фон {spec.get('bg', 'light')}")
    print("  опись: события из спеки; приватное — проверь листами scan_broll.py, прежде чем ставить в ролик")


if __name__ == "__main__":
    main()
