"""Концовка-ссылка: настоящая шапка профиля (скриншот или кадр записи) в 3D-рамке с
наклоном, кольца и мягкое появление; ссылка выделяется одним из трёх приёмов, сверху
призыв. Родная тема — светлая.

Когда брать: финал ролика «ссылка в шапке профиля» — на любой площадке. Кодового
слова здесь нет и не бывает: концовка-ссылка и «напиши СЛОВО в комменты» — два разных
CTA, в одном ролике одно из двух (в reel это `cta.тип`).

Приёмы выделения (слот highlight):
  pop   — «выпуклая»: ссылка выходит из карточки к зрителю плашкой, тап, волны;
  click — «клик»: курсор прилетает, маркер под ссылкой, клик, всплывает подсказка;
  zoom  — «наезд»: камера ныряет к ссылке, карточка уходит в размытие, тап, волны.
Без профиля карточка рисуется сама (кружок-аватар, имя, ссылка) — для пробы.
Ссылка на плашке набрана шрифтом темы, а не вырезана из скриншота: на мелком
скриншоте вырезка мылится, набор остаётся резким при любом увеличении.
"""
import struct
import subprocess
from pathlib import Path

import _common as c

NAME = "end_card"
TITLE = "Концовка-ссылка"
DEFAULT_KIND = "light"
BOX = (220, 1500)
BASE_TAGS = ["концовка", "cta", "ссылка", "профиль", "шапка", "призыв"]
HIGHLIGHTS = ("pop", "click", "zoom")
POINTERS = ("auto", "tap", "cursor", "none")
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}
SLOTS = {
    "cta": {"about": "призыв по словам; *слово* — акцент, _слово_ — второй цвет, \\n — перенос",
            "default": "Ссылка в шапке *профиля*"},
    "context": {"about": "строка-контекст над призывом, можно пусто", "default": ""},
    "profile": {"about": "скриншот профиля (PNG/JPG/WEBP) или запись (MP4/MOV); пусто — карточка рисуется",
                "default": ""},
    "profile_at": {"about": "секунда записи, с которой взять кадр", "default": 0.0},
    "crop": {"about": "[x, y, w, h] в пикселях источника — шапка профиля; пусто — весь кадр",
             "default": []},
    "link_box": {"about": "[x, y, w, h] в пикселях источника — где на скриншоте ссылка", "default": []},
    "link": {"about": "текст ссылки на плашке", "default": "example.com/link"},
    "name": {"about": "имя на нарисованной карточке (без профиля)", "default": "Мой профиль"},
    "highlight": {"about": "приём выделения: pop | click | zoom", "default": "pop"},
    "pointer": {"about": "указатель: auto (click — курсор, иначе тап) | tap | cursor | none",
                "default": "auto"},
    "tone": {"about": "тон скриншота: auto | light | dark", "default": "auto"},
    "glow": {"about": "цвет выделения: auto (тёмная — акцент, светлая — второй) | accent | secondary | #hex",
             "default": "auto"},
    "tags": {"about": "до 4 фоновых слов", "default": ["ссылка", "профиль", "шапка", "канал"]},
}

CARD_CY = 1050          # центр карточки по вертикали (full)
BEZEL = 18              # стеклянная рамка вокруг скриншота
PILL_PX = 46            # кегль ссылки на плашке
PERSPECTIVE = 1800
T_CARD, T_HL = 0.2, 1.35
BLOBS = [("left", -160, 260, 560, "sec"), ("right", -180, 1180, 600, "acc")]


# ── источник ─────────────────────────────────────────────────────────────────

def image_size(path):
    """(w, h) картинки: PNG и JPEG — по заголовку, остальное — ffprobe."""
    p = Path(path)
    data = p.read_bytes()[:64 * 1024]
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker, size = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + size
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height", "-of", "csv=p=0", str(p)])
    w, h = out.decode().strip().split(",")[:2]
    return int(w), int(h)


def frame_from_video(path, at):
    """Кадр записи → PNG в кеше (оригинал не трогается)."""
    p = Path(path)
    out = Path.home() / ".cache" / "reel" / "end_card" / f"{p.stem}-{float(at):.2f}.png"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{float(at):.3f}", "-i", str(p),
                        "-frames:v", "1", str(out)], check=True)
    return out


def mean_luma(path, crop):
    """Средняя яркость области 0…255 (ffmpeg → 1×1 пиксель). Нет ffmpeg — None."""
    x, y, w, h = crop
    try:
        raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-vf",
                                       f"crop={w}:{h}:{x}:{y},scale=1:1", "-f", "rawvideo",
                                       "-pix_fmt", "gray", "-"])
        return raw[0] if raw else None
    except (OSError, subprocess.CalledProcessError):
        return None


