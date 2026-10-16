#!/usr/bin/env python3
"""Основа ролика: спикер с наездами + б-роллы по словам → <вариант>/main/index.html.

Видео основы — base.mp4 варианта (если собран «текст за головой») или черновик
roughcut.mp4. Длительность — из файла (ffprobe), куски — из cut-list rough-cut.
Вставки half: спикер уезжает вниз на 480 px, верх занимает б-ролл, между ними шов.
У пункта плана "enter": "down" — половина не появляется кадром, а съезжает сверху вниз
(жест «стянуть шторку»), спикер уезжает вниз вместе с ней за ENTER_S.
"film_roll": [{"from": <якорь>, "dur": 0.75, "cycles": 4}] — кадр-лента: кадр уезжает вверх,
за ним едет тот же кадр, всё быстрее, как плёнка в проекторе, и встаёт на место без шва.

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
ENTER_S = 0.4
FRAME_GAP = 40      # чёрная полоса между кадрами «плёнки»


def roll_durations(total, cycles, ratio=0.72):
    """Длительности проходов ленты: каждый следующий быстрее (ту-ту-ту-ту)."""
    w = [ratio ** i for i in range(cycles)]
    return [round(total * x / sum(w), 4) for x in w]


def landscape_frame(mode, w, h, faces):
    """Горизонтальный исходник в кадре 9:16. → (css, фон-html, лица в координатах кадра).
    face — обрезка по лицу: видео на весь кадр, сдвиг по медиане лица за ролик (кадр не
           прыгает); центр наездов пересчитывается в обрезанный кадр;
    blur — весь кадр по ширине посередине, за ним тот же ролик размытым на весь экран
           (скринкаст: обрезать нельзя, на экране всё нужное)."""
    import statistics
    if mode == "face":
        shown = w * 1920 / h
        cx = statistics.median(x for _, x, _ in faces) if faces else 0.5
        pos = min(1.0, max(0.0, (cx * shown - 540) / (shown - 1080))) if shown > 1080 else 0.5
        off = (1080 - shown) * pos
        mapped = [(t, (off + x * shown) / 1080, y) for t, x, y in faces]
        return f"#cam video {{ object-position: {pos * 100:.1f}% 50%; }}", "", mapped
    hh = 1080 * h / w
    top = (1920 - hh) / 2
    css = ("#cam video { object-fit: contain; }\n"
           "#bgblur { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; "
           "filter: blur(40px) brightness(0.55); transform: scale(1.15); }")
    mapped = [(t, x, (top + y * hh) / 1920) for t, x, y in faces]
    return css, "blur", mapped


def render_html(dur, zoom_rows, brolls, halves, seam_color, media_names, rolls=(), frame=("", "")):
    js, body = [], []
    for r in zoom_rows:
        js += r["js"]
    for n, r in enumerate(brolls):
        h = 960 if r["layout"] == "half" else 1920
        rate = f' data-playback-rate="{r["rate"]:g}"' if r["rate"] != 1 else ""
        if r.get("enter") == "down" and r["layout"] == "half":
            js.append(f'tl.fromTo("#br{n}", {{y: -960}}, {{y: 0, duration: {ENTER_S}, ease: "power3.out"}}, '
                      f'{r["a"]:.3f});')
        body.append(f'<video id="br{n}" src="{media_names[n]}" data-start="{r["a"]:.3f}" '
                    f'data-duration="{r["b"] - r["a"]:.3f}" data-media-start="{r["in"]:.3f}"{rate} '
                    f'data-track-index="{1 + n % 2}" muted playsinline style="position:absolute; left:0; top:0; '
                    f'width:1080px; height:{h}px; object-fit:cover; object-position:{r["pos"]}; z-index:2"></video>')
    for k, (a, b) in enumerate(halves):
        slide = any(r.get("enter") == "down" and abs(r["a"] - a) < 0.02 for r in brolls)
        if slide:   # спикер уезжает вниз вместе с въезжающей сверху половиной
            js.append(f'tl.fromTo("#cam", {{y: 0}}, {{y: {HALF_Y}, duration: {ENTER_S}, ease: "power3.out"}}, '
                      f'{a:.3f}); tl.set("#cam", {{y: 0}}, {b:.3f});')
        else:
            js.append(f'tl.set("#cam", {{y: {HALF_Y}}}, {a:.3f}); tl.set("#cam", {{y: 0}}, {b:.3f});')
        body.append(f'<div id="seam{k}" class="clip" data-start="{a:.3f}" data-duration="{b - a:.3f}" '
                    f'data-track-index="3" style="position:absolute; left:0; top:956px; width:1080px; height:8px; '
                    f'background:{seam_color}; inset:auto; z-index:3"></div>')
    css = """
