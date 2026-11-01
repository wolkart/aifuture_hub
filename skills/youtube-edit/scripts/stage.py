"""Каркас сцен длинного ролика 16:9 — HyperFrames 1920×1080, время по словам таймлайна.

Вынесено из ролика news-reposter (story16 / inserts16 / beats16 / panels, 2026-10-19): то, что
там ловили глаза автора, здесь делает каркас.

  • время — по словам (`at(фраза, слово)`), а не секундами: правка резки сдвигает всё само;
    вырезанное слово-якорь → ближайшее уцелевшее, случай — в отчёт (`WORDS.misses`);
  • `out()` уводит элемент от ТЕКУЩЕЙ прозрачности (`tl.to`): с `fromTo(opacity 1)` финальный
    уход всех id проявлял на 0,25 с то, что ушло раньше, — «вспышка» в конце каждой вставки;
  • `fitted` — вставка начинается за ~0,35 с до своего первого элемента («три секунды
    тонировка — сидишь, ждёшь»);
  • `idle_gaps` — паузы внутри сцены по её JS («картинка висит и ждёт следующей анимации»);
    закрываются действиями на слова: `mark` / `wave` / `shake` / `chip`;
  • `cursorTo(sel)` — курсор кончиком в центр элемента по разметке («мышка кликнула мимо»);
  • вся сцена медленно наезжает (+3,5 %) — «всё время в движении»;
  • вид `over` — поверх экрана: прозрачный клип с вуалью, под ним живая запись (V1), а не
    впечатанный кусок; `place=LEFT` — графику правой колонки целиком влево («всё ушло вправо»).

Сцены ролика пишутся в export/монтаж/scenes.py (образец — assets/scenes.example.py):

    from stage import *
    def install():
        s = Ins("install", at(91, "одной") - 0.3, "full", what="«1 команда» → терминал → бот")
        ...
        return s.done(s.t(95, "бесплатно", 1, 0.8))
    SCENES = [install, ...]

Собирает и рендерит build.py; правила ремесла — references/scene-craft.md.
"""
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REEL = HERE.parents[1] / "reel" / "scripts"
sys.path.insert(0, str(REEL))
import hf        # noqa: E402  (reel)
import settings as settings_mod  # noqa: E402  (reel)

W, H = 1920, 1080
DANGER = "#E5484D"
GREEN = "#1F8A55"
FOCUS_X = 0.47              # лицо в кадре головы по горизонтали (замер news-reposter) — панели wide_drawer
LEAD = {}                   # имя → насколько позже начать (fitted)
_S = {"theme": None, "settings": None, "raw": {}, "logos": None, "work": None}


# ── время слов ──────────────────────────────────────────────────────────────

def _norm(w):
    return re.sub(r"[^\wё]", "", str(w).lower().replace("ё", "е"))


class Words:
    """Фразы таймлайна (timeline.py words): [{n, a, b, text, words: [[текст, начало|None, конец|None]]}]."""

    def __init__(self, phrases):
        self.order = [p["n"] for p in phrases]
        self.phr = {p["n"]: p for p in phrases}
        self.misses = []              # (фраза, слово, текст, чем заменено)

    def k(self, n, needle=0):
        """Номер слова фразы n: число — как есть (за концом — последнее); строка — первое слово,
        начинающееся с неё, иначе первое, где она внутри («нас-настраивал»)."""
        ws = self.phr[n]["words"]
        if isinstance(needle, int):
            return min(needle, len(ws) - 1) if needle >= 0 else len(ws) + needle
        nd = _norm(needle)
        for i, w in enumerate(ws):
            if _norm(w[0]).startswith(nd):
                return i
        for i, w in enumerate(ws):
            if nd in _norm(w[0]):
                return i
        raise KeyError(f"во фразе {n} нет слова «{needle}»: {' '.join(w[0] for w in ws)}")

    def last(self, n):
        return len(self.phr[n]["words"]) - 1

    def _flat(self):
        for n in self.order:
            for i, w in enumerate(self.phr[n]["words"]):
                yield n, i, w

    def t(self, n, k=0, edge=0):
        """Секунда таймлайна слова k фразы n (edge 0 — начало, 1 — конец). Вырезано → ближайшее
        уцелевшее (сначала предыдущее — его конец, потом следующее — его начало)."""
        i = self.k(n, k)
        w = self.phr[n]["words"][i]
        if w[1 + edge] is not None:
            return w[1 + edge]
        flat = list(self._flat())
        j = next(x for x, (nn, ii, _) in enumerate(flat) if nn == n and ii == i)
        prev = next((x for x in range(j - 1, -1, -1) if flat[x][2][2] is not None), None)
        nxt = next((x for x in range(j + 1, len(flat)) if flat[x][2][1] is not None), None)
        if prev is None and nxt is None:
            raise KeyError("в words.json нет ни одного уцелевшего слова")
        use_prev = prev is not None and (nxt is None or j - prev <= nxt - j)
        pn, pi, pw = flat[prev if use_prev else nxt]
        self.misses.append((n, i, w[0], f"{'конец' if use_prev else 'начало'} «{pw[0]}» ({pn}, {pi})"))
        return pw[2] if use_prev else pw[1]

    def said(self, a, b):
        """Что звучит на таймлайне в [a, b) — для отчёта пауз."""
        return " ".join(w[0] for _, _, w in self._flat() if w[1] is not None and a - 0.2 <= w[1] < b)