def source(s):
    """Слот profile → (картинка | None, файл для проекта | None)."""
    if not s["profile"]:
        return None, None
    p = Path(str(s["profile"])).expanduser()
    if not p.exists():
        raise ValueError(f"профиль не найден: {s['profile']}")
    if p.suffix.lower() in VIDEO_EXT:
        p = frame_from_video(p, s["profile_at"])
    elif p.suffix.lower() not in c.IMAGE_EXT:
        raise ValueError(f"профиль: картинка или запись, а не {p.suffix}")
    return p, (str(p), f"profile{p.suffix.lower()}")


def box4(value, what):
    if not (isinstance(value, (list, tuple)) and len(value) == 4):
        raise ValueError(f"{what}: нужен [x, y, w, h] в пикселях источника")
    x, y, w, h = (float(v) for v in value)
    if w <= 0 or h <= 0:
        raise ValueError(f"{what}: ширина и высота больше нуля")
    return x, y, w, h


# ── геометрия ────────────────────────────────────────────────────────────────

def text_width(text, px):
    """Оценка ширины строки шрифтом темы (жирный гротеск): узкие знаки уже, m/w шире."""
    em = 0.0
    for ch in str(text):
        if ch in ".,:;!|'il1tfjr/ ":
            em += 0.34
        elif ch in "mwMW@":
            em += 0.9
        elif ch.isupper() or ch.isdigit() or ch in "_-":
            em += 0.64
        else:
            em += 0.6
    return em * px


def pill_size(link):
    """Плашка ссылки: иконка + текст + поля. → (w, h)."""
    return round(text_width(link, PILL_PX) * 1.06 + PILL_PX * 1.0 + 16 + 2 * 30), round(PILL_PX * 1.25 + 36)


def geometry(s, img):
    """Размер карточки, где на ней ссылка и масштаб скриншота. Координаты — от левого
    верхнего угла лица карточки (без рамки)."""
    if img is None:
        cw, ch = 900, 400
        lw = text_width(s["link"], 36) + 36 + 14 + 24
        return {"cw": cw, "ch": ch, "k": 1.0, "img": None, "crop": None,
                "lx": 44, "ly": 296, "lw": lw, "lh": 56}
    iw, ih = image_size(img)
    x, y, w, h = box4(s["crop"], "crop") if s["crop"] else (0, 0, iw, ih)
    if not s["link_box"]:
        raise ValueError("link_box: укажи, где на скриншоте ссылка — [x, y, w, h] в пикселях")
    lx, ly, lw, lh = box4(s["link_box"], "link_box")
    cw = 960 if w / h > 2.4 else 900
    k = cw / w
    return {"cw": cw, "ch": round(h * k), "k": k, "img": (iw, ih), "crop": (x, y, w, h),
            "lx": (lx - x) * k, "ly": (ly - y) * k, "lw": lw * k, "lh": lh * k}


# ── вид ──────────────────────────────────────────────────────────────────────

CHAIN = ('<svg class="chain" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
         'stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7'
         'l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>')
CURSOR = ('<svg class="cur" viewBox="0 0 32 32"><path d="M6 3 L6 26 L12 20 L16 29 L20 27 L16 18.5 '
          'L24 18.5 Z" fill="#FFFFFF" stroke="#000000" stroke-width="1.8" stroke-linejoin="round"/></svg>')


def colors(pal, s, tone):
    glow = s["glow"]
    if glow == "auto":
        hl = pal["acc"] if pal["dark"] else pal["sec"]
    else:
        hl = c.color_key(glow, pal)
    light_card = tone == "light"
    return {
        "hl": hl,
        "pill_bg": c.WHITE if light_card else c.mix(pal["deep_end"], pal["deep"], 0.35),
        "pill_ink": c.mix(pal["sec"], c.BLACK, 0.25) if light_card else c.mix(pal["sec"], c.WHITE, 0.35),
        "face_bg": c.WHITE if light_card else c.mix(pal["deep_end"], pal["deep"], 0.2),
        "face_ink": pal["ink"] if light_card else c.WHITE,
        "dim": "rgba(255, 255, 255, 0.32)" if light_card else "rgba(0, 0, 0, 0.4)",
        "edge": c.mix(pal["bg1"], pal["sec"], 0.35) if not pal["dark"] else c.mix(pal["deep"], pal["sec"], 0.3),
    }


