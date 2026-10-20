"""Светлая панель (16:9) — основа графики на кусках «говорящая голова»: панель в брендовом
градиенте выезжает справа на ~2/3 кадра, кадр с автором одновременно уезжает влево — автор
целиком в левой части; панель держится открытой, а на ней по словам сменяются группы —
список, сообщение, цифра, сравнение, крупная фраза (смена — размытием, как у LABA_DA);
в конце панель уезжает, кадр возвращается как был.
Родная тема — светлая; раскладка — full: сцена сама показывает видео автора (слот face) и в
монтажке кладётся поверх его кадра на эти секунды. Звук голоса — с основной дорожки, в файле
только звуки появления.

Когда брать: основа (автор, 2026-10-18: «основой должны быть эти штуки — лучше цепляют взгляд»);
всплывашки вокруг головы (`wide_chips`, `wide_number`, `wide_message`, `wide_list`) — для мелких
акцентов между панелями.
"""
from pathlib import Path

import _common as c
import _wide as w

NAME = "wide_drawer"
TITLE = "Светлая панель с группами (16:9)"
DEFAULT_KIND = "light"
FORMAT = w.FORMAT
DEFAULT_LAYOUT = "full"
BASE_TAGS = ["панель", "объяснение", "пункты", "дровер"]
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}
TYPES = ("list", "message", "number", "compare", "text", "choice")
SLOTS = {
    "face": {"about": "видео с автором (кусок записи камеры), пусто — без видео", "default": ""},
    "face_start": {"about": "с какой секунды видео начать", "default": 0.0},
    "focus_x": {"about": "где автор в кадре по горизонтали, доля (центр лица)", "default": 0.45},
    "panel": {"about": "ширина панели, доля кадра", "default": 0.64},
    "open_at": {"about": "секунда, когда панель выезжает", "default": 0.2},
    "close_at": {"about": "секунда, когда панель уезжает (0 — последняя группа + 3 с)", "default": 0},
    "groups": {"about": ("группы по очереди: [{at, type: list|message|number|compare|text|choice, rubric, title, …}] — "
                         "list: items [{icon, title, sub, at}]; message: name, avatar, time, text, reply, reply_at; "
                         "number: value (*часть* синим), caption — со звуком «приз»; "
                         "compare: left/right {icon, title, sub, at}, verdict, verdict_at, pick: left|right, pick_at; "
                         "text: title, icon; choice: items [{icon, title, sub, at}], pick (номер с 0), pick_at, verdict, verdict_at — "
                         "выбранный вариант зеленеет с галочкой (звук «выбор»), остальные гаснут"),
               "default": [{"at": 0.6, "type": "list", "rubric": "Разбираем", "title": "Главное *коротко*",
                            "items": [{"icon": "1", "title": "Первое", "sub": "пояснение", "at": 1.2},
                                      {"icon": "2", "title": "Второе", "sub": "пояснение", "at": 1.9}]},
                           {"at": 3.6, "type": "number", "rubric": "Итог", "value": "*×10*", "caption": "быстрее"}]},
    "tags": {"about": "доп. теги", "default": []},
}


def blue_html(text):
    out, blue = [], False
    for part in str(text).split("*"):
        if part:
            out.append(f'<span class="blue">{c.esc(part)}</span>' if blue else c.esc(part))
        blue = not blue
    return "".join(out)


def check_html(id_):
    return f'<div class="okc" id="{id_}">✓</div>'


def pick_js(card, check, others, t):
    """Выбор: карточка зеленеет, галочка выскакивает, остальные гаснут."""
    js = [f'tl.to("#{card}", {{ borderColor: OK, backgroundColor: OK_TINT, duration: 0.22, ease: "power2.out" }}, {c.fmt(t)});',
          f'tl.fromTo("#{check}", {{ opacity: 0, scale: 0.3 }}, {{ opacity: 1, scale: 1, duration: 0.32, ease: "back.out(2.6)" }}, {c.fmt(t)});']
    if others:
        js.append(f'tl.to("{", ".join("#" + o for o in others)}", {{ opacity: 0.42, filter: "grayscale(1)", duration: 0.25 }}, {c.fmt(t)});')
    return js