WORDS = Words([])


def at(n, k=0, edge=0, d=0.0):
    """Секунда таймлайна слова (фраза n, слово k — номер или начало слова) + сдвиг d."""
    return round(WORDS.t(n, k, edge) + d, 3)


def last(n):
    return WORDS.last(n)


# ── настройки и тема ────────────────────────────────────────────────────────

def init(work, settings_path=None):
    """Рабочая папка (export/монтаж) → слова, тема автора, логотипы. Вызывает build.py до импорта scenes.py."""
    global WORDS
    work = Path(work)
    _S["work"] = work
    wp = work / "words.json"
    WORDS = Words(json.loads(wp.read_text(encoding="utf-8")) if wp.exists() else [])
    sp = settings_mod.find(settings_path)
    sp = sp if sp and Path(sp).exists() else None
    s = settings_mod.load(str(sp)) if sp else settings_mod.default()
    raw = json.loads(Path(sp).read_text(encoding="utf-8")) if sp else {}
    _S.update(theme=s["theme"], settings=sp, raw=raw.get("ютуб", {}) or {})
    lib = (s.get("folders") or {}).get("library")
    logos = _S["raw"].get("логотипы")
    logos = (Path(sp).parent / Path(logos).expanduser()) if logos else (Path(lib) / "_логотипы" if lib else None)
    _S["logos"] = logos
    _theme_globals()
    return WORDS


def theme():
    return _S["theme"] or settings_mod.default()["theme"]


def settings_path():
    return _S["settings"]


def section():
    """Раздел «ютуб» настроек автора."""
    return _S["raw"]


def _theme_globals():
    global INK, SEC, MUTED, OK, BASE_CSS
    th = theme()
    INK, SEC, MUTED, OK = th["text_dark"], th["secondary"], th["muted"], th["success"]
    BASE_CSS = _base_css(th)


def _base_css(th):
    ink, ok = th["text_dark"], th["success"]
    light = th["bg_light"][1] if isinstance(th.get("bg_light"), (list, tuple)) else "#E0E9FF"
    return f"""
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; }}
body {{ font-family: "ReelMain", sans-serif; color: {ink}; }}
.bg {{ position: absolute; inset: 0; background: radial-gradient(ellipse 80% 70% at 50% 42%, #FFFFFF 0%, {light} 100%); }}
.ui {{ font-family: -apple-system, "SF Pro Text", "Helvetica Neue", system-ui, sans-serif; }}
.mono {{ font-family: "SF Mono", Menlo, Monaco, monospace; }}
.abs {{ position: absolute; }}
.win {{ position: absolute; border-radius: 22px; overflow: hidden; box-shadow: 0 40px 100px rgba(20, 24, 60, 0.22), 0 0 0 1px rgba(0,0,0,0.06); opacity: 0; }}
.tl {{ display: flex; gap: 10px; }} .tl i {{ width: 15px; height: 15px; border-radius: 50%; display: block; }}
.tl i:nth-child(1) {{ background: #FF5F57; }} .tl i:nth-child(2) {{ background: #FEBC2E; }} .tl i:nth-child(3) {{ background: #28C840; }}
.pill {{ position: absolute; display: inline-flex; align-items: center; gap: 12px; padding: 14px 26px; border-radius: 999px;
  background: #fff; color: {ink}; font-weight: 700; font-size: 30px; white-space: nowrap; box-shadow: 0 16px 40px rgba(20,24,60,.16); opacity: 0; }}
.bchip {{ position: absolute; display: inline-flex; align-items: center; gap: 10px; padding: 12px 24px; border-radius: 999px; background: #fff;
  font-weight: 700; white-space: nowrap; box-shadow: 0 14px 36px rgba(20,24,60,.18); opacity: 0; z-index: 30; color: {ink}; }}
.cursor {{ position: absolute; left: 0; top: 0; opacity: 0; z-index: 50; }}
.ch {{ opacity: 0; }}
.opt {{ border: 4px solid transparent; }}
.okc {{ position: absolute; right: 22px; top: 50%; margin-top: -33px; width: 66px; height: 66px; border-radius: 50%; background: {ok};
  color: #fff; font-size: 40px; font-weight: 900; display: flex; align-items: center; justify-content: center; opacity: 0;
  box-shadow: 0 10px 26px rgba(91, 208, 138, 0.45); z-index: 5; }}
.key {{ display: inline-flex; align-items: center; justify-content: center; min-width: 110px; height: 110px; padding: 0 26px; border-radius: 22px;
  background: #fff; color: {ink}; font-size: 44px; font-weight: 800; box-shadow: 0 8px 0 #C9CEDD, 0 18px 40px rgba(20,24,60,.18); opacity: 0; }}
.big {{ position: absolute; font-family: "ReelDisplay", "ReelMain", sans-serif; font-weight: 800; color: {ink}; letter-spacing: -0.03em;
  line-height: 1; opacity: 0; white-space: nowrap; }}
"""