def css(pal, g, col, pill_w, pill_h, layout):
    cw, ch = g["cw"], g["ch"]
    ow, oh = cw + 2 * BEZEL, ch + 2 * BEZEL
    left, top = (c.W - ow) / 2, CARD_CY - oh / 2
    dark = pal["dark"]
    glass = "rgba(255, 255, 255, 0.07)" if dark else "rgba(255, 255, 255, 0.6)"
    rim = "rgba(255, 255, 255, 0.16)" if dark else "rgba(255, 255, 255, 0.95)"
    floor = c.rgba(pal["deep_end"], 0.7) if dark else c.rgba(pal["ink"], 0.28)
    img_css = ""
    if g["img"]:
        iw, ih = g["img"]
        x, y = g["crop"][:2]
        img_css = (f"#shot {{ position: absolute; left: {-x * g['k']:.1f}px; top: {-y * g['k']:.1f}px; "
                   f"width: {iw * g['k']:.1f}px; height: {ih * g['k']:.1f}px; max-width: none; }}")
    return f"""
#cam {{ position: absolute; inset: 0; }}
#stage {{ position: absolute; inset: 0; }}
#rings {{ position: absolute; left: {c.W / 2}px; top: {CARD_CY}px; width: 0; height: 0; }}
.bring {{ position: absolute; left: {-ow * 0.42:.0f}px; top: {-ow * 0.42:.0f}px; width: {ow * 0.84:.0f}px;
  height: {ow * 0.84:.0f}px; border-radius: 50%; border: 4px solid {c.rgba(pal['sec'], 0.6)}; opacity: 0; }}
#halo {{ position: absolute; left: {-ow * 0.55:.0f}px; top: {-ow * 0.55:.0f}px; width: {ow * 1.1:.0f}px;
  height: {ow * 1.1:.0f}px; border-radius: 50%; opacity: 0;
  background: radial-gradient(circle, {c.rgba(pal['sec'], 0.38 if dark else 0.3)} 0%, {c.rgba(pal['sec'], 0)} 65%); }}
#floor {{ position: absolute; left: {left + ow * 0.1:.0f}px; top: {top + oh + 40:.0f}px; width: {ow * 0.8:.0f}px;
  height: 70px; border-radius: 50%; background: {floor}; filter: blur(34px); opacity: 0; }}
#fade {{ position: absolute; inset: 0; opacity: 0; perspective: {PERSPECTIVE}px;
  perspective-origin: 50% {top + BEZEL + g['ly'] + g['lh'] / 2:.0f}px; }}
#card {{ position: absolute; left: {left:.0f}px; top: {top:.0f}px; width: {ow}px; height: {oh}px;
  transform-style: preserve-3d; }}
.edge {{ position: absolute; inset: 0; border-radius: 46px; background: {col['edge']}; }}
#bezel {{ position: absolute; inset: 0; border-radius: 46px; background: {glass};
  box-shadow: inset 0 0 0 2px {rim}, inset 0 0 0 4px {c.rgba(pal['sec'], 0.18)},
  0 50px 120px {c.rgba(pal['deep_end'] if dark else pal['ink'], 0.32)}; }}
#face {{ position: absolute; left: {BEZEL}px; top: {BEZEL}px; width: {cw}px; height: {ch}px;
  border-radius: 30px; overflow: hidden; background: {col['face_bg']}; color: {col['face_ink']}; }}
{img_css}
#dim {{ position: absolute; inset: 0; background: {col['dim']}; opacity: 0; }}
#glare {{ position: absolute; top: -50%; left: 0; width: 38%; height: 200%; transform: rotate(18deg);
  background: linear-gradient(90deg, rgba(255, 255, 255, 0), rgba(255, 255, 255, {0.16 if dark else 0.5}),
  rgba(255, 255, 255, 0)); opacity: 0; }}
#slot {{ position: absolute; left: {g['lx'] - 10:.1f}px; top: {g['ly'] - 6:.1f}px; width: {g['lw'] + 20:.1f}px;
  height: {g['lh'] + 12:.1f}px; border-radius: 14px; background: {c.rgba(col['hl'], 0.22)};
  box-shadow: 0 0 0 3px {c.rgba(col['hl'], 0.75)}; opacity: 0; }}
#mark {{ position: absolute; left: {g['lx'] - 8:.1f}px; top: {g['ly'] + g['lh'] * 0.18:.1f}px;
  width: {g['lw'] + 16:.1f}px; height: {g['lh'] * 0.82:.1f}px; border-radius: 10px;
  background: {c.rgba(col['hl'], 0.32)}; transform-origin: 0 50%; opacity: 0; }}
#pp {{ position: absolute; left: {BEZEL + g['lx'] + g['lw'] / 2:.1f}px; top: {BEZEL + g['ly'] + g['lh'] / 2:.1f}px;
  width: 0; height: 0; transform-style: preserve-3d; }}
#lift {{ position: absolute; left: 0; top: 0; width: 0; height: 0; transform-style: preserve-3d; }}
.ctr {{ position: absolute; left: 0; top: 0; }}
#pill, #pglow, .rip {{ width: {pill_w}px; height: {pill_h}px; border-radius: 999px; }}
#pill {{ display: flex; align-items: center; justify-content: center; gap: 16px; opacity: 0;
  background: {col['pill_bg']}; color: {col['pill_ink']}; font-size: {PILL_PX}px; font-weight: 700;
  letter-spacing: -0.01em; white-space: nowrap; box-shadow: 0 0 0 3px {col['hl']},
  0 30px 60px {c.rgba(pal['deep_end'] if dark else pal['ink'], 0.35)}; }}
#pglow {{ background: {col['hl']}; filter: blur(28px); opacity: 0; }}
.rip {{ border: 4px solid {col['hl']}; opacity: 0; }}
.chain {{ width: {PILL_PX}px; height: {PILL_PX}px; flex: none; }}
#tap {{ width: 76px; height: 76px; border-radius: 50%;
  background: {"rgba(255, 255, 255, 0.35)" if col['pill_bg'] != c.WHITE else "rgba(0, 0, 0, 0.22)"};
  border: 4px solid rgba(255, 255, 255, 0.95); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3); }}
#ptr {{ position: absolute; left: 0; top: 0; opacity: 0; }}
.cur {{ width: 72px; height: 72px; filter: drop-shadow(0 8px 14px rgba(0, 0, 0, 0.35)); }}
#bub {{ display: flex; align-items: center; gap: 14px; padding: 22px 34px; border-radius: 28px; opacity: 0;
  background: {col['pill_bg']}; color: {col['pill_ink']}; font-size: {PILL_PX}px; font-weight: 700;
  white-space: nowrap; box-shadow: 0 0 0 3px {col['hl']},
  0 30px 70px {c.rgba(pal['deep_end'] if dark else pal['ink'], 0.35)}; }}
#bub .tail {{ position: absolute; left: 50%; bottom: -13px; width: 26px; height: 26px; margin-left: -13px;
  transform: rotate(45deg); background: {col['pill_bg']}; box-shadow: 3px 3px 0 0 {col['hl']}; }}
#bub .tail.up {{ top: -13px; bottom: auto; box-shadow: -3px -3px 0 0 {col['hl']}; }}
#scrim {{ position: absolute; left: 0; right: 0; top: 0; height: 1000px; opacity: 0;
  background: linear-gradient(180deg, {pal['bg0']} 0%, {c.rgba(pal['bg0'], 0.96)} 70%, {c.rgba(pal['bg0'], 0)} 100%); }}
.dav {{ position: absolute; left: 44px; top: 44px; width: 150px; height: 150px; border-radius: 50%;
  background: linear-gradient(135deg, {pal['sec']}, {pal['acc']}); }}
.dnm {{ position: absolute; left: 230px; top: 64px; font-size: 46px; font-weight: 800; }}
.dbar {{ position: absolute; left: 230px; height: 22px; border-radius: 11px;
  background: {c.rgba(pal['muted'], 0.35)}; }}
.dlink {{ position: absolute; left: {g['lx']:.0f}px; top: {g['ly']:.0f}px; height: {g['lh']:.0f}px;
  display: flex; align-items: center; gap: 14px; font-size: 36px; font-weight: 700; color: {col['pill_ink']}; }}
.dlink .chain {{ width: 36px; height: 36px; }}
"""


