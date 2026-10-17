"""Настройки автора: reel.settings.json вне скилла. Только stdlib.

Скилл обезличен: тема, шрифты, акценты, стиль субтитров, музыка, словарь замен,
CTA и папки живут в файле автора. Ключи файла — русские (его правит человек),
внутри скриптов — нормализованный словарь с английскими ключами.

Где искать файл (первое найденное):
  1. явный путь (--settings);
  2. REEL_SETTINGS из окружения или из .env рядом со скиллом;
  3. ./reel.settings.json, ./reel/reel.settings.json от текущей папки.
Относительные пути внутри файла считаются от папки самого файла.
Ключи с «_» в начале — комментарии автора, скрипты их не читают.
"""
import json
import os
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

CAPTION_STYLES = {"строки": "lines", "по_слову": "word", "капс": "caps",
                  "lines": "lines", "word": "word", "caps": "caps"}
WORD_ANIMS = {"приближение": "pop", "без_анимации": "none", "волна": "wave",
              "pop": "pop", "none": "none", "wave": "wave"}
# CTA ролика: кодовое слово в комменты (карточка cta) или 3D-концовка со ссылкой
# (ассет end_card из motion-assets). В одном ролике одно из двух.
CTA_TYPES = {"код": "code", "ссылка": "link", "code": "code", "link": "link"}

# Нейтральная палитра на случай, если в файле чего-то нет. Свой стиль — в файле автора.
DEFAULT_THEME = {
    "bg_dark": ["#1E1E2E", "#050508"],
    "bg_light": ["#FFFFFF", "#EEF1F7"],
    "text_dark": "#2B2B3A",
    "secondary": "#5B8DEF",
    "muted": "#9A9AB0",
    "success": "#4CC38A",
    "danger": "#FF3B1F",
    "accent": {"name": "по_умолчанию", "solid": "#F2A93B", "on_light": "#B8740A", "gradient": None},
}


def load_env(path=None):
    """`.env` рядом со скиллом → os.environ, не перебивая уже заданное."""
    path = Path(path) if path else SKILL_ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("\"'")
        if key and value and not os.environ.get(key):
            os.environ[key] = value


def find(explicit=None, cwd=None):
    if explicit:
        return Path(explicit).expanduser()
    load_env()
    env = os.environ.get("REEL_SETTINGS")
    if env:
        return Path(env).expanduser()
    cwd = Path(cwd or os.getcwd())
    for cand in (cwd / "reel.settings.json", cwd / "reel" / "reel.settings.json"):
        if cand.exists():
            return cand
    return None


def lessons_path(settings_path):
    return Path(settings_path).parent / "lessons.md"


def _path(base, value):
    if not value:
        return None
    p = Path(str(value)).expanduser()
    return p if p.is_absolute() else (base / p).resolve()


