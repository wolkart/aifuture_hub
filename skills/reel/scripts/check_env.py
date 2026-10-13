#!/usr/bin/env python3
"""Доктор /reel: что есть, чего не хватает. Только stdlib.

Красное — без этого не собрать ролик; жёлтое — работает с деградацией.
usage: check_env.py [--settings reel.settings.json] [--json]
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hf  # noqa: E402
import settings as settings_mod  # noqa: E402

HERE = Path(__file__).resolve().parent


def checks(s):
    out = []

    def add(level, name, note):
        out.append({"level": level, "name": name, "note": note})

    for tool, why in (("ffmpeg", "резка, склейка"), ("ffprobe", "длительности"), ("npx", "рендер HyperFrames"),
                      ("uv", "rough-cut, музыка, маска")):
        add("ok" if shutil.which(tool) else "red", tool, why)
    rc = HERE.parents[1] / "rough-cut" / "scripts" / "snap_words.py"
    add("ok" if rc.exists() else "red", "rough-cut", "соседний скилл — первая стадия /reel")
    add("ok" if sys.platform == "darwin" and shutil.which("swiftc") else "yellow", "Apple Vision",
        "взгляд на склейках и центр лица для наездов; без него — наезд от центра кадра")
    g = hf.CACHE / f"gsap-{hf.GSAP_VERSION}.min.js"
    add("ok" if g.exists() else "yellow", "GSAP", "скачается из npm при первой сборке слоя (~70 КБ)")
    if s is None:
        add("red", "настройки", "нет reel.settings.json: спроси тему и кодовое слово, предложи сохранить "
                                "(образец — assets/reel.settings.example.json)")
        return out
    add("ok", "настройки", str(s["path"]))
    t = s["theme"]
    for key, label in (("font_main", "шрифт основной"), ("font_display", "шрифт крупный")):
        p = t.get(key)
        add("ok" if p and Path(p).exists() else "red", label,
            str(p) if p else "не задан — без файла Chrome молча рисует фолбэком без кириллицы-стиля")
    m = s["music"]
    has_music = (m["track"] and Path(m["track"]).exists() and m["recipe"]) or (m["bed"] and Path(m["bed"]).exists())
    add("ok" if has_music else "yellow", "музыка", "трек с рецептом или готовая подложка; без неё — ролик без музыки")
    lib = s["folders"]["library"]
    add("ok" if lib and (Path(lib) / "index.json").exists() else "yellow", "библиотека ассетов",
        "index.json motion-assets; без неё — только б-роллы файлами и карточки")
    lessons = s["lessons"]
    add("ok" if lessons and Path(lessons).exists() else "yellow", "lessons.md",
        "прошлые правки автора; появится с первой правкой")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--settings", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    res = checks(settings_mod.load(args.settings))
    if args.json:
        print(json.dumps(res, ensure_ascii=False))
        return
    mark = {"ok": "✓", "yellow": "!", "red": "✗"}
    for r in res:
        print(f"{mark[r['level']]} {r['name']}: {r['note']}")
    if any(r["level"] == "red" for r in res):
        print("Есть красное — собрать ролик пока нельзя.")


if __name__ == "__main__":
    main()