def face_html(s, g):
    if g["img"]:
        return '<img id="shot" src="{}" alt="" />'
    return (f'<div class="dav"></div><div class="dnm">{c.esc(s["name"])}</div>'
            '<div class="dbar" style="top:150px; width:520px"></div>'
            '<div class="dbar" style="top:200px; width:400px"></div>'
            f'<div class="dlink">{CHAIN}<span>{c.esc(s["link"])}</span></div>')


def ctr(id_, inner, cls="ctr"):
    """Элемент с центром в начале координат родителя (xPercent/yPercent −50 в твинах)."""
    return f'<div class="{cls}" id="{id_}">{inner}</div>'


def pill_x(lcx, ow, pill_w, z, pull=0.3, margin=70):
    """Где встанет центр плашки на карточке (от левого края рамки): чуть ближе к центру
    карточки и целиком в кадре. Плашка поднята на z — перспектива раздвигает её от
    центра кадра в f раз, поэтому граница считается по проекции."""
    left = (c.W - ow) / 2
    f = PERSPECTIVE / (PERSPECTIVE - z)
    want = left + lcx + (ow / 2 - lcx) * pull
    lo = c.W / 2 + (margin + pill_w * f / 2 - c.W / 2) / f
    hi = c.W / 2 + (c.W - margin - pill_w * f / 2 - c.W / 2) / f
    return min(max(want, lo), hi) - left