INK = SEC = MUTED = OK = BASE_CSS = None
_theme_globals()

JS_BASE = """const popIn = (sel, at, d = 0.26) => tl.fromTo(sel,
  { opacity: 0, y: 16, scale: 0.96, filter: "blur(12px)" },
  { opacity: 1, y: 0, scale: 1, filter: "blur(0px)", duration: d, ease: "power3.out" }, at);
// от текущей прозрачности (to, а не fromTo с opacity 1): финальный out всех id не проявляет на 0,25 с то, что ушло раньше
const out = (sel, at, d = 0.2) => tl.to(sel, { opacity: 0, filter: "blur(10px)", duration: d, ease: "power2.in", lazy: false }, at);
const fade = (sel, at, d = 0.2) => tl.fromTo(sel, { opacity: 0 }, { opacity: 1, duration: d }, at);
const moveTo = (sel, at, x, y, d = 0.5) => tl.to(sel, { x: x, y: y, duration: d, ease: "power2.inOut" }, at);
const click = (sel, at) => { tl.to(sel, { scale: 0.86, duration: 0.07 }, at); tl.to(sel, { scale: 1, duration: 0.1 }, at + 0.07); };
// курсор кончиком стрелки — в центр элемента по разметке (offsetLeft/Top: без GSAP-сдвигов), а не по ручным координатам
const center = (sel) => { let el = document.querySelector(sel), x = el.offsetWidth / 2, y = el.offsetHeight / 2;
  while (el) { x += el.offsetLeft; y += el.offsetTop; el = el.offsetParent; } return [x, y]; };
const cursorTo = (sel, at, d = 0.5) => { const [x, y] = center(sel); tl.to("#cur", { x: x - 8, y: y - 3, duration: d, ease: "power2.inOut" }, at); };
const pick = (card, check, others, at) => {
  tl.to(card, { borderColor: "#5BD08A", backgroundColor: "#E7F8EE", duration: 0.22, ease: "power2.out" }, at);
  tl.fromTo(check, { opacity: 0, scale: 0.3 }, { opacity: 1, scale: 1, duration: 0.32, ease: "back.out(2.6)" }, at);
  if (others) tl.to(others, { opacity: 0.42, filter: "grayscale(1)", duration: 0.25 }, at); };
const mark = (sel, at) => { tl.to(sel, { scale: 1.06, duration: 0.14, ease: "power2.out", yoyo: true, repeat: 1 }, at);
  tl.fromTo(sel, { outline: "0px solid rgba(102,149,241,0)" }, { outline: "8px solid rgba(102,149,241,0.45)", duration: 0.16,
    yoyo: true, repeat: 1, immediateRender: false }, at); };
const shake = (sel, at) => tl.to(sel, { x: "+=10", duration: 0.05, yoyo: true, repeat: 5, ease: "sine.inOut" }, at);"""

