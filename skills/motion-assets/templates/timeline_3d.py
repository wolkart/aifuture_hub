"""Дорожка монтажа в 3D: наклонённый таймлайн с дорожкой видео и звуковой волной, куски
«пауза» и «э-э» вспыхивают красным, вылетают из дорожки в глубину, остальное со щелчком
схлопывается; бегунок проходит по ролику. Родная тема — тёмная.

Когда брать: «нейросеть сама режет паузы и оговорки», «черновой монтаж за тебя» —
показать, что именно вырезано, а не просто сказать.
"""
import random

import _common as c

NAME = "timeline_3d"
TITLE = "Дорожка монтажа в 3D"
DEFAULT_KIND = "dark"
BOX = (200, 1500)
BASE_TAGS = ["монтаж", "таймлайн", "дорожка", "вырезать", "паузы", "оговорки", "резка"]
SLOTS = {
    "context": {"about": "строка-контекст над заголовком, можно пусто", "default": ""},
    "headline": {"about": "заголовок по словам; *слово* — акцент, _слово_ — второй цвет",
                 "default": "Паузы и оговорки — *вырезаны*"},
    "cuts": {"about": "подписи вырезаемых кусков (1–4)", "default": ["пауза", "э-э", "пауза", "оговорка"]},
    "tags": {"about": "до 4 фоновых слов", "default": ["монтаж", "резка", "паузы", "дубли"]},
}
TRACK_W, TRACK_X = 900, 90
# куски дорожки: (доля ширины, вырезается?) — порядок слева направо
PATTERN = [(0.17, False), (0.07, True), (0.14, False), (0.06, True), (0.19, False), (0.07, True),
           (0.12, False), (0.06, True), (0.12, False)]
T_IN, T_MARK, T_OUT, T_SNAP = 0.15, 0.75, 1.15, 1.55


def arrange(cuts):
    """Куски с x и шириной в px; вырезаемых — столько, сколько подписей (≤ 4)."""
    n_cut = max(1, min(4, len(cuts)))
    out, x, k = [], TRACK_X, 0
    for frac, is_cut in PATTERN:
        if is_cut and k >= n_cut:
            is_cut = False
        w = round(TRACK_W * frac)
        out.append({"x": x, "w": w, "cut": is_cut, "label": cuts[k] if is_cut else ""})
        if is_cut:
            k += 1
        x += w
    # после схлопывания: оставшиеся встают подряд, по центру
    kept_w = sum(p["w"] for p in out if not p["cut"])
    nx = TRACK_X + (TRACK_W - kept_w) / 2
    for p in out:
        if not p["cut"]:
            p["dx"] = round(nx - p["x"], 1)
            nx += p["w"]
    return out


def wave(n, seed):
    """Высоты столбиков звуковой волны: детерминированно, без Math.random в странице."""
    rnd = random.Random(seed)
    return [round(0.25 + 0.75 * abs(rnd.gauss(0.45, 0.3)) % 1, 2) for _ in range(n)]