# ── сборка ───────────────────────────────────────────────────────────────────

def build(slots, theme, kind=None, layout="full"):
    s = c.merge_slots(SLOTS, slots)
    if s["highlight"] not in HIGHLIGHTS:
        raise ValueError(f"highlight {s['highlight']!r}: один из {', '.join(HIGHLIGHTS)}")
    if s["pointer"] not in POINTERS:
        raise ValueError(f"pointer {s['pointer']!r}: один из {', '.join(POINTERS)}")
    pal = c.palette(theme, kind or DEFAULT_KIND)
    img, file_ = source(s)
    g = geometry(s, img)
    tone = s["tone"]
    if tone == "auto":
        luma = mean_luma(img, [int(v) for v in g["crop"]]) if img else None
        tone = ("light" if luma >= 128 else "dark") if luma is not None else pal["kind"]
    col = colors(pal, s, tone)
    hl = s["highlight"]
    pointer = s["pointer"] if s["pointer"] != "auto" else ("cursor" if hl == "click" else "tap")
    pill_w, pill_h = pill_size(s["link"])
    # подсказка над ссылкой, если ссылка внизу карточки; иначе под ней — не закрывать имя
    bub_below = (g["ly"] + g["lh"] / 2) / g["ch"] < 0.6

    ow, oh = g["cw"] + 2 * BEZEL, g["ch"] + 2 * BEZEL
    card_top = CARD_CY - oh / 2
    head_top = max(230, card_top - 330)
    h = c.headline(s["cta"], s["context"], prefix="h", top=head_top, base_px=88)
    head_js, times = c.headline_js(h, 0.12 if s["context"] else 0.08, 0.9)
    words_end = times[-1] + 0.32 if times else 0.5

    # где плашка: центр ссылки на карточке (от левого края рамки) и сдвиг к центру карточки
    lcx = BEZEL + g["lx"] + g["lw"] / 2
    lcy = BEZEL + g["ly"] + g["lh"] / 2
    tx = pill_x(lcx, ow, pill_w, 170 if hl == "pop" else 60)
    s0 = min(1.0, (g["lw"] + 20) / pill_w)     # плашка рождается размером со ссылку

    dur = 5.0
    js = list(head_js)
    if h["ctx_id"]:
        js.append(f'fadeIn("#{h["ctx_id"]}", 0.02);')
    # мягкое появление: кольца, тень, карточка из размытия и глубины
    js += [f'tl.fromTo("#br{i}", {{ scale: 0.55, opacity: 0 }}, {{ scale: 1.25, opacity: 0.9, duration: 0.9, '
           f'ease: "power2.out" }}, {c.fmt(T_CARD + i * 0.16)});' for i in range(3)]
    js += [f'tl.fromTo("#br{i}", {{ opacity: 0.9 }}, {{ opacity: 0.25, duration: 1.2, immediateRender: false }}, '
           f'{c.fmt(T_CARD + 0.9 + i * 0.16)});' for i in range(3)]
    js.append(f'tl.fromTo("#halo", {{ opacity: 0, scale: 0.5 }}, {{ opacity: 1, scale: 1, duration: 1.2, '
              f'ease: "power2.out" }}, {T_CARD});')
    js += [
        f'tl.fromTo("#fade", {{ opacity: 0, filter: "blur(18px)" }}, {{ opacity: 1, filter: "blur(0px)", '
        f'duration: 0.7, ease: "power2.out" }}, {T_CARD});',
        f'tl.fromTo("#card", {{ y: 160, scale: 0.84, rotationX: 38, rotationY: -20 }}, {{ y: 0, scale: 1, '
        f'rotationX: 13, rotationY: -9, duration: 0.95, ease: "power3.out" }}, {T_CARD});',
        f'tl.fromTo("#floor", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.9 }}, {T_CARD});',
        'tl.fromTo("#glare", { x: -420, opacity: 1 }, { x: 1300, opacity: 1, duration: 0.9, '
        'ease: "power2.inOut" }, 0.95);',
    ]
    ptr_t = 2.05
    if hl == "zoom":
        z = min(2.6, max(1.5, 560 / g["lw"]))
        fx = (c.W - ow) / 2 + lcx                      # ссылка в кадре до наезда
        fy = card_top + lcy
        target_y = 1130
        pill_s = min(1.0, (g["lw"] * 1.15 + 40) / pill_w)
        js += [
            f'tl.fromTo("#card", {{ rotationX: 13, rotationY: -9 }}, {{ rotationX: 2, rotationY: 0, duration: 0.9, '
            f'ease: "power3.inOut", immediateRender: false }}, {T_HL});',
            f'tl.fromTo("#cam", {{ x: 0, y: 0, scale: 1, transformOrigin: "{fx:.1f}px {fy:.1f}px" }}, '
            f'{{ x: {c.W / 2 - fx:.1f}, y: {target_y - fy:.1f}, scale: {z:.3f}, '
            f'transformOrigin: "{fx:.1f}px {fy:.1f}px", duration: 0.95, ease: "power3.inOut" }}, {T_HL});',
            f'tl.fromTo("#shot, #face > div", {{ filter: "blur(0px)" }}, {{ filter: "blur(5px)", duration: 0.7 }}, '
            f'{c.fmt(T_HL + 0.25)});' if g["img"] else
            f'tl.fromTo("#face", {{ opacity: 1 }}, {{ opacity: 0.55, duration: 0.7, immediateRender: false }}, '
            f'{c.fmt(T_HL + 0.25)});',
            f'tl.fromTo("#pill", {{ opacity: 0, scale: {pill_s * 0.7:.3f}, xPercent: -50, yPercent: -50 }}, '
            f'{{ opacity: 1, scale: {pill_s:.3f}, xPercent: -50, yPercent: -50, duration: 0.45, '
            f'ease: "back.out(1.8)" }}, {c.fmt(T_HL + 0.6)});',
            f'tl.fromTo("#lift", {{ z: 0 }}, {{ z: 30, duration: 0.45 }}, {c.fmt(T_HL + 0.6)});',
            f'tl.fromTo("#floor", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.5, immediateRender: false }}, {T_HL});',
            f'tl.fromTo("#pglow", {{ opacity: 0, scale: {pill_s:.3f}, xPercent: -50, yPercent: -50 }}, '
            f'{{ opacity: 0.55, scale: {pill_s:.3f}, xPercent: -50, yPercent: -50, duration: 0.5 }}, '
            f'{c.fmt(T_HL + 0.7)});',
        ]
        if layout != "overlay":
            js.append(f'tl.fromTo("#scrim", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.6 }}, {c.fmt(T_HL + 0.3)});')
        ptr_t = 2.35
        rip_scale = pill_s
        tap_dx, tap_dy = pill_w * pill_s * 0.18, pill_h * pill_s * 0.15
        lift_x = 0
    elif hl == "pop":
        js += [
            f'tl.fromTo("#card", {{ rotationX: 13, rotationY: -9 }}, {{ rotationX: 8, rotationY: -3, '
            f'duration: {c.fmt(dur - 1.15)}, ease: "sine.inOut", immediateRender: false }}, 1.15);',
            f'tl.fromTo("#dim", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.45 }}, {T_HL});',
            f'tl.fromTo("#slot", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3 }}, {c.fmt(T_HL + 0.1)});',
            f'tl.fromTo("#pill", {{ opacity: 0, scale: {s0:.3f}, xPercent: -50, yPercent: -50 }}, '
            f'{{ opacity: 1, scale: 1, xPercent: -50, yPercent: -50, duration: 0.6, ease: "back.out(1.5)" }}, '
            f'{c.fmt(T_HL + 0.04)});',
            f'tl.fromTo("#lift", {{ x: 0, y: 0, z: 0 }}, {{ x: {tx - lcx:.1f}, y: 34, z: 170, duration: 0.6, '
            f'ease: "back.out(1.3)" }}, {c.fmt(T_HL + 0.08)});',
            f'tl.fromTo("#pglow", {{ opacity: 0, xPercent: -50, yPercent: -50 }}, '
            f'{{ opacity: 0.6, xPercent: -50, yPercent: -50, duration: 0.5 }}, {c.fmt(T_HL + 0.3)});',
        ]
        rip_scale = 1.0
        tap_dx, tap_dy = pill_w * 0.2, pill_h * 0.12
        lift_x = tx - lcx
    else:   # click
        js += [
            f'tl.fromTo("#card", {{ rotationX: 13, rotationY: -9 }}, {{ rotationX: 8, rotationY: -3, '
            f'duration: {c.fmt(dur - 1.15)}, ease: "sine.inOut", immediateRender: false }}, 1.15);',
            f'tl.fromTo("#dim", {{ opacity: 0 }}, {{ opacity: 0.7, duration: 0.45 }}, {c.fmt(T_HL + 0.6)});',
            f'tl.fromTo("#mark", {{ opacity: 1, scaleX: 0 }}, {{ opacity: 1, scaleX: 1, duration: 0.35, '
            f'ease: "power2.out" }}, {c.fmt(T_HL + 0.7)});',
            f'tl.fromTo("#slot", {{ opacity: 0, scale: 1.2 }}, {{ opacity: 1, scale: 1, duration: 0.3, '
            f'ease: "back.out(2)" }}, {c.fmt(T_HL + 1.05)});',
        ]
        ptr_t = T_HL + 0.0
        rip_scale = (g["lw"] + 20) / pill_w
        tap_dx, tap_dy = g["lw"] * 0.25, g["lh"] * 0.2
        lift_x = 0

    # указатель: прилетает, нажимает; волны от места нажатия
    press = (T_HL + 1.15) if hl == "click" else ptr_t + 0.4
    if pointer != "none":
        if pointer == "cursor":
            js += [
                f'tl.fromTo("#ptr", {{ opacity: 0, x: {tap_dx + 260:.1f}, y: {tap_dy + 330:.1f} }}, '
                f'{{ opacity: 1, x: {tap_dx:.1f}, y: {tap_dy:.1f}, duration: {c.fmt(press - 0.08 - ptr_t)}, '
                f'ease: "power3.out" }}, {c.fmt(ptr_t)});',
                f'tl.fromTo("#ptr", {{ scale: 1 }}, {{ scale: 0.82, duration: 0.08, yoyo: true, repeat: 1, '
                f'immediateRender: false }}, {c.fmt(press)});',
            ]
        else:
            js += [
                f'tl.fromTo("#ptr", {{ opacity: 0, scale: 1.5, x: {tap_dx + 70:.1f}, y: {tap_dy + 90:.1f} }}, '
                f'{{ opacity: 1, scale: 1, x: {tap_dx:.1f}, y: {tap_dy:.1f}, duration: 0.38, ease: "power2.out" }}, '
                f'{c.fmt(press - 0.4)});',
                f'tl.fromTo("#ptr", {{ scale: 1 }}, {{ scale: 0.72, duration: 0.09, yoyo: true, repeat: 1, '
                f'immediateRender: false }}, {c.fmt(press)});',
                f'tl.fromTo("#ptr", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.35, immediateRender: false }}, '
                f'{c.fmt(press + 0.55)});',
            ]
    if hl != "click":
        js.append(f'tl.fromTo("#pill", {{ scale: {rip_scale:.3f} }}, {{ scale: {rip_scale * 0.93:.3f}, '
                  f'duration: 0.09, yoyo: true, repeat: 1, immediateRender: false }}, {c.fmt(press)});')
    for i in range(3):
        js.append(f'tl.fromTo("#rp{i}", {{ opacity: 0.95, scale: {rip_scale:.3f}, xPercent: -50, yPercent: -50 }}, '
                  f'{{ opacity: 0, scale: {rip_scale * (1.45 + 0.35 * i):.3f}, xPercent: -50, yPercent: -50, '
                  f'duration: 0.9, ease: "power2.out" }}, {c.fmt(press + 0.03 + i * 0.16)});')
    bub_t = press + 0.12
    if hl == "click":
        bub_y = (g["lh"] / 2 + 22 + pill_h / 2 + 24) * (1 if bub_below else -1)
        bub_x = tx - lcx
        js += [
            f'tl.fromTo("#bub", {{ opacity: 0, scale: 0.55, x: {bub_x:.1f}, y: {bub_y + 40:.1f}, '
            f'xPercent: -50, yPercent: -50 }}, {{ opacity: 1, scale: 1, x: {bub_x:.1f}, y: {bub_y:.1f}, '
            f'xPercent: -50, yPercent: -50, duration: 0.45, ease: "back.out(1.8)" }}, {c.fmt(bub_t)});',
            f'tl.fromTo("#lift", {{ z: 0 }}, {{ z: 60, duration: 0.45 }}, {c.fmt(bub_t)});',
        ]
    # дыхание в удержании: свечение плашки и редкие волны, чтобы кадр не замирал
    if hl != "click":
        js.append(f'tl.fromTo("#pglow", {{ opacity: 0.6 }}, {{ opacity: 0.25, duration: 0.7, yoyo: true, '
                  f'repeat: 1, ease: "sine.inOut", immediateRender: false }}, {c.fmt(press + 0.6)});')
    js.append(f'tl.fromTo("#rp3", {{ opacity: 0.7, scale: {rip_scale:.3f}, xPercent: -50, yPercent: -50 }}, '
              f'{{ opacity: 0, scale: {rip_scale * 1.6:.3f}, xPercent: -50, yPercent: -50, duration: 1.1, '
              f'ease: "power2.out" }}, {c.fmt(press + 1.4)});')
    js += [f'tl.fromTo("#br{i}", {{ scale: 1.25, opacity: 0.25 }}, {{ scale: 1.55, opacity: 0, duration: 1.6, '
           f'immediateRender: false }}, {c.fmt(press + 0.1 + i * 0.2)});' for i in range(3)]

    rips = "".join(ctr(f"rp{i}", "", "ctr rip") for i in range(4))
    ptr_html = ""
    if pointer == "cursor":     # кончик стрелки — в точке нажатия
        ptr_html = f'<div id="ptr" style="margin:-7px 0 0 -14px">{CURSOR}</div>'
    elif pointer == "tap":      # тап-кружок центрирован на точке нажатия
        ptr_html = '<div id="ptr" style="margin:-38px 0 0 -38px"><div id="tap"></div></div>'
    pill_inner = f'{CHAIN}<span>{c.esc(s["link"])}</span>'
    if hl == "click":           # клик по самой карточке: волны и курсор на поверхности, подсказка над ней
        surface = rips + ptr_html
        lift_inner = ctr("bub", pill_inner + f'<div class="tail{" up" if bub_below else ""}"></div>')
    else:                       # плашка над карточкой: волны и тап — вместе с ней
        surface = ""
        lift_inner = ctr("pglow", "") + rips + ctr("pill", pill_inner) + ptr_html
    face = face_html(s, g)
    if g["img"]:
        face = face.format(file_[1])
    card = ('<div id="card">'
            + "".join(f'<div class="edge" style="transform: translateZ({-5 * (i + 1)}px)"></div>' for i in range(3))
            + '<div id="bezel"></div>'
            f'<div id="face">{face}<div id="dim"></div><div id="mark"></div><div id="slot"></div>'
            '<div id="glare"></div></div>'
            f'<div id="pp">{surface}<div id="lift">{lift_inner}</div></div></div>')
    rings = '<div id="rings"><div id="halo"></div>' + "".join(f'<div class="bring" id="br{i}"></div>' for i in range(3)) + "</div>"
    scrim = '<div id="scrim"></div>' if (hl == "zoom" and layout != "overlay") else ""
    content = (f'<div id="cam"><div id="stage">{rings}<div id="floor"></div>'
               f'<div id="fade">{card}</div></div></div>{scrim}{h["html"]}')
    deco, deco_js = c.decor(pal, layout, s["tags"], dur, BLOBS)
    box = (head_top - 40, min(c.H, CARD_CY + oh / 2 + 120))
    body, bg, size = c.compose(pal, layout, deco, content, dur, box)
    js += deco_js

    names = {"pop": "выпуклая плашка", "click": "клик и подсказка", "zoom": "наезд к ссылке"}
    events = c.headline_events(h, times, label="призыв")
    if s["context"]:
        events.append(c.ev(0.02, f"строка-контекст «{s['context']}»"))
    src_name = "скриншот профиля" if g["img"] else f"нарисованная карточка «{s['name']}»"
    events += [
        c.ev(T_CARD, f"{src_name} появляется в 3D из размытия, кольца расходятся"),
        c.ev(1.15, "карточка видна целиком, наклон в 3D"),
        c.ev(0.95, "блик проходит по карточке"),
    ]
    if hl == "pop":
        events += [c.ev(T_HL, "остальная карточка приглушается, ссылка подсвечена на месте"),
                   c.ev(T_HL + 0.08, f"ссылка «{s['link']}» выходит из карточки плашкой к зрителю"),
                   c.ev(T_HL + 0.7, "плашка со ссылкой видна целиком")]
    elif hl == "zoom":
        events += [c.ev(T_HL, "камера ныряет к ссылке, карточка уходит в размытие"),
                   c.ev(T_HL + 0.6, f"плашка «{s['link']}» проявляется крупно"),
                   c.ev(T_HL + 1.05, "плашка со ссылкой видна целиком, крупно")]
    else:
        events += [c.ev(ptr_t, "курсор летит к ссылке"),
                   c.ev(T_HL + 0.7, "маркер под ссылкой"),
                   c.ev(T_HL + 1.05, "рамка вокруг ссылки")]
    if pointer != "none":
        events.append(c.ev(press, f"{'клик курсором' if pointer == 'cursor' else 'тап'} по ссылке, волны"))
    if hl == "click":
        events.append(c.ev(bub_t, f"всплывает подсказка «{s['link']}»"))
        events.append(c.ev(bub_t + 0.45, "подсказка со ссылкой видна целиком"))
    events.append(c.ev(press + 0.6, "удержание: свечение и редкие волны до конца"))
    describes = (f"концовка-ссылка ({names[hl]}): {src_name} в 3D-рамке, ссылка «{s['link']}» "
                 f"выделяется, призыв «{h['plain']}»; без кодового слова")
    style = c.base_css(pal, layout) + css(pal, g, col, pill_w, pill_h, layout)
    files = [file_] if file_ else []
    return c.result(style, body, js, dur, events, pal, layout, bg, size, files,
                    BASE_TAGS + [names[hl]], describes, preview_t=min(press + 0.9, dur - 0.1))
