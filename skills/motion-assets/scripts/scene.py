#!/usr/bin/env python3
"""Сцена из шаблона → проект HyperFrames в библиотеке + запись в index.json. Только stdlib.

  scene.py list [--json]                              — шаблоны и их слоты
  scene.py <шаблон> --id <id> [--slots slots.json] [--theme dark|light]
           [--layout full|half|overlay] [--library <папка>] [--settings <файл>]
           [--tags a,b] [--describes "…"] [--render] [--quality draft|standard|high]

Проект ложится в <библиотека>/<id>/ (index.html + assets/ с GSAP и шрифтами темы).
Тема — из reel.settings.json автора (нет файла — нейтральная). С --render:
  full/half → <id>.mp4 (half — 1080×960, верхняя половина кадра; шаблоны wide_* — 1920×1080);
  overlay   → <id>.mov (ProRes 4444 с альфой; альфа проверяется ffprobe) +
              <id>-green.mp4 (на сплошном #00FF00 — хромакей в CapCut);
  превью    → <id>-preview.png (момент, когда сцена собрана целиком);
  звуки     → <id>-sfx.wav по событиям шаблона (у кого они есть — шаблоны wide_*) и та же
              дорожка внутри .mov/.mp4 — в монтажке кладётся одним файлом. Синтез — reel/scripts/sfx.py
              (свои WAV из папки звуков в настройках перебивают синтез по имени).
Затем запись в index.json добавляется или заменяется по id: опись событий — из
таймингов самого шаблона.
Относительный путь иконки в slots.json считается от папки slots.json.
"""
import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
sys.path.insert(0, str(HERE.parents[1] / "reel" / "scripts"))
sys.path.insert(0, str(TEMPLATES))
sys.path.insert(0, str(HERE))

import _common     # noqa: E402  (templates/)
import glyphs      # noqa: E402  (reel/scripts/)
import hf          # noqa: E402  (reel/scripts/)
import library     # noqa: E402
import settings    # noqa: E402  (reel/scripts/)

ALPHA_FMTS = ("yuva", "rgba", "argb", "bgra", "abgr", "gbrap", "ya")
GREEN = "0x00FF00"
MEDIA_EXT = (".svg", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".m4v", ".webm")


def list_templates():
    return sorted(p.stem for p in TEMPLATES.glob("*.py") if not p.stem.startswith("_"))


def load_template(name):
    if name not in list_templates():
        raise SystemExit(f"нет шаблона {name!r}; есть: {', '.join(list_templates())}")
    return importlib.import_module(name)


def resolve_paths(slots, base):
    """Относительные пути картинок и записей в слотах — от папки slots.json, и во вложенных
    списках и словарях тоже (иконки пунктов, обложки роликов)."""
    if isinstance(slots, dict):
        return {k: resolve_paths(v, base) for k, v in slots.items()}
    if isinstance(slots, list):
        return [resolve_paths(v, base) for v in slots]
    if isinstance(slots, str) and Path(slots).suffix.lower() in MEDIA_EXT:
        p = Path(slots).expanduser()
        if not p.is_absolute() and (base / p).exists():
            return str((base / p).resolve())
    return slots


def write_project(tpl, slots, theme, project_dir, kind=None, layout="full"):
    """index.html + assets/ в project_dir. → результат build шаблона."""
    built = tpl.build(slots, theme, kind=kind, layout=layout)
    fonts = hf.setup_project(project_dir, theme, extra=built["files"])
    w, h = built["size"]
    page = hf.page(built["css"], built["body"], built["js"], built["duration"], fonts,
                   bg=built["bg"], w=w, h=h)
    (Path(project_dir) / "index.html").write_text(page, encoding="utf-8")
    for line in glyphs.report(glyphs.check(page, theme.get("font_main"), theme.get("font_display")), "сцена"):
        print(line)
    return built


def pix_fmt(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                   "-show_entries", "stream=pix_fmt", "-of", "csv=p=0", str(path)])
    return out.decode().strip()


def has_alpha(fmt):
    return any(fmt.startswith(p) for p in ALPHA_FMTS)


def prores_cmd(src, out, decoder=None):
    """В ProRes 4444 с альфой. decoder libvpx-vp9 — для webm: родной декодер теряет альфу."""
    pre = ["-c:v", decoder] if decoder else []
    return (["ffmpeg", "-y", "-v", "error"] + pre + ["-i", str(src), "-c:v", "prores_ks",
            "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-an", str(out)])


def green_cmd(mov, out, w, h, fps=hf.FPS):
    return ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c={GREEN}:s={w}x{h}:r={fps}",
            "-i", str(mov), "-filter_complex", "[0:v][1:v]overlay=shortest=1,format=yuv420p",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-an", str(out)]


def preview_cmd(src, t, out):
    """Кадр в момент t: -ss после -i — точный кадр."""
    return ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ss", f"{t:.3f}", "-frames:v", "1", str(out)]


SFX = HERE.parents[1] / "reel" / "scripts" / "sfx.py"


def add_sfx(project, id_, built, files, settings_path=None):
    """Звуки сцены: <id>-sfx.wav + та же дорожка внутри видео. Нет меток — ничего не делает."""
    cues = built.get("sfx") or []
    if not cues:
        return files
    p = Path(project)
    cj, wav = p / f"{id_}-sfx.json", p / f"{id_}-sfx.wav"
    cj.write_text(json.dumps(cues, ensure_ascii=False), encoding="utf-8")
    cmd = ["uv", "run", "-q", str(SFX), "cues", str(cj), "--out", str(wav), "--total", f"{built['duration']:.3f}"]
    if settings_path:
        cmd += ["--settings", str(settings_path)]
    subprocess.run(cmd, check=True, capture_output=True)
    cj.unlink()
    for role in ("mov_alpha", "green", "mp4"):
        if role not in files:
            continue
        vid = p / files[role]
        tmp = vid.with_name(vid.stem + ".tmp" + vid.suffix)
        acodec = ["-c:a", "pcm_s16le"] if vid.suffix == ".mov" else ["-c:a", "aac", "-b:a", "192k"]
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(vid), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy"] + acodec + ["-shortest", str(tmp)], check=True)
        tmp.replace(vid)
    files["sfx"] = wav.name
    return files