def css(pal):
    panel = c.mix(pal["deep"], c.BLACK, 0.25)
    return f"""
.stage {{ position: absolute; left: 0; right: 0; top: 700px; height: 760px; perspective: 1500px; }}
#tl {{ position: absolute; left: 0; right: 0; top: 60px; height: 600px; transform-style: preserve-3d; opacity: 0; }}
#panel {{ position: absolute; left: 60px; right: 60px; top: 0; height: 600px; border-radius: 36px;
  background: linear-gradient(180deg, {c.rgba(c.mix(panel, c.WHITE, 0.06), 0.96)}, {c.rgba(panel, 0.96)});
  border: 2px solid {c.rgba(pal['sec'], 0.35)}; box-shadow: 0 50px 120px rgba(0, 0, 0, 0.6); }}
.ruler {{ position: absolute; top: 34px; height: 18px; width: 2px; background: {c.rgba(c.WHITE, 0.25)}; }}
.lane {{ position: absolute; left: 90px; width: 900px; border-radius: 14px; background: {c.rgba(c.WHITE, 0.04)}; }}
.clipv {{ position: absolute; top: 0; height: 150px; border-radius: 14px; overflow: hidden;
  background: linear-gradient(135deg, {c.mix(pal['sec'], c.BLACK, 0.15)}, {c.mix(pal['sec'], pal['deep'], 0.55)});
  border: 2px solid {c.rgba(c.WHITE, 0.18)}; }}
.clipv::after {{ content: ""; position: absolute; inset: 14px; border-radius: 8px;
  background: repeating-linear-gradient(90deg, {c.rgba(c.WHITE, 0.16)} 0 46px, {c.rgba(c.WHITE, 0.05)} 46px 52px); }}
.clipa {{ position: absolute; top: 0; height: 130px; border-radius: 14px; display: flex; align-items: center;
  gap: 4px; padding: 0 8px; overflow: hidden; background: {c.rgba(pal['ok'], 0.12)};
  border: 2px solid {c.rgba(pal['ok'], 0.35)}; }}
.bar {{ flex: 1 1 0; min-width: 3px; border-radius: 3px; background: {pal['ok']}; }}
.flag {{ position: absolute; top: 52px; left: 50%; margin-left: -80px; width: 160px; text-align: center;
  padding: 8px 0; border-radius: 999px;
  font-size: 26px; font-weight: 800; white-space: nowrap; color: {pal['deep']}; background: {pal['acc']}; opacity: 0; }}
.redv, .reda {{ position: absolute; inset: 0; border-radius: 14px; opacity: 0; }}
.redv {{ background: {c.rgba(pal['acc'], 0.55)}; box-shadow: 0 0 40px {c.rgba(pal['acc'], 0.8)}; }}
.reda {{ background: {c.rgba(pal['acc'], 0.5)}; }}
#head {{ position: absolute; top: 20px; left: 0; width: 2px; height: 560px; }}
#playhead {{ position: absolute; left: 90px; top: 20px; width: 4px; height: 560px; border-radius: 2px;
  background: {c.WHITE}; box-shadow: 0 0 18px {c.rgba(c.WHITE, 0.8)}; opacity: 0; }}
#playhead::before {{ content: ""; position: absolute; left: -12px; top: -6px; width: 28px; height: 28px;
  border-radius: 6px; background: {c.WHITE}; transform: rotate(45deg); }}
#snap {{ position: absolute; left: 90px; width: 900px; top: 0; height: 600px; border-radius: 36px;
  border: 4px solid {pal['ok']}; opacity: 0; }}
"""