def group_html(gi, g, files):
    """HTML группы, её элементы для анимации [(id, t, что, звук)] и выбор [(t, (карточка, галочка, остальные), что)]."""
    at = float(g.get("at", 0))
    kind = g.get("type", "list")
    if kind not in TYPES:
        raise ValueError(f"тип группы {kind!r}: один из {', '.join(TYPES)}")
    parts, els, picks = [], [], []
    if g.get("rubric"):
        parts.append(f'<div class="pill rub" id="g{gi}r" style="position:relative">{c.esc(g["rubric"])}</div>')
        els.append((f"g{gi}r", at, f"рубрика «{g['rubric']}»"))
    if g.get("title"):
        size = 104 if kind == "text" else 84
        title = blue_html(g["title"])
        if g.get("icon"):                                   # логотип у заголовка: «Ушёл от n8n» + значок n8n
            ic, f = c.icon_html(g["icon"], "", name=f"g{gi}ti")
            files += f
            box = int(size * 1.35)
            title = (f'<span class="tic" style="width:{box}px;height:{box}px">{ic}</span><span>{title}</span>')
        parts.append(f'<div class="ttl pt{" withic" if g.get("icon") else ""}" id="g{gi}t" style="font-size:{size}px">{title}</div>')
        els.append((f"g{gi}t", at + 0.12, f"заголовок «{str(g['title']).replace('*', '')}»"))
    if kind == "list":
        rows = []
        for i, it in enumerate(list(g.get("items", []))[:4]):
            h, f = w.item_html(i, it, 46, prefix=f"g{gi}i")
            rows.append(h)
            files += f
            els.append((f"g{gi}i{i}", float(it.get("at", at + 0.6 + 0.7 * i)) - 0.12, f"пункт «{it.get('title', '')}»"))
        parts.append(f'<div class="list">{"".join(rows)}</div>')
    elif kind == "message":
        av, f = c.icon_html(g.get("avatar", "•"), "", name=f"g{gi}av")
        files += f
        tm = f'<span class="tm">{c.esc(g["time"])}</span>' if g.get("time") else ""
        parts.append(f'<div class="msg" id="g{gi}m"><div class="hd"><div class="av">{av}</div><b>{c.esc(g.get("name", ""))}</b>{tm}</div>'
                     f'<div class="tx">{c.esc(g.get("text", ""))}</div></div>')
        els.append((f"g{gi}m", at + 0.2, f"сообщение «{g.get('text', '')}»"))
        if g.get("reply"):
            parts.append(f'<div class="rep" id="g{gi}p">{c.esc(g["reply"])}</div>')
            els.append((f"g{gi}p", float(g.get("reply_at") or at + 1.4) - 0.12, f"ответ «{g['reply']}»"))
    elif kind == "number":
        parts.append(f'<div class="num" id="g{gi}n">{blue_html(g.get("value", ""))}</div>')
        els.append((f"g{gi}n", at + 0.15, f"цифра «{str(g.get('value', '')).replace('*', '')}»", w.REWARD))
        if g.get("caption"):
            parts.append(f'<div class="pill cap" id="g{gi}c" style="position:relative">{c.esc(g["caption"])}</div>')
            els.append((f"g{gi}c", at + 0.4, f"подпись «{g['caption']}»"))
    elif kind == "compare":
        cards, pick = [], g.get("pick")
        if pick not in (None, "left", "right"):
            raise ValueError(f"compare.pick: left или right, а не {pick!r}")
        for side, dt in (("left", 0.3), ("right", 1.0)):
            d = g.get(side) or {}
            sub = f'<div class="sub">{c.esc(d["sub"])}</div>' if d.get("sub") else ""
            ic = ""
            if d.get("icon"):
                ih, f = c.icon_html(d["icon"], "", name=f"g{gi}{side[0]}ic")
                files += f
                ic = f'<div class="cic">{ih}</div>'
            mark = check_html(f"g{gi}{side[0]}k") if pick == side else ""
            cls = "cmp" + ("" if pick else f" {side}")
            cards.append(f'<div class="{cls}" id="g{gi}{side[0]}">{mark}{ic}<div class="ttl">{c.esc(d.get("title", ""))}</div>{sub}</div>')
            els.append((f"g{gi}{side[0]}", float(d.get("at", at + dt)) - 0.12, f"карточка «{d.get('title', '')}»"))
        parts.append(f'<div class="cmps">{"".join(cards)}</div>')
        if pick:
            t = float(g.get("pick_at") or max(t for _, t, *_ in els) + 0.6)
            other = "r" if pick == "left" else "l"
            picks.append((t, (f"g{gi}{pick[0]}", f"g{gi}{pick[0]}k", [f"g{gi}{other}"]),
                          f"выбор: «{(g.get(pick) or {}).get('title', '')}» зеленеет с галочкой"))
        if g.get("verdict"):
            parts.append(f'<div class="pill ver" id="g{gi}v" style="position:relative">{c.esc(g["verdict"])}</div>')
            els.append((f"g{gi}v", float(g.get("verdict_at") or at + 2.0) - 0.12, f"вывод «{g['verdict']}»"))
    elif kind == "choice":
        items, rows = list(g.get("items", []))[:4], []
        pick = g.get("pick")
        for i, it in enumerate(items):
            h, f = w.item_html(i, it, 46, prefix=f"g{gi}o")
            files += f
            h = h.replace('class="row"', 'class="row opt"', 1)
            h = h[:-len("</div>")] + check_html(f"g{gi}k{i}") + "</div>"
            rows.append(h)
            els.append((f"g{gi}o{i}", float(it.get("at", at + 0.6 + 0.7 * i)) - 0.12, f"вариант «{it.get('title', '')}»"))
        parts.append(f'<div class="list">{"".join(rows)}</div>')
        if pick is not None:
            if not 0 <= int(pick) < len(items):
                raise ValueError(f"choice.pick: номер варианта 0…{len(items) - 1}")
            p = int(pick)
            t = float(g.get("pick_at") or max(t for _, t, *_ in els) + 0.6)
            picks.append((t, (f"g{gi}o{p}", f"g{gi}k{p}", [f"g{gi}o{i}" for i in range(len(items)) if i != p]),
                          f"выбор: «{items[p].get('title', '')}» зеленеет с галочкой"))
        if g.get("verdict"):
            parts.append(f'<div class="pill ver" id="g{gi}v" style="position:relative">{c.esc(g["verdict"])}</div>')
            els.append((f"g{gi}v", float(g.get("verdict_at") or at + 2.0) - 0.12, f"вывод «{g['verdict']}»"))
    html = f'<div class="gw"><div class="grp" id="g{gi}">{"".join(parts)}</div></div>'
    return html, els, picks