def _first(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default


def accent(theme_raw, name=None):
    """Акцент по имени из «акценты» (или строка-цвет). Градиент — только у ударных слов
    субтитров; в карточках сплошной цвет."""
    name = name or theme_raw.get("акцент")
    table = theme_raw.get("акценты") or {}
    if isinstance(name, str) and name.startswith("#"):
        return {"name": name, "solid": name, "on_light": name, "gradient": None}
    a = table.get(name) if name else None
    if not a:
        return dict(DEFAULT_THEME["accent"])
    grad = a.get("градиент")
    solid = a.get("на_тёмном") or (grad[-1] if grad else DEFAULT_THEME["accent"]["solid"])
    on_light = a.get("на_светлом") or solid
    if isinstance(on_light, list):
        on_light = on_light[-1]
    return {"name": name, "solid": solid, "on_light": on_light, "gradient": grad or None}


def cta_type(value, default="code"):
    """«код» | «ссылка» (или code | link) → "code" | "link"; пусто или опечатка — default."""
    return CTA_TYPES.get(str(value or "").strip().lower(), default)


def resolve(raw, base_dir, accent_name=None, caption_style=None):
    """Сырой файл → нормализованный словарь. accent_name/caption_style — переопределение
    на один ролик (ротация акцентов и стилей для сравнения)."""
    base = Path(base_dir)
    t = raw.get("тема") or {}
    fonts = t.get("шрифты") or {}
    theme = {
        "bg_dark": t.get("фон_тёмный") or DEFAULT_THEME["bg_dark"],
        "bg_light": t.get("фон_светлый") or DEFAULT_THEME["bg_light"],
        "text_dark": t.get("текст_тёмный") or DEFAULT_THEME["text_dark"],
        "secondary": t.get("вторичный") or DEFAULT_THEME["secondary"],
        "muted": t.get("приглушённый") or DEFAULT_THEME["muted"],
        "success": t.get("служебный_успех") or DEFAULT_THEME["success"],
        "danger": t.get("служебный_огонь") or DEFAULT_THEME["danger"],
        "font_main": _path(base, fonts.get("основной")),
        "font_display": _path(base, _first(fonts, "цифры_и_крупно", "крупный")),
        "accent": accent(t, accent_name),
    }
    c = raw.get("субтитры") or {}
    style = CAPTION_STYLES.get(caption_style or c.get("стиль") or "строки", "lines")
    anim_raw = c.get("появление_слова")
    if isinstance(anim_raw, dict):
        anim_raw = anim_raw.get("по_умолчанию")
    back = c.get("подложка") or {}
    captions = {
        "style": style,
        "anim": WORD_ANIMS.get(anim_raw or "приближение", "pop"),
        "pop_from": float(c.get("приближение_с", 0.8)),
        "word_px": int(c.get("размер_слова_px", 72)),
        "line_px": int(c.get("размер_строки_px", 58)),
        "top_px": int(c.get("верх_px") or {"word": 1250, "caps": 1300}.get(style, 1385)),
        "caps_px": int(c.get("размер_капс_px", 104)),
        "top_half_px": int(c.get("верх_на_half_px", 880)),
        "backing": {
            "color": back.get("цвет") or theme["bg_dark"][-1],
            "opacity": float(back.get("плотность", 0.6)),
            "wide_em": float(back.get("шире_em", 1.5)),
            "tall_em": float(back.get("выше_em", 0.7)),
            "blur_px": int(back.get("размытие_px", 18)),
        },
    }
    snd = raw.get("звук") or {}
    m = raw.get("музыка") or {}
    rec = m.get("рецепт") or {}
    music = {
        "track": _path(base, m.get("трек")),
        "bed": _path(base, _first(m, "подложка", "подложка_3мин")),
        "recipe": None,
        "rel_lu": float(m.get("уровень_LU_к_голосу", -12)),
        "pause_lift_db": float(m.get("подъём_в_паузах_dB", 6)),
    }
    if rec.get("цикл"):
        quiet = rec.get("тихая_зона_для_конца") or [rec["цикл"][1], rec["цикл"][1] + 5]
        music["recipe"] = {
            "start": float(rec.get("старт", 0.0)),
            "loop": [float(x) for x in rec["цикл"]],
            "quiet_end": [float(x) for x in quiet],
            "min_start": float(rec.get("мин_старт", 0.0)),
            "xfade": float(rec.get("кроссфейд_с", 0.03)),
        }
    e = raw.get("монтаж") or {}
    z = e.get("наезды") or {}
    whoosh = z.get("вжух") or {}
    br = e.get("броллы") or {}
    folders = raw.get("папки") or {}
    brolls = folders.get("броллы") or []
    if isinstance(brolls, str):
        brolls = [brolls]
    return {
        "theme": theme,
        "captions": captions,
        "audio": {"voice_lufs": float(snd.get("громкость_голоса_LUFS", -14)),
                  "true_peak": float(snd.get("true_peak", -1.5))},
        "music": music,
        "dictionary": dict(raw.get("словарь_замен") or {}),
        "cta": raw.get("cta") or {},
        "cta_type": cta_type((raw.get("cta") or {}).get("тип")),
        "edit": {
            "zoom_levels": [float(x) for x in (z.get("уровни") or [1.15, 1.35])],
            "punch_add": float(whoosh.get("плюс", 0.12)),
            "punch_dur": float(whoosh.get("за_с", 0.16)),
            "layouts": e.get("раскладки") or ["full", "half"],
            "behind_text": bool(e.get("текст_за_головой", False)),
            "insert_len": [float(x) for x in (br.get("вставка_с") or [0.5, 1.8])],
        },
        "folders": {
            "library": _path(base, folders.get("библиотека_ассетов")),
            "brolls": [_path(base, b) for b in brolls],
            "sfx": _path(base, folders.get("звуки")),
        },
    }


def load(path=None, accent_name=None, caption_style=None):
    """Найти и прочитать настройки. Нет файла — None (скилл спрашивает минимум)."""
    p = find(path)
    if p is None or not p.exists():
        return None
    raw = json.loads(p.read_text(encoding="utf-8"))
    s = resolve(raw, p.parent, accent_name, caption_style)
    s["path"] = p
    s["lessons"] = lessons_path(p)
    return s


def default():
    """Настройки без файла: нейтральная тема, субтитры строками."""
    s = resolve({}, Path.cwd())
    s["path"] = None
    s["lessons"] = None
    return s