def build(slots, theme, kind=None, layout="full"):
    layout_ = layout
    s = c.merge_slots(SLOTS, slots)
    pal = c.palette(theme, kind or DEFAULT_KIND)
    cuts = [str(x) for x in (s["cuts"] or ["пауза"])][:4]
    h = c.headline(s["headline"], s["context"], prefix="h", top=300)
    js, times = c.headline_js(h, 0.12 if s["context"] else 0.08, 0.7)
    words_end = times[-1] + 0.32 if times else 0.5
    parts = arrange(cuts)
    dur = max(2.6, words_end + 0.5, T_SNAP + 0.9)

    rows = []
    for i, p in enumerate(parts):
        cls = "cut" if p["cut"] else ""
        flag = f'<div class="flag" id="fl{i}">{c.esc(p["label"])}</div>' if p["cut"] else ""
        bars = "".join(f'<i class="bar" style="height:{int(h_ * 100)}%"></i>' for h_ in wave(max(4, p["w"] // 14), i))
        if p["cut"]:   # у тишины волны почти нет, у «э-э» — короткий горб
            bars = "".join(f'<i class="bar" style="height:{6 if p["label"] == cuts[0] else 30}%"></i>'
                           for _ in range(max(4, p["w"] // 14)))
        rows.append(f'<div class="pc {cls}" id="pc{i}" style="position:absolute; left:{p["x"]}px; top:0; '
                    f'width:{p["w"] - 6}px; height:600px; transform-style:preserve-3d">{flag}'
                    f'<div class="clipv" style="left:0; top:120px; width:100%">'
                    f'<div class="redv" id="rv{i}"></div></div>'
                    f'<div class="clipa" style="left:0; top:310px; width:100%">{bars}'
                    f'<div class="reda" id="ra{i}"></div></div></div>')
    ruler = "".join(f'<div class="ruler" style="left:{TRACK_X + k * 75}px"></div>' for k in range(13))
    content = (h["html"] + '<div class="stage" id="stage"><div id="tl"><div id="panel"></div>'
               f'{ruler}{"".join(rows)}<div id="snap"></div><div id="playhead"></div></div></div>')
    deco, deco_js = c.decor(pal, layout_, s["tags"], dur)
    body, bg, size = c.compose(pal, layout_, deco, content, dur, BOX)

    if h["ctx_id"]:
        js.append(f'fadeIn("#{h["ctx_id"]}", 0.02);')
    js += [
        f'tl.fromTo("#tl", {{ opacity: 0, rotationX: 42, rotationY: -22, y: 120, scale: 0.86 }}, '
        f'{{ opacity: 1, rotationX: 24, rotationY: -12, y: 0, scale: 1, duration: 0.6, ease: "power3.out" }}, {T_IN});',
        f'tl.fromTo("#tl", {{ rotationY: -12 }}, {{ rotationY: -4, duration: {c.fmt(dur - 0.8)}, '
        f'ease: "sine.inOut", immediateRender: false }}, 0.75);',
        f'tl.fromTo("#playhead", {{ opacity: 0, x: 0 }}, {{ opacity: 1, x: {TRACK_W - 10}, duration: {c.fmt(T_SNAP - 0.35)}, '
        f'ease: "none" }}, 0.35);',
    ]
    for i, p in enumerate(parts):
        if p["cut"]:
            k = sum(1 for q in parts[:i] if q["cut"])
            t_mark = T_MARK + k * 0.06
            js += [
                f'tl.fromTo("#rv{i}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.12 }}, {c.fmt(t_mark)});',
                f'tl.fromTo("#ra{i}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.12 }}, {c.fmt(t_mark)});',
                f'tl.fromTo("#fl{i}", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.18, '
                f'ease: "back.out(2)" }}, {c.fmt(t_mark)});',
                f'tl.fromTo("#pc{i}", {{ z: 0, y: 0, rotationX: 0, rotationZ: 0, opacity: 1 }}, '
                f'{{ z: 420, y: -260, rotationX: -50, rotationZ: {-18 if k % 2 else 16}, opacity: 0, duration: 0.5, '
                f'ease: "power2.in" }}, {c.fmt(T_OUT + k * 0.05)});',
            ]
        else:
            js.append(f'tl.fromTo("#pc{i}", {{ x: 0 }}, {{ x: {p["dx"]}, duration: 0.35, ease: "back.out(1.4)" }}, '
                      f'{c.fmt(T_SNAP)});')
    js += [
        f'tl.fromTo("#snap", {{ opacity: 0, scale: 1.04 }}, {{ opacity: 0.9, scale: 1, duration: 0.18 }}, {c.fmt(T_SNAP + 0.3)});',
        f'tl.fromTo("#snap", {{ opacity: 0.9 }}, {{ opacity: 0, duration: 0.5, immediateRender: false }}, {c.fmt(T_SNAP + 0.5)});',
        f'tl.fromTo("#playhead", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.2, immediateRender: false }}, {c.fmt(T_SNAP - 0.05)});',
    ]
    js += deco_js

    events = c.headline_events(h, times)
    if s["context"]:
        events.append(c.ev(0.02, f"строка-контекст «{s['context']}»"))
    events += [
        c.ev(T_IN, "дорожка монтажа влетает в 3D"),
        c.ev(0.75, "дорожка видна целиком: видео и звуковая волна"),
        c.ev(0.35, "бегунок идёт по дорожке"),
        c.ev(T_MARK, "куски «" + "», «".join(cuts) + "» вспыхивают красным"),
        c.ev(T_OUT, "красные куски вылетают из дорожки в глубину"),
        c.ev(T_SNAP, "оставшееся схлопывается со щелчком"),
        c.ev(T_SNAP + 0.3, "дорожка без пауз видна целиком, зелёная рамка"),
    ]
    describes = (f"дорожка монтажа в 3D: вспыхивают и вылетают куски «{'», «'.join(cuts)}», остальное схлопывается; "
                 f"заголовок «{h['plain']}»")
    return c.result(c.base_css(pal, layout_) + css(pal), body, js, dur, events, pal, layout_, bg, size, [],
                    BASE_TAGS, describes, preview_t=min(T_SNAP + 0.6, dur - 0.1))
