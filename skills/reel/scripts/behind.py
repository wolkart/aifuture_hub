"""Задний слой «текст за головой»: тёмная подложка + крупные фразы по словам. Только stdlib.

Опция дорогая (маска человека ~3 мин на 10 с) и у автора разовая, поэтому по умолчанию
выключена. Слой кладётся ПОД вырезанного человека: видео → behind.webm → маска → всё
остальное. Масштаб наезда в этих окнах ≤ 1,04 — текст масштабируется вместе с видео и
иначе вылезает за край (это делает zoom.py по windows.json).

В plan.json:
  "behind_text": [
    {"from": <якорь>, "to": <якорь>|"end", "subs_from": <якорь>?,   ← субтитры вернутся с этого слова
     "phrases": [
       {"lines": [{"size": "l1", "words": [{"text": "Одна", "at": <якорь>}]},
                  {"size": "l2", "words": [{"text": "строка", "at": <якорь>, "color": "secondary"}]}],
        "strike": {"line": 0, "at": <якорь>}}   ← перечеркнуть строку (опционально)
     ]}]
Фраза держится до начала следующей (или до конца окна). size: lead | l1 | l2 | huge.
color: secondary | accent | без цвета (белый).
"""
import html

from hf import clip


def lighten(hex_color, t=0.06):
    h = hex_color.lstrip("#")
    c = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{min(255, round(x + (255 - x) * t)):02X}" for x in c)


def css(theme):
    bg0, bg1 = theme["bg_dark"][0], theme["bg_dark"][-1]
    return f"""
.plate {{ background: radial-gradient(ellipse 85% 60% at 50% 38%, {lighten(bg0)} 0%, {bg0} 30%, {bg1} 85%); opacity: 0; }}
.hero {{ position: absolute; left: 0; right: 0; text-align: center; letter-spacing: -0.02em; line-height: 1; }}
.hero .w {{ display: inline-block; opacity: 0; }}
.lead {{ top: 215px; font-size: 84px; font-weight: 800; }}
.l1 {{ top: 300px; font-size: 112px; font-weight: 800; }}
.l2 {{ top: 425px; font-size: 158px; font-weight: 900; }}
.huge {{ top: 330px; font-family: var(--display); font-weight: 700; font-size: 250px; letter-spacing: 0.01em; }}
.secondary {{ color: {theme["secondary"]}; }} .accent {{ color: {theme["accent"]["solid"]}; }}
.sk {{ position: relative; display: inline-block; }}
.strike {{ position: absolute; left: -10px; right: -10px; top: 50px; height: 10px; background: {theme["accent"]["solid"]};
  border-radius: 5px; transform-origin: left center; }}
"""


def resolve(behind, at, dur):
    """Якоря → секунды. Окно: {a, b, subs_from, phrases: [{a, b, lines: [{size, words: [{text, t, color}]}], strike}]}"""
    out = []
    for win in behind:
        a = at(win.get("from", 0.0))
        b = dur if win.get("to") in (None, "end") else at(win["to"])
        phrases = []
        for ph in win.get("phrases", []):
            lines = [{"size": ln.get("size", "l1"),
                      "words": [{"text": w["text"], "t": at(w.get("at", a)), "color": w.get("color")}
                                for w in ln.get("words", [])]} for ln in ph.get("lines", [])]
            starts = [w["t"] for ln in lines for w in ln["words"]]
            pa = at(ph["from"]) if ph.get("from") is not None else (a if not phrases else min(starts))
            strike = None
            if ph.get("strike"):
                strike = {"line": int(ph["strike"].get("line", 0)), "t": at(ph["strike"]["at"])}
            phrases.append({"a": pa, "lines": lines, "strike": strike})
        for i, ph in enumerate(phrases):
            ph["b"] = phrases[i + 1]["a"] - 0.02 if i + 1 < len(phrases) else b
        subs_from = at(win["subs_from"]) if win.get("subs_from") is not None else b
        out.append({"a": a, "b": b, "subs_from": subs_from, "phrases": phrases})
    return out


def hidden_windows(resolved):
    """Где субтитры не нужны: тот же текст стоит крупно за головой."""
    return [(w["a"] - 0.05, w["subs_from"]) for w in resolved]


def edges(resolved):
    """Начала подложек: страница субтитров, накрывающая начало, обрывается перед ним."""
    return [w["a"] for w in resolved if w["a"] > 0]


def build(resolved, theme):
    """→ (css, body[], js[], windows) — windows: [[a, b]] подложек (маска только в них)."""
    body, js, windows = [], [], []
    for k, win in enumerate(resolved):
        pid = f"plate{k + 1}"
        body.append(clip(pid, win["a"], win["b"], "", 0, "plate"))
        js.append(f'tl.set("#{pid}", {{opacity: 1}}, {win["a"]:.3f});')
        windows.append([round(win["a"], 3), round(win["b"], 3)])
        for j, ph in enumerate(win["phrases"]):
            hid = f"h{k + 1}{chr(97 + j)}"
            rows = []
            for li, ln in enumerate(ph["lines"]):
                parts = []
                for wi, w in enumerate(ln["words"]):
                    cls = f'w {w["color"]}' if w["color"] else "w"
                    parts.append(f'<span class="{cls}" id="{hid}w{li}{wi}">{html.escape(w["text"])}</span>')
                spans = " ".join(parts)
                if ph["strike"] and ph["strike"]["line"] == li:
                    spans = f'<span class="sk">{spans}<i class="strike"></i></span>'
                rows.append(f'<div class="hero {ln["size"]}">{spans}</div>')
            body.append(clip(hid, ph["a"], ph["b"], "".join(rows), 1))
            for li, ln in enumerate(ph["lines"]):
                for wi, w in enumerate(ln["words"]):
                    js.append(f'tl.fromTo("#{hid}w{li}{wi}", {{opacity: 0, y: 34, scale: 0.92, filter: "blur(14px)"}}, '
                              f'{{opacity: 1, y: 0, scale: 1, filter: "blur(0px)", duration: 0.2, ease: "power3.out"}}, '
                              f'{w["t"]:.3f});')
            if ph["strike"]:
                js.append(f'tl.fromTo("#{hid} .strike", {{scaleX: 0}}, {{scaleX: 1, duration: 0.22, '
                          f'ease: "power2.inOut"}}, {ph["strike"]["t"]:.3f});')
            js.append(f'tl.to("#{hid} .hero", {{opacity: 0, filter: "blur(10px)", duration: 0.1, '
                      f'ease: "power1.in"}}, {ph["b"] - 0.1:.3f});')
    return css(theme), body, js, windows
