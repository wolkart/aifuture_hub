"""Логотипы выстраиваются: на светлой карточке сервисы влетают по одному (каждый — на своё
слово), с отскоком и поворотом, подпись проявляется, рядом выскакивает галочка.
Родная тема — светлая.

Когда брать: «работает в X, Y и Z», «подключается к…», «на выбор: A, B, C» — вместо текстовой
карточки-перечня (урок 2026-10-17: перечень текстом — примитивно, логотипы — графика).
Логотипы приходят файлами: чужих знаков в шаблоне нет.
"""
import _common as c

NAME = "logo_row"
TITLE = "Логотипы выстраиваются"
DEFAULT_KIND = "light"
BOX = (420, 1420)
BASE_TAGS = ["логотипы", "сервисы", "интеграции", "совместимость"]
SLOTS = {
    "title": {"about": "строка над логотипами, можно пусто", "default": ""},
    "items": {"about": "1–4 сервиса: [{icon: путь/эмодзи, label: имя, at: секунда}]",
              "default": [{"icon": "⚡", "label": "Сервис", "at": 0.1}]},
    "check": {"about": "галочка у каждого: true | false", "default": True},
    "duration": {"about": "длина сцены, с (0 — по последнему логотипу + 0,9)", "default": 0},
    "tags": {"about": "до 4 фоновых слов", "default": []},
}


def css(pal, n):
    row = 230 if n <= 3 else 190
    return f"""
#card {{ position: absolute; left: 80px; right: 80px; top: 470px; padding: 50px 60px 40px; border-radius: 48px;
  background: {c.WHITE}; box-shadow: 0 40px 90px rgba(0, 0, 0, 0.18); opacity: 0; }}
#ttl {{ font-size: 46px; font-weight: 700; color: {pal['muted']}; margin-bottom: 20px; opacity: 0; }}
.it {{ display: flex; align-items: center; height: {row}px; }}
.lg {{ width: {row - 40}px; height: {row - 40}px; border-radius: 34px; display: flex; align-items: center; justify-content: center;
  opacity: 0; }}
.lg img, .lg span {{ width: 100%; height: 100%; object-fit: contain; font-size: {row - 70}px; line-height: {row - 40}px; text-align: center; }}
.lb {{ margin-left: 40px; font-size: {int(row * 0.3)}px; font-weight: 800; white-space: nowrap; color: {pal['ink']}; opacity: 0; letter-spacing: -0.01em; }}
.ok {{ margin-left: auto; width: 84px; height: 84px; border-radius: 50%; background: {pal['ok']}; color: {c.WHITE};
  font-size: 54px; font-weight: 800; display: flex; align-items: center; justify-content: center; opacity: 0; }}
"""


def build(slots, theme, kind=None, layout="full"):
    s = c.merge_slots(SLOTS, slots)
    pal = c.palette(theme, kind or DEFAULT_KIND)
    items = s["items"][:4]
    files, rows = [], []
    for i, it in enumerate(items):
        ic, f = c.icon_html(it["icon"], "", name=f"logo{i}")
        files += f
        ok = f'<div class="ok" id="ok{i}">✓</div>' if s["check"] else ""
        label = c.esc(it["label"])
        rows.append(f'<div class="it"><div class="lg" id="lg{i}">{ic}</div><div class="lb" id="lb{i}">{label}</div>{ok}</div>')
    ttl = f'<div id="ttl">{c.esc(s["title"])}</div>' if s["title"] else ""
    content = f'<div id="card">{ttl}{"".join(rows)}</div>'
    times = [float(it.get("at", 0.15 + 0.45 * i)) for i, it in enumerate(items)]
    dur = float(s["duration"]) or (max(times) + 0.9)
    deco, deco_js = c.decor(pal, layout, s["tags"], dur)
    body, bg, size = c.compose(pal, layout, deco, content, dur, BOX)
    js = ['tl.fromTo("#card", { opacity: 0, y: 80, scale: 0.92 }, { opacity: 1, y: 0, scale: 1, duration: 0.32, '
          'ease: "power3.out" }, 0.0);']
    if s["title"]:
        js.append('fadeIn("#ttl", 0.1);')
    events = [c.ev(0.0, "карточка выезжает снизу")]
    for i, t in enumerate(times):
        js += [f'tl.fromTo("#lg{i}", {{ opacity: 0, x: 420, rotation: 25, scale: 0.4 }}, {{ opacity: 1, x: 0, rotation: 0, '
               f'scale: 1, duration: 0.42, ease: "back.out(1.7)" }}, {c.fmt(t)});',
               f'tl.fromTo("#lb{i}", {{ opacity: 0, x: 40 }}, {{ opacity: 1, x: 0, duration: 0.25, ease: "power2.out" }}, '
               f'{c.fmt(t + 0.15)});']
        if s["check"]:
            js.append(f'tl.fromTo("#ok{i}", {{ opacity: 0, scale: 0.2 }}, {{ opacity: 1, scale: 1, duration: 0.3, '
                      f'ease: "back.out(3)" }}, {c.fmt(t + 0.3)});')
        events.append(c.ev(t, f"логотип «{items[i]['label']}» влетает"))
        events.append(c.ev(t + 0.45, f"«{items[i]['label']}» виден целиком" + (" с галочкой" if s["check"] else "")))
    events.append(c.ev(min(dur, max(times) + 0.6), "все логотипы на месте"))
    js += deco_js
    labels = ", ".join(it["label"] for it in items)
    describes = f"логотипы выстраиваются на карточке: {labels}" + (" — с галочками" if s["check"] else "")
    style = c.base_css(pal, layout) + css(pal, len(items))
    return c.result(style, body, js, dur, events, pal, layout, bg, size, files, BASE_TAGS, describes,
                    preview_t=max(times) + 0.6)