def render(project, id_, built, quality=None):
    """Рендер под раскладку. → {роль: имя файла в папке проекта}."""
    p = Path(project)
    files = {}
    if built["layout"] == "overlay":
        mov = p / f"{id_}.mov"
        hf.render(p, mov, "mov", quality)
        if not has_alpha(pix_fmt(mov)):
            webm = p / f"{id_}.webm"
            hf.render(p, webm, "webm", quality)
            subprocess.run(prores_cmd(webm, mov, "libvpx-vp9"), check=True)
            webm.unlink()
        green = p / f"{id_}-green.mp4"
        w, h = built["size"]
        subprocess.run(green_cmd(mov, green, w, h), check=True)
        files.update(mov_alpha=mov.name, green=green.name)
        src = mov
    else:
        mp4 = p / f"{id_}.mp4"
        hf.render(p, mp4, "mp4", quality)
        files["mp4"] = mp4.name
        src = mp4
    prev = p / f"{id_}-preview.png"
    subprocess.run(preview_cmd(src, built["preview_t"], prev), check=True)
    files["preview"] = prev.name
    return files


def entry_for(id_, name, built, slots, files, extra_tags=(), describes=None):
    tags = list(dict.fromkeys(list(built["tags"]) + [t for t in extra_tags if t]))
    return {
        "id": id_, "kind": "overlay" if built["layout"] == "overlay" else "scene",
        "layout": built["layout"], "duration": built["duration"], "theme": built["theme_kind"],
        "tags": tags, "describes": describes or built["describes"], "events": built["events"],
        "template": name, "slots": slots,
        "files": {role: f"{id_}/{fname}" for role, fname in files.items()},
    }


def print_list(as_json):
    data = []
    for name in list_templates():
        t = load_template(name)
        data.append({"name": name, "title": t.TITLE, "theme": t.DEFAULT_KIND,
                     "doc": (t.__doc__ or "").strip().split("\n\n")[0],
                     "slots": {k: {"about": v["about"], "default": v["default"]}
                               for k, v in t.SLOTS.items()}})
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    for d in data:
        print(f"{d['name']} — {d['title']} ({'тёмная' if d['theme'] == 'dark' else 'светлая'})")
        for k, v in d["slots"].items():
            print(f"    {k}: {v['about']}  [по умолчанию: {json.dumps(v['default'], ensure_ascii=False)}]")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("template", help="имя шаблона или list")
    ap.add_argument("--id")
    ap.add_argument("--slots", help="JSON-файл со слотами (чего нет — дефолт шаблона)")
    ap.add_argument("--theme", choices=("dark", "light"), help="по умолчанию — родная тема шаблона")
    ap.add_argument("--layout", choices=("full", "half", "overlay"),
                    help="по умолчанию — раскладка шаблона (у вертикальных full, у 16:9 — своя)")
    ap.add_argument("--library")
    ap.add_argument("--settings")
    ap.add_argument("--accent", help="акцент из настроек на эту сцену (по имени)")
    ap.add_argument("--tags", default="", help="доп. теги через запятую")
    ap.add_argument("--describes", help="своё описание вместо собранного из слотов")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--quality", choices=("draft", "standard", "high"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.template == "list":
        print_list(args.json)
        return 0
    if not args.id:
        raise SystemExit("нужен --id <id> (имя папки и записи в index.json)")
    tpl = load_template(args.template)
    s = settings.load(args.settings, accent_name=args.accent)
    theme_note = "" if s else " (нет reel.settings.json — нейтральная тема)"
    theme = (s or settings.default())["theme"]
    lib = library.resolve_library(args.library, args.settings)

    slots = {}
    if args.slots:
        sp = Path(args.slots)
        slots = resolve_paths(json.loads(sp.read_text(encoding="utf-8")), sp.resolve().parent)
    merged = _common.merge_slots(tpl.SLOTS, slots)
    project = lib / args.id
    layout = args.layout or getattr(tpl, "DEFAULT_LAYOUT", "full")
    built = write_project(tpl, merged, theme, project, args.theme, layout)
    files = {"project": "index.html"}
    if args.render:
        files.update(render(project, args.id, built, args.quality))
        files = add_sfx(project, args.id, built, files, args.settings)
    entry = entry_for(args.id, args.template, built, merged, files,
                      [t.strip() for t in args.tags.split(",")], args.describes)
    index_file = library.put(lib, entry)
    catalog_html = library.refresh_catalog(lib)

    if args.json:
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return 0
    print(f"Сцена: {args.template} → {project}{theme_note}")
    print(f"  {entry['kind']}/{entry['layout']}/{entry['theme']}, {entry['duration']} с, "
          f"{built['size'][0]}×{built['size'][1]}")
    for ev in entry["events"]:
        print(f"  {ev['t']:>5.2f}  {ev['what']}")
    for role, rel in entry["files"].items():
        print(f"  {role}: {lib / rel}")
    if not args.render:
        print("  рендер: тот же вызов с --render")
    print(f"Индекс: {index_file}")
    if catalog_html:
        print(f"Каталог: {catalog_html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