#cam { position: absolute; inset: 0; will-change: transform; z-index: 1; }
#cam video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
#reel { position: absolute; inset: 0; background: #000; will-change: transform; }
""" + frame[0]
    copies, step = [], 1920 + FRAME_GAP
    for k, (ra, rd, cycles) in enumerate(rolls):
        for vid, off in ((f"fu{k}", -step), (f"fd{k}", step)):
            copies.append(f'<video id="{vid}" src="base.mp4" data-start="{ra:.3f}" data-duration="{rd:.3f}" '
                          f'data-media-start="{ra:.3f}" data-track-index="{5 + k}" playsinline muted '
                          f'style="inset:auto; left:0; top:{off}px; width:1080px; height:1920px"></video>')
        t = ra
        durs = roll_durations(rd, cycles)
        for i, d in enumerate(durs):
            ease = "power2.out" if i == len(durs) - 1 else ("power2.in" if i == 0 else "none")
            js.append(f'tl.fromTo("#reel", {{y: 0}}, {{y: {-step}, duration: {d}, ease: "{ease}", '
                      f'immediateRender: false}}, {t:.3f});')
            t += d
        js.append(f'tl.set("#reel", {{y: 0}}, {t:.3f});')
    cam = (f'<div id="cam" class="inner"><div id="reel"><video id="base" src="base.mp4" data-start="0" '
           f'data-duration="{dur:.3f}" data-track-index="0" playsinline muted></video>{"".join(copies)}</div></div>')
    bg = ""
    if frame[1]:   # размытый фон: тот же ролик за кадром, на своей дорожке
        bg = (f'<video id="bgblur" src="base.mp4" data-start="0" data-duration="{dur:.3f}" '
              f'data-track-index="9" playsinline muted></video>')
        css = css.replace("#reel { position: absolute; inset: 0; background: #000;",
                          "#reel { position: absolute; inset: 0; background: transparent;")
    return hf.page(css, bg + cam + "\n" + "\n".join(body), "\n".join(js), dur, bg="#000")


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
    faces = zoom.load_faces(b.faces) if b.faces.exists() else []
    frame = ("", "")
    w, h = hf.size(base_src)
    if w > h:   # горизонтальный исходник (шортс из длинного ролика) — ставим в 9:16
        mode = plan.get("frame") or ("face" if faces else "blur")
        css, bg, faces = landscape_frame(mode, w, h, faces)
        frame = (css, bg)
        print(f"кадр: горизонтальный {w}×{h} → 9:16, {'по лицу' if mode == 'face' else 'весь кадр на размытом фоне'}"
              f" (в плане \"frame\": face | blur)")
    if plan.get("zoom", True):
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
    rolls = [(round(at(r["from"]), 3), float(r.get("dur", 0.75)), int(r.get("cycles", 4)))
             for r in plan.get("film_roll", [])]
    hf.setup_project(b.main, s["theme"], [(src, name) for name, src in files.items()])
    (b.main / "index.html").write_text(
        render_html(dur, rows, brolls, halves, s["theme"]["bg_dark"][-1], media, rolls, frame),
        encoding="utf-8")
    for ra, rd, cyc in rolls:
        print(f"кадр-лента: {ra:.2f}–{ra + rd:.2f} с, {cyc} прохода, всё быстрее")

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
