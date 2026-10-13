#!/usr/bin/env python3
"""Основа ролика: спикер с наездами + б-роллы по словам → <вариант>/main/index.html.

Видео основы — base.mp4 варианта (если собран «текст за головой») или черновик
roughcut.mp4. Длительность — из файла (ffprobe), куски — из cut-list rough-cut.
Вставки half: спикер уезжает вниз на 480 px, верх занимает б-ролл, между ними шов.

usage: build_main.py <папка варианта> [--settings reel.settings.json] [--library <папка>]
Затем: npx hyperframes render <вариант>/main → main.mp4 (команду печатает скрипт).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hf  # noqa: E402
import inserts as ins  # noqa: E402
import settings as settings_mod  # noqa: E402
import words as wmod  # noqa: E402
import zoom  # noqa: E402
from layout import Build  # noqa: E402

HALF_Y = 480


def render_html(dur, zoom_rows, brolls, halves, seam_color, media_names):
    js, body = [], []
    for r in zoom_rows:
        js += r["js"]
    for n, r in enumerate(brolls):
        h = 960 if r["layout"] == "half" else 1920
        rate = f' data-playback-rate="{r["rate"]:g}"' if r["rate"] != 1 else ""
        body.append(f'<video id="br{n}" src="{media_names[n]}" data-start="{r["a"]:.3f}" '
                    f'data-duration="{r["b"] - r["a"]:.3f}" data-media-start="{r["in"]:.3f}"{rate} '
                    f'data-track-index="{1 + n % 2}" muted playsinline style="position:absolute; left:0; top:0; '
                    f'width:1080px; height:{h}px; object-fit:cover; object-position:{r["pos"]}; z-index:2"></video>')
    for k, (a, b) in enumerate(halves):
        js.append(f'tl.set("#cam", {{y: {HALF_Y}}}, {a:.3f}); tl.set("#cam", {{y: 0}}, {b:.3f});')
        body.append(f'<div id="seam{k}" class="clip" data-start="{a:.3f}" data-duration="{b - a:.3f}" '
                    f'data-track-index="3" style="position:absolute; left:0; top:956px; width:1080px; height:8px; '
                    f'background:{seam_color}; inset:auto; z-index:3"></div>')
    css = """
#cam { position: absolute; inset: 0; will-change: transform; z-index: 1; }
#cam video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
"""
    cam = (f'<div id="cam" class="inner"><video id="base" src="base.mp4" data-start="0" '
           f'data-duration="{dur:.3f}" data-track-index="0" playsinline muted></video></div>')
    return hf.page(css, cam + "\n" + "\n".join(body), "\n".join(js), dur, bg="#000")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("variant")
    ap.add_argument("--settings", default=None)
    ap.add_argument("--library", default=None)
    args = ap.parse_args()

    b = Build(args.variant)
    plan = b.load_plan()
    s = (settings_mod.load(args.settings, plan.get("accent"), plan.get("captions"))
         or settings_mod.default())
    words = wmod.load(b.transcript)
    base_src = b.base if b.base.exists() else b.roughcut
    dur = round(hf.duration(base_src) - 0.02, 3)
    at = lambda a: wmod.at(words, a)  # noqa: E731

    lib_dir = Path(args.library) if args.library else s["folders"]["library"]
    library = json.loads((lib_dir / "index.json").read_text(encoding="utf-8")) \
        if lib_dir and (lib_dir / "index.json").exists() else None
    search = [b.export.parent] + list(s["folders"]["brolls"])
    brolls, _, _, problems = ins.resolve(plan.get("items", []), at, dur, library, lib_dir, search,
                                         s["edit"]["insert_len"])
    errors = [p for p in problems if p["level"] == "error"]
    for p in problems:
        print(f"{'✗' if p['level'] == 'error' else '⚠'} {p['where']}: {p['text']}")
    if errors:
        raise SystemExit("build_main: в плане ошибки — правь plan.json (см. выше)")

    spans = [(a, min(bb, dur)) for a, bb in ins.spans_from_cutlist(json.loads(b.cutlist.read_text()))
             if a < dur] if b.cutlist.exists() else [(0.0, dur)]
    rows = []
    if plan.get("zoom", True):
        faces = zoom.load_faces(b.faces) if b.faces.exists() else []
        if not faces:
            print("⚠ faces.csv нет — центр наезда по умолчанию (запусти face_centers.py)")
        plates = b.read_json(b.windows, []) if plan.get("behind_text") else []
        rows = zoom.plan(spans, words, plan.get("punch_words", []), faces, plates,
                         s["edit"]["zoom_levels"], s["edit"]["punch_add"], s["edit"]["punch_dur"])
    halves = ins.half_windows(brolls)
    b.write_json(b.half_windows, halves)

    media, files = [], {"base.mp4": base_src}
    for r in brolls:
        if not r["path"] or not Path(r["path"]).exists():
            raise SystemExit(f"build_main: нет файла б-ролла для пункта #{r['n'] + 1}: {r['path']}")
        name = f"{r.get('asset') or Path(r['path']).stem}{Path(r['path']).suffix}"
        files[name] = r["path"]
        media.append(name)
    hf.setup_project(b.main, s["theme"], [(src, name) for name, src in files.items()])
    (b.main / "index.html").write_text(
        render_html(dur, rows, brolls, halves, s["theme"]["bg_dark"][-1], media), encoding="utf-8")

    for r in rows:
        print(f"{r['i']:2d} {r['a']:6.2f}–{r['b']:6.2f} | {r['kind']:28s} | центр {r['origin']}")
    for r in brolls:
        word = wmod.first_at_or_after(words, r["a"], 0.3)
        print(f"   {r['a']:6.2f}–{r['b']:6.2f} ({r['b'] - r['a']:.2f} с) {r['layout']:4s} | "
              f"{Path(str(r['path'])).name} @{r['in']:.1f}" + (f" ×{r['rate']:g}" if r["rate"] != 1 else "")
              + (f" | «{word['text']} …»" if word else ""))
    print(f"вставок {len(brolls)}, под б-роллами {ins.coverage(brolls, dur):.1f} с из {dur:.1f}")
    print("рендер: " + " ".join(hf.render_cmd(b.main, b.main_mp4)))


if __name__ == "__main__":
    main()