# Вуали вставки поверх экрана: экран виден, затемнено там, где графика.
VEIL = "linear-gradient(90deg, rgba(8,10,30,0.62) 0%, rgba(8,10,30,0.5) 50%, rgba(8,10,30,0.2) 70%, rgba(8,10,30,0) 80%)"
VEILS = {
    None: VEIL,                                                                         # графика слева (по умолчанию)
    "light": "radial-gradient(ellipse 52% 50% at 50% 45%, rgba(8,10,30,0) 55%, rgba(8,10,30,0.55) 100%)",  # показывают центр
    "right": "linear-gradient(270deg, rgba(8,10,30,0.66) 0%, rgba(8,10,30,0.55) 36%, rgba(8,10,30,0) 50%)",  # графика справа
    "bands": ("linear-gradient(180deg, rgba(8,10,30,0.66) 0%, rgba(8,10,30,0.5) 36%, rgba(8,10,30,0) 41%, "
              "rgba(8,10,30,0) 73%, rgba(8,10,30,0.5) 77%, rgba(8,10,30,0.66) 100%)"),    # показывают полосу по центру
}
# Графика, свёрстанная правой колонкой x 1120–1870, — целиком влево и крупнее (x → 110–1047), справа экран открыт
LEFT = "translate(-1290px, 0px) scale(1.25)"
DRIFT = 0.035               # медленный наезд сцены за её длину


# ── мелкие куски интерфейса ─────────────────────────────────────────────────

CURSOR = ('<svg viewBox="0 0 28 28" width="46" height="46"><path d="M5 2 L5 23 L10.5 18 L14.5 26.5 L18 25 L14 16.5 L21.5 16.5 Z" '
          'fill="#111" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>')


def f(t):
    """Время в JS: не меньше нуля (сдвиг начала может увести ранний якорь в минус)."""
    return f"{max(0.0, t):.3f}"


def tip(x, y):
    """Курсор кончиком стрелки в точку кадра (у стрелки кончик в (8, 3) от угла)."""
    return x - 8, y - 3


def logo(name):
    """SVG логотипа из папки логотипов автора (Simple Icons CC0 и свои); нет — пусто."""
    p = (_S["logos"] / name) if _S["logos"] else None
    return p.read_text(encoding="utf-8") if p and p.exists() else ""


def logo_path(name, fallback="✦"):
    """Путь к логотипу для слотов шаблона (icon); нет файла — запасной значок."""
    p = (_S["logos"] / name) if _S["logos"] else None
    return str(p) if p and p.exists() else fallback


def ico(name, px=44):
    return f'<span style="width:{px}px; height:{px}px; display:inline-flex; flex:none">{logo(name)}</span>'


def check(id_):
    return f'<div class="okc" id="{id_}">✓</div>'


def typed(text, prefix="c", cls="ch"):
    """Текст по буквам (печатается type_js / Ins.type)."""
    return "".join(f'<span class="{cls}" id="{prefix}{i}">{"&nbsp;" if ch == " " else ch}</span>' for i, ch in enumerate(text))


def type_js(n, start, span, prefix="c"):
    step = span / max(1, n)
    return [f'tl.set("#{prefix}{i}", {{ opacity: 1 }}, {f(start + i * step)});' for i in range(n)]


def mac_bar(title, dark=False):
    bg, fg = ("#2A2A2E", "#9A9AA6") if dark else ("#ECECEF", "#6B6B78")
    return (f'<div class="ui" style="height:52px; background:{bg}; display:flex; align-items:center; padding:0 18px; gap:16px">'
            f'<div class="tl"><i></i><i></i><i></i></div><div style="flex:1; text-align:center; color:{fg}; font-size:21px; margin-right:60px">{title}</div></div>')


def window(id_, x, y, w, inner, title="", h=None, dark=False, bg=None):
    """Окно macOS: шапка с тремя кружками + содержимое."""
    hh = f"height:{h}px;" if h else ""
    back = bg or ("#1C1C1F" if dark else "#fff")
    return (f'<div class="win" id="{id_}" style="left:{x}px; top:{y}px; width:{w}px; {hh} background:{back}">'
            f'{mac_bar(title, dark)}{inner}</div>')


def term(id_, x, y, w, inner, title="Терминал", h=None):
    return window(id_, x, y, w, f'<div class="mono" style="padding:24px 28px; font-size:28px; line-height:1.5; color:#E6E6EA">{inner}</div>',
                  title, h, dark=True)


def pill(id_, x, y, html, size=32, extra=""):
    return f'<div class="pill" id="{id_}" style="left:{x}px; top:{y}px; font-size:{size}px; {extra}">{html}</div>'


