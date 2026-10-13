"""Карточки переднего слоя: типовые шаблоны со слотами. Только stdlib.

Карточка — это то, что ставится на ключевое слово, когда подходящего б-ролла или
ассета нет. Шаблоны сняты с прототипа (рилс собирался руками, у каждой карточки свой
код) и обобщены: текст — слотами, моменты — якорями на слова (см. words.at).

В plan.json:
  {"kind": "card", "template": "tiles", "from": <якорь>, "to": <якорь>, "slots": {...}}
Слоты и пример каждого шаблона — references/cards.md. Цвета — только из темы автора.
Все анимации seek-safe: fromTo/to по transform/opacity/цвету, селекторы по id.
"""
import html
from pathlib import Path

from hf import rgb


def mix(a, b, t):
    """Смешать два hex-цвета: t=0 → a, t=1 → b."""
    ha, hb = a.lstrip("#"), b.lstrip("#")
    ca = [int(ha[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(hb[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def esc(text):
    return html.escape(str(text))


def icon_html(icon, size):
    """Иконка слотом: эмодзи/символ или путь к .svg (вставляется инлайн)."""
    if not icon:
        return ""
    p = Path(str(icon)).expanduser()
    if p.suffix.lower() == ".svg" and p.exists():
        sized = f'<svg width="{size}" height="{size}"'
        svg = p.read_text(encoding="utf-8").replace("<svg", sized, 1)
        return f'<span style="display:inline-block; width:{size}px; height:{size}px">{svg}</span>'
    return f'<span style="font-size:{int(size * 0.8)}px; line-height:1">{esc(icon)}</span>'


def css(theme):
    acc, sec, mut, ok = (theme["accent"]["solid"], theme["secondary"], theme["muted"], theme["success"])
    panel = mix(theme["bg_dark"][0], theme["bg_dark"][-1], 0.5)
    light = mix(sec, "#FFFFFF", 0.82)
    return f"""
.card {{ position: absolute; left: 60px; right: 60px; top: 190px; padding: 34px 40px; border-radius: 34px;
  background: rgba({rgb(panel)}, 0.88); border: 1.5px solid rgba({rgb(sec)}, 0.28);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.5); opacity: 0; }}
.ttl {{ font-size: 44px; font-weight: 800; letter-spacing: -0.01em; }}
.sub {{ font-size: 28px; font-weight: 500; color: {mut}; margin-top: 6px; }}
.row {{ display: flex; align-items: center; gap: 16px; }}
.chip {{ display: inline-flex; align-items: center; gap: 10px; padding: 12px 22px; border-radius: 999px; font-size: 30px;
  font-weight: 600; background: rgba({rgb(sec)}, 0.16); border: 1.5px solid rgba({rgb(sec)}, 0.45); color: {light}; opacity: 0; }}
.chip.c {{ background: rgba({rgb(acc)}, 0.16); border-color: rgba({rgb(acc)}, 0.5); color: {mix(acc, "#FFFFFF", 0.8)}; }}
.lbl {{ font-size: 30px; font-weight: 700; color: {light}; opacity: 0; }}
.dot {{ width: 18px; height: 18px; border-radius: 50%; background: {sec}; display: inline-block; }}
.tiles {{ display: flex; gap: 22px; justify-content: center; }}
.tile {{ position: relative; width: 280px; height: 230px; border-radius: 26px; background: rgba(255,255,255,0.05);
  border: 1.5px solid rgba(255,255,255,0.1); display: flex; flex-direction: column; align-items: center;
  justify-content: center; opacity: 0; }}
.tile .ic {{ font-family: var(--display); font-size: 96px; font-weight: 700; line-height: 1; }}
.tile .tl {{ font-size: 32px; font-weight: 700; margin-top: 14px; color: #E6E6F2; }}
.tile .xw {{ position: absolute; left: 46px; right: 46px; top: 84px; height: 10px; transform: rotate(-20deg); }}
.tile .x {{ width: 100%; height: 100%; border-radius: 5px; background: {acc}; transform-origin: left center; }}
.tile.ok {{ border-color: rgba({rgb(sec)},0.6); background: rgba({rgb(sec)},0.12); }}
.tile.ok .ic {{ color: {sec}; }}
.term {{ padding: 0; overflow: hidden; }}
.term .bar {{ display: flex; gap: 12px; padding: 22px 28px; background: rgba(255,255,255,0.05); align-items: center; }}
.term .bar i {{ width: 20px; height: 20px; border-radius: 50%; display: inline-block; }}
.term .bar span {{ font-family: Menlo, monospace; font-size: 24px; color: {mut}; margin-left: 14px; }}
.term .body {{ padding: 26px 32px 34px; font-family: Menlo, monospace; font-size: 31px; line-height: 1.5; }}
.term .cmd {{ word-break: break-all; color: #E8E8F5; }}
.term .cmd .p {{ color: {ok}; }}
.term .cmd .ch {{ opacity: 0; }}
.term .out {{ color: {mut}; opacity: 0; }}
.term .ok {{ color: {ok}; font-weight: 700; }}
.ava {{ width: 120px; height: 120px; border-radius: 50%; background: linear-gradient(135deg, {sec}, {acc});
  display: flex; align-items: center; justify-content: center; font-size: 56px; flex: none; }}
.pill {{ margin-left: auto; padding: 14px 26px; border-radius: 999px; background: rgba({rgb(ok)},0.16);
  border: 1.5px solid rgba({rgb(ok)},0.55); color: {ok}; font-size: 30px; font-weight: 800; opacity: 0; }}
.blk {{ border-radius: 22px; padding: 22px 26px; background: rgba(255,255,255,0.05); }}
.bar2 {{ height: 18px; border-radius: 9px; background: rgba(255,255,255,0.16); margin-top: 14px; }}
.ai {{ display: flex; justify-content: center; margin: 18px 0; opacity: 0; }}
.ai span {{ padding: 12px 30px; border-radius: 999px; font-size: 30px; font-weight: 800;
  background: linear-gradient(90deg, {sec}, {mix(sec, acc, 0.35)}); }}
.typed {{ font-size: 29px; font-weight: 600; line-height: 1.35; margin-top: 10px; }}
.typed .ch {{ opacity: 0; }}
.sched .r {{ display: flex; align-items: center; gap: 26px; padding: 18px 6px; border-top: 1.5px solid rgba(255,255,255,0.07); opacity: 0; }}
.sched .tm {{ font-family: Menlo, monospace; font-size: 42px; font-weight: 700; width: 140px; }}
.sched .st {{ font-size: 36px; font-weight: 600; }}
.two {{ display: flex; gap: 22px; }}
.half {{ flex: 1; border-radius: 26px; padding: 30px; background: rgba(255,255,255,0.05); opacity: 0; text-align: center; }}
.half .big {{ font-size: 120px; line-height: 1.1; }}
.half .h {{ font-size: 42px; font-weight: 800; margin-top: 8px; }}
.half .s {{ font-size: 32px; font-weight: 600; margin-top: 8px; }}
.msg {{ font-size: 32px; font-weight: 600; line-height: 1.4; }}
.kb {{ display: flex; gap: 14px; margin-top: 22px; }}
.btn {{ flex: 1; padding: 22px 10px; border-radius: 18px; text-align: center; font-size: 34px; font-weight: 700;
  background: rgba(255,255,255,0.08); border: 1.5px solid rgba(255,255,255,0.08); opacity: 0; }}
"""


class Ctx:
    """Общее для шаблонов: время по якорю, накопитель js, цвета темы."""

    def __init__(self, at, theme):
        self.at, self.theme, self.js = at, theme, []
        self.light = mix(theme["secondary"], "#FFFFFF", 0.82)  # светлый текст в тон вторичного

    def card_in_out(self, cid, a, b):
        self.js.append(f'tl.fromTo("#{cid} .card", {{opacity: 0, y: -24, scale: 0.96}}, {{opacity: 1, y: 0, '
                       f'scale: 1, duration: 0.26, ease: "power3.out"}}, {a:.3f});')
        self.js.append(f'tl.to("#{cid} .card", {{opacity: 0, y: -14, duration: 0.16, ease: "power1.in"}}, '
                       f'{b - 0.16:.3f});')

    def pop(self, sel, at, dur=0.22, frm="{opacity: 0, y: 14, scale: 0.9}"):
        self.js.append(f'tl.fromTo("{sel}", {frm}, {{opacity: 1, y: 0, scale: 1, duration: {dur}, '
                       f'ease: "back.out(1.7)"}}, {at:.3f});')

    def slide(self, sel, at, dx=-14, dur=0.18):
        self.js.append(f'tl.fromTo("{sel}", {{opacity: 0, x: {dx}}}, {{opacity: 1, x: 0, duration: {dur}}}, {at:.3f});')

    def fade(self, sel, at, dur=0.2):
        self.js.append(f'tl.fromTo("{sel}", {{opacity: 0}}, {{opacity: 1, duration: {dur}}}, {at:.3f});')

    def type_on(self, sel, text, t0, t1):
        stagger = max(0.001, (t1 - t0) / max(1, len(text)))
        self.js.append(f'tl.to("{sel} .ch", {{opacity: 1, duration: 0.01, stagger: {stagger:.4f}}}, {t0:.3f});')


def typed(text):
    return "".join(f'<span class="ch">{esc(c)}</span>' for c in text)


def t_tiles(cid, a, b, s, c):
    """Плитки-варианты: зачёркнутые («без кода», «без редактора») и одна «да» («бесплатно»)."""
    tiles = []
    for it in s["items"]:
        x = '<div class="xw"><div class="x"></div></div>' if it.get("crossed") else ""
        cls = "tile ok" if it.get("ok") else "tile"
        tiles.append(f'<div class="{cls}"><div class="ic">{esc(it.get("icon", ""))}</div>'
                     f'<div class="tl">{esc(it.get("label", ""))}</div>{x}</div>')
    c.card_in_out(cid, a, b)
    for i, it in enumerate(s["items"]):
        t = c.at(it.get("at")) if it.get("at") is not None else a + 0.2 + 0.3 * i
        c.pop(f"#{cid} .tile:nth-child({i + 1})", t)
        if it.get("crossed"):
            c.js.append(f'tl.fromTo("#{cid} .tile:nth-child({i + 1}) .x", {{scaleX: 0}}, {{scaleX: 1, '
                        f'duration: 0.2, ease: "power2.out"}}, {t + 0.35:.3f});')
            c.js.append(f'tl.to("#{cid} .tile:nth-child({i + 1}) .ic, #{cid} .tile:nth-child({i + 1}) .tl", '
                        f'{{opacity: 0.35, duration: 0.18}}, {t + 0.4:.3f});')
    return f'<div class="card"><div class="tiles">{"".join(tiles)}</div></div>'


def t_terminal(cid, a, b, s, c):
    """Терминал: команда печатается, строки вывода появляются по словам."""
    cmd = s.get("command", "")
    lines = s.get("lines", [])
    outs = "".join(f'<div class="out" id="{cid}o{i}">'
                   + (f'<span class="ok">{esc(ln["text"])}</span>' if ln.get("ok") else esc(ln["text"]))
                   + "</div>" for i, ln in enumerate(lines))
    dots = "".join(f'<i style="background:{col}"></i>' for col in ("#FF5F57", "#FEBC2E", "#28C840"))
    c.card_in_out(cid, a, b)
    t0 = c.at(s["type_from"]) if s.get("type_from") is not None else a + 0.15
    t1 = c.at(s["type_to"]) if s.get("type_to") is not None else t0 + min(1.5, 0.03 * len(cmd))
    c.type_on(f"#{cid} .cmd", cmd, t0, t1)
    for i, ln in enumerate(lines):
        c.slide(f"#{cid}o{i}", c.at(ln["at"]), dx=-12, dur=0.14)
    return (f'<div class="card term"><div class="bar">{dots}<span>{esc(s.get("title", "terminal"))}</span></div>'
            f'<div class="body"><div class="cmd"><span class="p">$ </span>{typed(cmd)}</div>{outs}</div></div>')


def t_profile(cid, a, b, s, c):
    """Профиль: иконка + название + подпись + плашка-статус («✓ Готов»)."""
    c.js.append(f'tl.fromTo("#{cid} .card", {{opacity: 0, scale: 0.85}}, {{opacity: 1, scale: 1, duration: 0.3, '
                f'ease: "back.out(2)"}}, {a:.3f});')
    c.js.append(f'tl.to("#{cid} .card", {{opacity: 0, duration: 0.12}}, {b - 0.12:.3f});')
    pill = ""
    if s.get("pill"):
        pill = f'<div class="pill" style="font-size:34px">{esc(s["pill"])}</div>'
        c.pop(f"#{cid} .pill", c.at(s["pill_at"]) if s.get("pill_at") is not None else a + 0.4)
    return (f'<div class="card" style="padding:44px 46px"><div class="row" style="gap:26px">'
            f'<div style="flex:none">{icon_html(s.get("icon"), 150)}</div>'
            f'<div><div class="ttl" style="font-size:58px">{esc(s.get("title", ""))}</div>'
            f'<div class="sub" style="font-size:32px">{esc(s.get("subtitle", ""))}</div></div>{pill}</div></div>')


def t_chips(cid, a, b, s, c):
    """Группы чипов: заголовок, под ним группы «подпись + чипы» (источники, теги, списки)."""
    c.card_in_out(cid, a, b)
    sub = ""
    if s.get("subtitle"):
        sub = f'<div class="sub" style="opacity:0">{esc(s["subtitle"])}</div>'
        c.js.append(f'tl.fromTo("#{cid} .sub", {{opacity: 0}}, {{opacity: 1, duration: 0.2}}, '
                    f'{c.at(s.get("subtitle_at")) if s.get("subtitle_at") is not None else a + 0.3:.3f});')
    groups = []
    for g_i, g in enumerate(s.get("groups", [])):
        gid = f"{cid}g{g_i}"
        mark = (icon_html(g["icon"], 38) if g.get("icon")
                else f'<span class="dot" style="background:{c.theme["accent"]["solid"] if g.get("accent") else c.theme["secondary"]}"></span>&nbsp;')
        chips = "".join(f'<span class="chip{" c" if g.get("accent") else ""}">{esc(ch["text"])}</span>'
                        for ch in g.get("chips", []))
        groups.append(f'<div id="{gid}" style="margin-top:{28 if g_i == 0 else 30}px">'
                      f'<div class="lbl" style="display:flex; align-items:center; gap:12px">{mark}{esc(g.get("label", ""))}</div>'
                      f'<div class="row" style="margin-top:16px; flex-wrap:wrap">{chips}</div></div>')
        lt = c.at(g["label_at"]) if g.get("label_at") is not None else a + 0.3 + g_i * 0.8
        c.slide(f"#{gid} .lbl", lt)
        for i, ch in enumerate(g.get("chips", [])):
            c.pop(f"#{gid} .chip:nth-child({i + 1})", c.at(ch["at"]) if ch.get("at") is not None else lt + 0.2 * (i + 1))
    return f'<div class="card"><div class="ttl">{esc(s.get("title", ""))}</div>{sub}{"".join(groups)}</div>'


def t_rewrite(cid, a, b, s, c):
    """Было → ИИ → стало: серые строки источника, бейдж, печатающийся новый текст."""
    acc = c.theme["accent"]["solid"]
    text = s.get("text", "")
    c.card_in_out(cid, a, b)
    c.pop(f"#{cid} .ai", c.at(s["badge_at"]) if s.get("badge_at") is not None else a + 0.3)
    t0 = c.at(s["text_at"]) if s.get("text_at") is not None else a + 0.6
    c.pop(f"#{cid}new", t0, frm="{opacity: 0, y: 20, scale: 0.97}")
    t1 = c.at(s["type_to"]) if s.get("type_to") is not None else t0 + 1.2
    c.type_on(f"#{cid}new .typed", text, t0 + 0.15, t1)
    bars = "".join(f'<div class="bar2" style="width:{w}%"></div>' for w in (92, 78, 86, 52))
    return (f'<div class="card"><div class="ttl" style="font-size:38px; margin-bottom:22px">{esc(s.get("title", ""))}</div>'
            f'<div class="row" style="align-items:stretch; gap:14px">'
            f'<div class="blk" style="flex:1"><div class="sub" style="margin:0">{esc(s.get("source_label", ""))}</div>{bars}</div>'
            f'<div class="ai" style="margin:0; align-items:center"><span style="padding:12px 18px">{esc(s.get("badge", "ИИ →"))}</span></div>'
            f'<div class="blk" style="flex:1.25; border:1.5px solid rgba({rgb(acc)},0.5); opacity:0" id="{cid}new">'
            f'<div class="sub" style="margin:0; color:{acc}">{esc(s.get("target_label", ""))}</div>'
            f'<div class="typed">{typed(text)}</div></div></div></div>')


def t_rows(cid, a, b, s, c):
    """Строки-статусы: «09:00 ✓ опубликовано», «19:00 ◷ в очереди»."""
    c.card_in_out(cid, a, b)
    rows = []
    for i, r in enumerate(s.get("rows", [])):
        col = c.theme["success"] if r.get("state", "ok") == "ok" else c.theme["secondary"]
        rows.append(f'<div class="r" id="{cid}r{i}"><span class="tm">{esc(r.get("left", ""))}</span>'
                    f'<span class="st" style="color:{col}">{esc(r.get("right", ""))}</span></div>')
        c.slide(f"#{cid}r{i}", c.at(r["at"]) if r.get("at") is not None else a + 0.3 + 0.3 * i, dx=-16)
    return (f'<div class="card sched"><div class="ttl" style="margin-bottom:14px">{esc(s.get("title", ""))}</div>'
            f'{"".join(rows)}</div>')


def t_compare(cid, a, b, s, c):
    """Две половины: «Сервер — онлайн 24/7» против «Компьютер — можно выключить»."""
    c.card_in_out(cid, a, b)
    halves = []
    for i, it in enumerate(s.get("items", [])[:2]):
        dim = it.get("state") == "dim"
        col = c.theme["muted"] if dim else c.theme["success"]
        big_style = ' style="opacity:0.5"' if dim else ""
        halves.append(f'<div class="half"><div class="big"{big_style}>'
                      f'{esc(it.get("icon", ""))}</div><div class="h">{esc(it.get("title", ""))}</div>'
                      f'<div class="s" style="color:{col}">{esc(it.get("note", ""))}</div></div>')
        t = c.at(it["at"]) if it.get("at") is not None else a + 0.12 + 0.6 * i
        c.pop(f"#{cid} .half:nth-child({i + 1})", t)
        if it.get("note_at") is not None:
            c.fade(f"#{cid} .half:nth-child({i + 1}) .s", c.at(it["note_at"]))
    return f'<div class="card"><div class="two">{"".join(halves)}</div></div>'


def t_buttons(cid, a, b, s, c):
    """Окно бота: аватар, сообщение, кнопки нажимаются по словам."""
    sec = c.theme["secondary"]
    c.card_in_out(cid, a, b)
    show = c.at(s["show_at"]) if s.get("show_at") is not None else a + 0.12
    c.js.append(f'tl.to("#{cid} .btn", {{opacity: 1, duration: 0.16, stagger: 0.09}}, {max(show, a + 0.12):.3f});')
    btns = []
    for i, bt in enumerate(s.get("buttons", [])):
        btns.append(f'<div class="btn">{esc(bt["text"])}</div>')
        if bt.get("press_at") is not None:
            t = c.at(bt["press_at"])
            c.js.append(f'tl.to("#{cid} .btn:nth-child({i + 1})", {{scale: 0.95, backgroundColor: '
                        f'"rgba({rgb(sec)},0.55)", borderColor: "{sec}", duration: 0.09}}, {t:.3f});')
            c.js.append(f'tl.to("#{cid} .btn:nth-child({i + 1})", {{scale: 1, backgroundColor: '
                        f'"rgba({rgb(sec)},0.22)", duration: 0.2}}, {t + 0.1:.3f});')
    hint = f' <span style="color:{c.theme["muted"]}">{esc(s["hint"])}</span>' if s.get("hint") else ""
    return (f'<div class="card"><div class="row"><div class="ava" style="width:84px;height:84px;font-size:40px">'
            f'{esc(s.get("avatar", ""))}</div><div><div class="ttl" style="font-size:38px">{esc(s.get("title", ""))}</div>'
            f'<div class="sub" style="margin-top:2px">{esc(s.get("subtitle", ""))}</div></div></div>'
            f'<div class="msg" style="margin-top:20px">{esc(s.get("message", ""))}{hint}</div>'
            f'<div class="kb">{"".join(btns)}</div></div>')


def t_cta(cid, a, b, s, c):
    """Финал: «Напиши в комменты» + крупное кодовое слово + что пришлю."""
    c.js.append(f'tl.fromTo("#{cid} .card", {{opacity: 0, scale: 0.9, y: -20}}, {{opacity: 1, scale: 1, y: 0, '
                f'duration: 0.3, ease: "back.out(1.8)"}}, {a:.3f});')
    sub = ""
    if s.get("sub"):
        sub = (f'<div class="sub" style="font-size:32px; margin-top:4px; opacity:0" id="{cid}s">'
               f'{esc(s["sub"])}</div>')
        c.fade(f"#{cid}s", c.at(s["sub_at"]) if s.get("sub_at") is not None else a + 0.6, dur=0.25)
    return (f'<div class="card" style="text-align:center; padding:30px 40px 36px">'
            f'<div class="sub" style="font-size:36px; color:{c.light}; margin:0">{esc(s.get("lead", ""))}</div>'
            f'<div style="font-family:var(--display); font-weight:700; font-size:{int(s.get("size", 190))}px; '
            f'line-height:1.05; color:{c.theme["accent"]["solid"]}; letter-spacing:0.01em">{esc(s.get("word", ""))}</div>'
            f'{sub}</div>')


TEMPLATES = {"tiles": t_tiles, "terminal": t_terminal, "profile": t_profile, "chips": t_chips,
             "rewrite": t_rewrite, "rows": t_rows, "compare": t_compare, "buttons": t_buttons, "cta": t_cta}


def build(cards, at, theme, track=1):
    """cards: [{"id"?, "template", "a", "b", "slots", "top"?}] с уже посчитанными a/b.
    → (css, body[], js[])"""
    c = Ctx(at, theme)
    body = []
    for i, cd in enumerate(cards):
        cid = cd.get("id") or f"c{i + 1}"
        fn = TEMPLATES.get(cd["template"])
        if fn is None:
            raise ValueError(f"карточка {cid}: нет шаблона «{cd['template']}» (есть: {', '.join(TEMPLATES)})")
        inner = fn(cid, cd["a"], cd["b"], cd.get("slots") or {}, c)
        if cd.get("top") is not None:
            inner = inner.replace('<div class="card', f'<div style="position:absolute; inset:0; transform:'
                                  f'translateY({int(cd["top"]) - 190}px)"><div class="card', 1) + "</div>"
        body.append(f'<div id="{cid}" class="clip" data-start="{cd["a"]:.3f}" '
                    f'data-duration="{cd["b"] - cd["a"]:.3f}" data-track-index="{track}">{inner}</div>')
    return css(theme), body, c.js