def build(slots, theme, kind=None, layout=None):
    layout = layout or DEFAULT_LAYOUT
    s = c.merge_slots(SLOTS, slots)
    pal = c.palette(theme, kind or DEFAULT_KIND)
    b0, b1 = w.blues(pal)
    groups = sorted(list(s["groups"]), key=lambda g: float(g.get("at", 0)))
    pw = int(min(0.75, max(0.5, float(s["panel"]))) * w.WW)
    open_at = float(s["open_at"])
    files, video = [], ""
    html, plan = [], []
    for gi, g in enumerate(groups):
        h, els, picks = group_html(gi, g, files)
        html.append(h)
        plan.append((float(g.get("at", 0)), els, picks))
    last_el = max([t for _, els, _ in plan for _, t, *_ in els] + [t for _, _, picks in plan for t, _, _ in picks]
                  + [open_at + 1.0])
    close = float(s["close_at"]) or (last_el + 3.0)
    dur = close + 0.55 + w.TAIL
    if s["face"]:
        p = Path(str(s["face"])).expanduser()
        if not p.exists():
            raise ValueError(f"видео автора не найдено: {s['face']}")
        if p.suffix.lower() not in VIDEO_EXT:
            raise ValueError(f"face: видео MP4/MOV/WEBM, а не {p.suffix}")
        name = f"face{p.suffix.lower()}"
        files.insert(0, (str(p), name))
        video = (f'<video id="fv" src="{name}" data-start="0" data-duration="{dur:.3f}" '
                 f'data-media-start="{float(s["face_start"]):.3f}" data-track-index="1" muted playsinline></video>')
    left_w = w.WW - pw
    shift = (left_w / 2) - float(s["focus_x"]) * w.WW            # центр лица → в центр левой части
    content = (f'<div id="face">{video}</div>'
               f'<div id="panel" style="width:{pw}px">{"".join(html)}</div>')
    body, bg, size = w.compose(pal, layout, content)
    ease = '"power3.inOut"'
    js = [f'const OK = "{c.rgba(pal["ok"], 1)}", OK_TINT = "{c.rgba(c.mix(c.WHITE, pal["ok"], 0.13), 1)}";',
          f'tl.fromTo("#panel", {{ x: {pw + 80} }}, {{ x: 0, duration: 0.55, ease: {ease} }}, {c.fmt(open_at)});',
          f'tl.fromTo("#face", {{ x: 0 }}, {{ x: {shift:.0f}, duration: 0.55, ease: {ease} }}, {c.fmt(open_at)});']
    events = [c.ev(open_at, "панель выезжает справа, кадр с автором уезжает влево"),
              c.ev(open_at + 0.55, "автор в левой части, панель на месте")]
    sfx = [w.cue(open_at, w.WHOOSH)]
    for gi, (gat, els, picks) in enumerate(plan):
        nxt = plan[gi + 1][0] if gi + 1 < len(plan) else None
        if gi:
            sfx.append(w.cue(gat - 0.1, w.SWISH))
            events.append(c.ev(gat, f"смена группы → {groups[gi].get('type', 'list')}"))
        for eid, t, what, *snd in els:
            t = max(open_at + 0.45, t)
            js.append(f'popIn("#{eid}", {c.fmt(t)});')
            events.append(c.ev(t, what))
            sfx.append(w.cue(t, snd[0] if snd else w.POP))
        for t, (card, check, others), what in picks:
            t = max(open_at + 0.6, t)
            js += pick_js(card, check, others, t)
            events.append(c.ev(t, what))
            sfx.append(w.cue(t, w.SELECT))
        if nxt is not None:
            js.append(f'groupOut("#g{gi}", {c.fmt(nxt - 0.05 - w.EXIT)});')
    js += [f'tl.fromTo("#panel", {{ x: 0 }}, {{ x: {pw + 80}, duration: 0.5, ease: {ease}, immediateRender: false }}, {c.fmt(close)});',
           f'tl.fromTo("#face", {{ x: {shift:.0f} }}, {{ x: 0, duration: 0.5, ease: {ease}, immediateRender: false }}, {c.fmt(close)});']
    events.append(c.ev(close, "панель уезжает, кадр возвращается"))
    sfx.append(w.cue(close, w.WHOOSH))
    style = w.css(pal, layout) + f"""
#face {{ position: absolute; inset: 0; background: {c.background(pal)}; }}
#face video {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
#panel {{ position: absolute; right: 0; top: 0; bottom: 0; background: {c.background(pal)};
  border-radius: 44px 0 0 44px; box-shadow: -30px 0 80px rgba(0, 0, 0, 0.28); }}
.gw {{ position: absolute; left: 110px; right: 110px; top: 50%; transform: translateY(-50%); }}
.rub {{ font-size: 34px; padding: 14px 30px; }}
.pt {{ color: {pal['ink']}; margin: 22px 0 18px; opacity: 0; }}
.row {{ display: flex; align-items: center; gap: 22px; padding: 20px 28px 20px 20px; margin-top: 16px;
  background: {c.WHITE}; border-radius: 24px; color: {pal['ink']}; opacity: 0;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.12), 0 2px 6px rgba(0, 0, 0, 0.06); }}
.msg {{ background: {c.WHITE}; border-radius: 30px; padding: 30px 36px 34px; color: {pal['ink']}; opacity: 0; margin-top: 22px;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.12); }}
.hd {{ display: flex; align-items: center; gap: 16px; font-size: 34px; margin-bottom: 14px; }}
.av {{ width: 66px; height: 66px; border-radius: 50%; background: linear-gradient(135deg, {b0}, {b1}); color: {c.WHITE};
  display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: 800; overflow: hidden; }}
.av img {{ width: 100%; height: 100%; object-fit: cover; }}
.tm {{ margin-left: auto; font-size: 26px; color: {pal['muted']}; font-weight: 600; }}
.tx {{ font-size: 44px; font-weight: 600; line-height: 1.25; }}
.rep {{ margin: 20px 0 0 auto; width: fit-content; max-width: 760px; padding: 22px 32px; border-radius: 28px 28px 8px 28px;
  background: linear-gradient(135deg, {b0}, {b1}); color: {c.WHITE}; font-size: 40px; font-weight: 700; line-height: 1.25; opacity: 0;
  box-shadow: 0 16px 44px {c.rgba(b0, 0.4)}; }}
.num {{ font-family: "ReelDisplay", "ReelMain", sans-serif; font-size: 230px; font-weight: 800; color: {pal['ink']};
  letter-spacing: -0.03em; line-height: 1; margin-top: 10px; opacity: 0; }}
.cap {{ font-size: 40px; color: {pal['ink']}; margin-top: 18px; }}
.cmps {{ display: flex; gap: 26px; margin-top: 10px; }}
.cmp {{ flex: 1; background: {c.WHITE}; border-radius: 28px; padding: 34px 32px; color: {pal['ink']}; opacity: 0;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.12); }}
.cmp .ttl {{ font-size: 46px; }}
.cmp .sub {{ font-size: 30px; margin-top: 10px; }}
.cmp.right {{ outline: 4px solid {c.rgba(b0, 0.55)}; }}
.ver {{ margin-top: 26px; font-size: 36px; background: linear-gradient(135deg, {b0}, {b1}); color: {c.WHITE}; padding: 16px 32px; }}
.withic {{ display: flex; align-items: center; gap: 30px; }}
.tic {{ flex: none; border-radius: 24%; background: {c.WHITE}; display: flex; align-items: center; justify-content: center;
  box-shadow: 0 12px 34px rgba(0, 0, 0, 0.14); }}
.tic img, .tic span {{ width: 66%; height: 66%; object-fit: contain; display: flex; align-items: center; justify-content: center; }}
.cmp {{ position: relative; border: 4px solid transparent; }}
.cic {{ width: 92px; height: 92px; margin-bottom: 18px; display: flex; align-items: center; }}
.cic img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
.cic span {{ font-size: 70px; }}
.opt {{ border: 4px solid transparent; }}
.okc {{ flex: none; width: 66px; height: 66px; margin-left: auto; border-radius: 50%; background: {pal['ok']}; color: {c.WHITE};
  font-size: 40px; font-weight: 900; display: flex; align-items: center; justify-content: center; opacity: 0;
  box-shadow: 0 10px 26px {c.rgba(pal['ok'], 0.45)}; }}
.cmp .okc {{ position: absolute; right: 22px; top: 22px; margin: 0; }}
"""
    kinds = ", ".join(g.get("type", "list") for g in groups)
    describes = f"светлая панель справа ({int(pw / w.WW * 100)} % кадра), автор в левой части; группы: {kinds}"
    return w.result(style, body, js, dur, events, pal, layout, bg, size, files, BASE_TAGS + list(s["tags"]),
                    describes, preview_t=min(dur - 0.3, last_el + 0.4), sfx=sfx)