def bubble(id_, text, time, x, y, w=560, mine=False):
    bg = "#E1F7D2" if mine else "#fff"
    return (f'<div class="abs ui" id="{id_}" style="left:{x}px; top:{y}px; width:{w}px; background:{bg}; border-radius:18px; padding:16px 20px; '
            f'font-size:24px; color:#1F1F28; box-shadow:0 2px 4px rgba(0,0,0,.06); opacity:0">{text}'
            f'<div style="text-align:right; font-size:17px; color:#8A9AA6; margin-top:6px">{time}</div></div>')


# ── вставка ─────────────────────────────────────────────────────────────────

class Ins:
    """Вставка: время — от её начала, html, js, звуки.

    kind: "full" — сцена-действие на весь кадр со своим светлым фоном (Д);
          "over" — поверх экрана: прозрачный клип, вуаль (veil: None | light | right | bands), экран виден (Э).
    """

    def __init__(self, name, s0, kind="full", what="", veil=None, place=None):
        assert kind in ("full", "over"), kind
        self.name, self.kind, self.what = name, kind, what
        self.s0 = round(s0 + LEAD.get(name, 0.0), 3)
        self.body, self.js, self.sfx, self.files, self.css = [], [JS_BASE], [], [], BASE_CSS
        self.ids = []
        self.veil, self.place = veil, place
        self._cursor = False

    def t(self, n, k=0, edge=0, d=0.0):
        """Время слова относительно начала вставки."""
        return round(WORDS.t(n, k, edge) - self.s0 + d, 3)

    def add(self, html, *ids):
        self.body.append(html)
        self.ids += [i for i in ids if i not in self.ids]
        return self

    def style(self, css):
        self.css += css
        return self

    def file(self, src, name=None):
        """Картинка/видео в проект сцены → имя для src="…"."""
        name = name or Path(src).name
        self.files.append((str(src), name))
        return name

    def code(self, *lines):
        self.js += list(lines)
        return self

    def sound(self, at, snd, db=-15, dur=None):
        self.sfx.append([round(at, 3), snd, db] + ([round(dur, 2)] if dur else []))
        return self

    def pop(self, sel, at, snd="pop", db=-15, d=0.26):
        self.js.append(f'popIn("{sel}", {f(at)}, {d});')
        return self.sound(at, snd, db) if snd else self

    def fade(self, sel, at, d=0.2):
        self.js.append(f'fade("{sel}", {f(at)}, {d});')
        return self

    def out(self, sel, at, d=0.2):
        self.js.append(f'out("{sel}", {f(at)}, {d});')
        return self

    def type(self, text_len, start, span, prefix="c", snd=True):
        """Печать текста, свёрстанного typed(…, prefix): буквы по одной за span секунд."""
        self.js += type_js(text_len, start, span, prefix)
        return self.sound(start, "type", -18, span) if snd else self

    def cursor(self, x, y, at=0.0):
        """Курсор в точке (x, y) кадра; появляется в at."""
        if not self._cursor:
            self.add(f'<div class="cursor" id="cur">{CURSOR}</div>')
            self._cursor = True
        cx, cy = tip(x, y)
        self.js += [f'tl.set("#cur", {{ x: {cx}, y: {cy} }}, 0);', f'fade("#cur", {f(at)}, 0.15);']
        return self

    def cursor_to(self, sel, at, d=0.5, click=True, snd="tap"):
        """Курсор едет в центр элемента и (по умолчанию) кликает по нему в конце хода."""
        self.js.append(f'cursorTo("{sel}", {f(at)}, {d});')
        if click:
            self.js.append(f'click("{sel}", {f(at + d)});')
            if snd:
                self.sound(at + d, snd, -12)
        return self

    def pick(self, card, check_sel, others, at):
        """Выбор варианта: карточка зеленеет, галочка, остальные гаснут; звук select."""
        oth = f'"{others}"' if others else "null"
        self.js.append(f'pick("{card}", "{check_sel}", {oth}, {f(at)});')
        return self.sound(at, "select", -12)

    # действия на слова внутри сцены — закрывают паузы (`build.py --gaps`); порядок, как у pop: что, потом когда
    def mark(self, sel, at):
        """Пульс элемента — «вот про это говорю»."""
        self.js.append(f'mark("{sel}", {f(at)});')
        return self.sound(at, "tap", -20)

    def wave(self, sels, at):
        """Пульс по группе с шагом 0,08 с: sels — список селекторов."""
        self.js += [f'mark("{x}", {f(at + 0.08 * i)});' for i, x in enumerate(sels)]
        return self.sound(at, "tap", -19)

    def shake(self, sel, at):
        """Встряска — сомнение, ошибка, «не так»."""
        self.js.append(f'shake("{sel}", {f(at)});')
        return self.sound(at, "tap", -18)

    def chip(self, id_, html, x, y, at, until=None, size=30, extra=""):
        """Плашка по смыслу фразы там, где показать нечем; until — когда уйти (иначе — в конце)."""
        self.add(f'<div class="bchip" id="{id_}" style="left:{x}px; top:{y}px; font-size:{size}px; {extra}">{html}</div>', id_)
        self.pop(f"#{id_}", at - 0.1)
        if until is not None:
            self.out(f"#{id_}", until)
        return self

    def done(self, end):
        """Конец вставки: всё уходит в end, хвост 0,3 с; вход «вжух» (на весь кадр) или «свист» (поверх экрана)."""
        if self.ids:
            self.js.append(f'out("{", ".join("#" + i for i in self.ids)}", {f(end)}, 0.25);')
        self.sfx = [q for q in self.sfx if 0 <= q[0] < end + 0.3]
        full = self.kind == "full"
        self.sfx += [[0.0, "whoosh" if full else "swish", -12 if full else -16], [round(end, 3), "swish", -18]]
        body = ('<div class="bg"></div>' if full else "") + "\n".join(self.body)
        return dict(name=self.name, s0=self.s0, dur=round(end + 0.3, 3), kind=self.kind, what=self.what, css=self.css,
                    body=body, js=self.js, sfx=sorted(self.sfx, key=lambda q: q[0]), files=self.files,
                    veil=self.veil, place=self.place)


# ── шаблоны motion-assets (панели, акценты, подписка) ───────────────────────

AT_KEYS = re.compile(r"^(at|.+_at)$")
FULL_TEMPLATES = ("wide_drawer", "wide_follow")


def rel_times(x, s0):
    """Все ключи at / *_at в слотах — из секунд таймлайна в секунды от начала сцены (рекурсивно)."""
    if isinstance(x, dict):
        return {k: (round(v - s0, 3) if AT_KEYS.match(k) and isinstance(v, (int, float)) else rel_times(v, s0))
                for k, v in x.items()}
    if isinstance(x, list):
        return [rel_times(v, s0) for v in x]
    return x


def _times(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if AT_KEYS.match(k) and isinstance(v, (int, float)):
                yield v
            else:
                yield from _times(v)
    elif isinstance(x, list):
        for v in x:
            yield from _times(v)


class Tpl:
    """Сцена из шаблона motion-assets (wide_drawer / wide_chips / wide_number / wide_message / wide_list / wide_follow).

    slots — как у шаблона (references/templates.md motion-assets), но время (at, reply_at, …) — секунды
    ТАЙМЛАЙНА (`at(…)`): здесь переводится в секунды от начала сцены. face=True — шаблону нужен кусок
    таймлайна с лицом (слот face; build.py вырежет его из записи по cut-list).
    """

    def __init__(self, name, template, s0, slots, what="", layout=None, face=False):
        self.name, self.template, self.what, self.face = name, template, what, face
        self.s0 = round(s0, 3)
        self.layout = layout or ("full" if template in FULL_TEMPLATES else "overlay")
        self.slots = rel_times(slots, self.s0)

    def spec(self):
        return dict(name=self.name, template=self.template, s0=self.s0, kind="tpl", layout=self.layout,
                    what=self.what, slots=self.slots, face=self.face)


def drawer(name, s0, end, groups, what="", panel=0.64):
    """Светлая панель wide_drawer (автор уезжает влево, группы по словам): выезжает за 0,6 с до первого
    текста, закрывается не раньше, чем последний элемент побудет на экране 1,6 с. Время — таймлайна."""
    rel = rel_times(groups, s0)
    times = list(_times(rel))
    g0 = rel[0]
    first = min([g0["at"]] + [t - 0.12 for t in _times({k: v for k, v in g0.items() if k != "at"})])
    close = max(end - s0 - 0.5, max(times) + 1.6)
    focus = section().get("лицо_x", FOCUS_X)
    slots = {"face": "", "face_start": 0, "focus_x": focus, "panel": panel,
             "open_at": max(0.25, round(first - 0.6, 3)), "close_at": round(close, 3), "groups": rel}
    t = Tpl(name, "wide_drawer", s0, {}, what, "full", face=True)
    t.slots = slots
    return t


# ── разбор JS таймлайна: первый элемент и паузы ─────────────────────────────

SKIP_SEL = ("#cur", "#veil", "#bgv", "#spn", "#stage", "#place")
ENTER = re.compile(r'(popIn|fade|click|moveTo)\("([^"]+)",\s*([-\d.]+)')
ENTER_LAST = re.compile(r'(tl\.fromTo|tl\.set|pick|mark)\("([^"]+)".*,\s*([-\d.]+)\)\s*;?\s*$')
ANY = re.compile(r'(popIn|fade|out|click|moveTo|cursorTo|pick|mark|shake|tl\.fromTo|tl\.to|tl\.set)\(')


def _stmts(js):
    for stmt in "\n".join(js[1:]).replace(");", ");\n").split("\n"):
        stmt = stmt.strip()
        if stmt:
            yield stmt


def first_content(js):
    """Момент первого элемента сцены (не окно-основа в 0, не курсор, не вуаль) по строкам JS."""
    times = []
    for stmt in _stmts(js):
        if stmt.startswith(("out(", "const ")) or "opacity: 0, duration" in stmt:
            continue
        m = ENTER.match(stmt) or ENTER_LAST.match(stmt)
        if not m or any(m.group(2).startswith(x) for x in SKIP_SEL):
            continue
        if m.group(1) == "tl.set" and "opacity: 1" not in stmt:
            continue
        t = float(m.group(3))
        if t > 0.16:                                     # окна-основа в 0–0,15 с — фон, не содержание
            times.append(t)
    return min(times) if times else 0.0


def activity(js):
    """Интервалы, когда в кадре что-то появляется или движется: [(a, b)]. Долгие фоновые (> 3 с:
    крутилка, бегущий пунктир, наезд сцены) не в счёт — глаз их не считает событием."""
    iv = []
    for stmt in _stmts(js):
        m = ANY.match(stmt)
        if not m or stmt.startswith("const ") or '"#veil"' in stmt or '"#stage"' in stmt:
            continue
        kind = m.group(1)
        args = re.findall(r',\s*(-?[\d.]+)', stmt)
        if kind in ("mark", "shake"):
            if not args:
                continue
            t, d = float(args[0]), 0.35
        elif kind in ("popIn", "fade", "out", "click", "cursorTo"):
            if not args:
                continue
            t = float(args[0])
            d = {"click": 0.17}.get(kind, float(args[1]) if len(args) > 1 else 0.26)
        elif kind == "moveTo":
            t, d = float(args[0]), float(args[3]) if len(args) > 3 else 0.5
        elif kind == "pick":
            t, d = float(args[-1]), 0.32
        else:
            tm = re.search(r',\s*(-?[\d.]+)\)\s*;?\s*$', stmt)
            if not tm:
                continue
            t = float(tm.group(1))
            dm = re.search(r'duration:\s*([\d.]+)', stmt)
            d = float(dm.group(1)) if dm else 0.05
            rp = re.search(r'repeat:\s*(\d+)', stmt)
            d *= (int(rp.group(1)) + 1) if rp else 1
        if d > 3.0:
            continue
        iv.append((max(0.0, t), max(0.0, t) + max(d, 0.05)))
    return sorted(iv)


def idle_gaps(sc, min_gap=1.8):
    """Паузы внутри сцены: между событиями ничего не происходит дольше min_gap → [(a, b)] от начала сцены."""
    iv = activity(sc["js"])
    if not iv:
        return []
    end = sc["dur"] - 0.3
    gaps, cur = [], iv[0][1]
    for a, b in iv[1:]:
        if a > end - 0.05:
            break
        if a - cur > min_gap:
            gaps.append((round(cur, 2), round(a, 2)))
        cur = max(cur, b)
    if end - cur > min_gap:
        gaps.append((round(cur, 2), round(end, 2)))
    return gaps


MIN_VISIBLE = 0.8          # элемент на экране меньше — «мелькнуло», не успеть прочитать
SHOW = re.compile(r'(popIn|fade)\("([^"]+)",\s*([-\d.]+)')
HIDE = re.compile(r'out\("([^"]+)",\s*([-\d.]+)')
NOT_CONTENT = ("#cur", "#caret", "#veil", "#bgv", "#stage", "#place")


def brief(sc, min_visible=MIN_VISIBLE):
    """Что мелькнуло: [(селектор, когда появился, сколько был виден)]. Сцена (Ins) — по JS: появление → ближайший
    уход этого id (нет своего — уход всей сцены); шаблон — последнее время в слотах против длины сцены."""
    if sc.get("kind") == "tpl":
        slots = sc["slots"]
        dur = slots.get("close_at") or slots.get("duration") or 0
        times = [t for t in _times({k: v for k, v in slots.items() if k not in ("open_at", "close_at")})]
        last_t = max(times) if times else 0
        return [("последний элемент", round(last_t, 2), round(dur - last_t, 2))] if dur and dur - last_t < min_visible + 0.4 else []
    shows, hides = [], {}
    for stmt in _stmts(sc["js"]):
        m = SHOW.match(stmt)
        if m:
            shows += [(x.strip(), float(m.group(3))) for x in m.group(2).split(",")]
            continue
        m = HIDE.match(stmt)
        if m:
            for x in m.group(1).split(","):
                hides.setdefault(x.strip(), []).append(float(m.group(2)))
    end = sc["dur"] - 0.3
    out = []
    for sel, t in shows:
        if sel.startswith(NOT_CONTENT):
            continue
        gone = min([h for h in hides.get(sel, []) if h > t] or [end])
        if gone - t < min_visible:
            out.append((sel, round(t, 2), round(gone - t, 2)))
    return out


def fitted(fn, lead=0.35, tol=0.6):
    """Сцена, которая начинается за lead до своего первого элемента: пустое ожидание > tol — сдвиг начала
    (повторный вызов fn с LEAD). Шаблоны (Tpl) возвращаются как есть — у них своя логика входа."""
    res = fn()
    if isinstance(res, Tpl):
        return res.spec(), 0.0
    LEAD.pop(res["name"], None)
    res = fn()
    gap = first_content(res["js"])
    shift = 0.0
    if gap > tol:
        shift = LEAD[res["name"]] = round(gap - lead, 3)
        res = fn()
    res["sfx"] = sorted([q for q in res["sfx"] if q[0] >= 0], key=lambda q: q[0])
    return res, shift


# ── проект HyperFrames ──────────────────────────────────────────────────────

def project(sc, d, bg_video=None):
    """Сцена (Ins.done) → проект HyperFrames в папке d: index.html + scene.json. Без рендера.
    Вставка поверх экрана: bg_video — кусок таймлайна под ней (клип непрозрачный, лёгкий mp4); без него —
    прозрачный клип (ProRes 4444: с вуалью на весь кадр ~50 МБ/с — только когда место есть)."""
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    body, js = sc["body"], list(sc["js"])
    if sc.get("place"):
        body = f'<div id="place" style="position:absolute; inset:0; transform-origin:0 0; transform:{sc["place"]}">{body}</div>'
    body = f'<div id="stage" style="position:absolute; inset:0">{body}</div>'
    js.append(f'tl.fromTo("#stage", {{ scale: 1 }}, {{ scale: {1 + DRIFT}, duration: {sc["dur"]:.3f}, ease: "none" }}, 0);')
    bg = "#FFFFFF"
    if sc["kind"] == "over":
        body = (f'<div class="abs" id="veil" style="inset:0; opacity:0; background:{VEILS[sc.get("veil")]}"></div>' + body)
        js = js[:1] + ['fade("#veil", 0.0, 0.3);', f'out("#veil", {f(sc["dur"] - 0.35)}, 0.3);'] + js[1:]
        bg = "transparent"
        if bg_video:
            body = (f'<div class="abs" style="inset:0"><video id="bgv" src="{bg_video}" data-start="0" data-duration="{sc["dur"]:.3f}" '
                    f'data-media-start="0" data-track-index="1" muted playsinline style="position:absolute; inset:0; width:100%; '
                    f'height:100%; object-fit:cover"></video></div>' + body)
            bg = "#000000"
    fonts = hf.setup_project(d, theme(), extra=sc["files"])
    page = hf.page(sc["css"], body, "\n".join(js), sc["dur"], fonts, bg=bg, w=W, h=H)
    (d / "index.html").write_text(page, encoding="utf-8")
    meta = {k: sc[k] for k in ("name", "kind", "s0", "dur", "what", "sfx", "veil")}
    meta["baked"] = bool(bg_video)
    (d / "scene.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def copy_example(dst):
    """assets/scenes.example.py → dst (если файла ещё нет)."""
    src = HERE.parent / "assets" / "scenes.example.py"
    if not Path(dst).exists():
        shutil.copy(src, dst)
    return Path(dst)


__all__ = ["W", "H", "INK", "SEC", "MUTED", "OK", "DANGER", "GREEN", "LEFT", "VEILS", "CURSOR", "WORDS",
           "at", "last", "f", "tip", "logo", "logo_path", "ico", "check", "typed", "type_js", "mac_bar", "window", "term", "pill",
           "bubble", "Ins", "Tpl", "drawer", "section"]
