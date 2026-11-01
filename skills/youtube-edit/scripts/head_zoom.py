#!/usr/bin/env python3
"""Лёгкий зум на говорящей голове там, где нет непрозрачной графики (автор 2026-10-19: «нигде нет
зума на меня, когда говорю без графики»). Перенос zoom16 из news-reposter на таймлайн резки:
  • статики нет: каждый кусок между склейками двигается; ходы по кругу — быстрый наезд с
    удержанием, медленный отъезд, медленный наезд, быстрый отъезд; уровни 1,00 / 1,06 / 1,12;
  • на склейке масштаб прыгает ≥ 0,06 или кусок сразу начинается быстрым ходом — прячет скачок;
  • рядом с панелью (wide_drawer: там лицо без зума) кадр приходит к 1,00 плавно и с 1,00 же
    стартует; после сцены на весь кадр — жёсткая склейка, можно любой;
  • акценты (прозрачные, дорожка выше) зуму не мешают — лежат поверх.
Куски головы — scan.json (лицо ≥ 12 % ширины кадра), склейки — cut-list. Рендер — HyperFrames: кусок
таймлайна (timeline.py piece) в #cam, масштаб GSAP (плавно, без дрожи zoompan). Выход — clips/zoom-NN/
zoom-NN.mp4 без звука (голос — на V1) + zoom.json для сборки.

  python3 head_zoom.py <export/монтаж> [--render] [--cutlist …] [--settings …]
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "reel" / "scripts"))
import hf        # noqa: E402
import stage     # noqa: E402
import timeline  # noqa: E402

LO, MID, HI = 1.0, 1.06, 1.12
FAST, MIN_STEP, GLIDE, MIN_REGION = 0.3, 0.06, 1.0, 1.2
W, H = timeline.W, timeline.H


def covers(clips):
    """Непрозрачная графика на таймлайне: [(a, b, «face» — панель с лицом без зума | «full»)]."""
    out = []
    for c in clips:
        if c.get("layout") == "full" and c.get("dur"):          # непрозрачный клип: под ним V1 не видно — зум не нужен
            out.append((c["start"], c["start"] + c["dur"], "face" if c.get("template") == "wide_drawer" else "full"))
    return sorted(out)


def regions(heads, cov, min_region=MIN_REGION):
    """Куски головы без непрозрачной графики: [(a, b, что до, что после)]; «что» — face | full | cut."""
    res = []
    for ha, hb in heads:
        t, before = ha, "cut"
        for a, b, kind in cov + [(hb, hb, "cut")]:
            if b <= t or a >= hb + 0.01:
                continue
            if a - t >= min_region:
                res.append((round(t, 3), round(min(a, hb), 3), before, kind if a < hb else "cut"))
            t, before = max(t, b), kind
            if t >= hb:
                break
    return res


ROTATION = [("in", True, LO, HI), ("out", False, MID, LO), ("in", False, MID, HI), ("out", True, MID, LO)]


def plan(a, b, before, after, cuts, origin="47% 44%"):
    """Ходы камеры в куске [a, b): склейки внутри → под-куски. → (строки JS GSAP от начала куска, сводка)."""
    pts = [a] + [c for c in cuts if a + 0.4 < c < b - 0.4] + [b]
    r, prev, js, rows = 0, None, [], []
    for i, (s, e) in enumerate(zip(pts, pts[1:])):
        rs, d = round(s - a, 3), e - s
        if i == 0 and before == "face":
            mv = ("in", False, LO, MID)                          # от кадра панели — без скачка
        else:
            for k in range(len(ROTATION)):
                mv = ROTATION[(r + k) % len(ROTATION)]
                if prev is None or abs(mv[2] - prev) >= MIN_STEP - 1e-9 or mv[1]:
                    r = (r + k + 1) % len(ROTATION)
                    break
        _, fast, s0, s1 = mv
        fast = fast or d < 1.0
        js.append(f'tl.set("#cam", {{ transformOrigin: "{origin}", scale: {s0} }}, {rs:.3f});')
        if fast:
            js.append(f'tl.to("#cam", {{ scale: {s1}, duration: {max(0.05, min(FAST, d - 0.05)):.3f}, ease: "power3.out" }}, {rs + 0.02:.3f});')
        else:
            js.append(f'tl.fromTo("#cam", {{ scale: {s0} }}, {{ scale: {s1}, duration: {d - 0.03:.3f}, ease: "sine.inOut", '
                      f'immediateRender: false }}, {rs:.3f});')
        rows.append((round(s, 3), round(e, 3), f"{'быстро' if fast else 'медленно'} {s0:.2f}→{s1:.2f}"))
        prev = s1
    if after == "face" and prev and prev > LO:                   # к панели — плавно к 1,00
        t0 = max(pts[-2] - a + FAST + 0.1, b - a - GLIDE)
        if b - a - t0 > 0.3:
            js.append(f'tl.fromTo("#cam", {{ scale: {prev} }}, {{ scale: {LO}, duration: {b - a - 0.03 - t0:.3f}, ease: "sine.inOut", '
                      f'immediateRender: false }}, {t0:.3f});')
        else:
            js.append(f'tl.to("#cam", {{ scale: {LO}, duration: 0.25, ease: "sine.inOut" }}, {max(0, b - a - 0.3):.3f});')
    return js, rows


def origin_for(scan, sp, a, b):
    """Точка зума — медиана центра лица в куске (время записи → таймлайна)."""
    pts = [(cx, cy) for t, w, cx, cy in (r + [None] * (4 - len(r)) for r in scan.get("faces", []))
           if w and cx is not None and (tl := timeline.to_tl(sp, t)) is not None and a <= tl < b and w >= scan.get("head_w", 0.12)]
    if not pts:
        return "47% 44%"
    return f"{statistics.median(p[0] for p in pts) * 100:.0f}% {statistics.median(p[1] for p in pts) * 100:.0f}%"


def build(work, cut_d, i, a, b, js, render):
    d = Path(work) / "clips" / f"zoom-{i:02d}"
    d.mkdir(parents=True, exist_ok=True)
    src = d / f"bg-{a:.2f}-{b - a:.2f}-q10.mp4"
    if render and not src.exists():
        for old in d.glob("bg-*.mp4"):
            old.unlink()
        timeline.piece(cut_d, a, b - a + 0.1, src)
    fonts = hf.setup_project(d, stage.theme())
    body = (f'<div id="cam" style="position:absolute; inset:0; overflow:hidden"><video id="v" src="{src.name}" data-start="0" '
            f'data-duration="{b - a:.3f}" data-media-start="0" data-track-index="1" muted playsinline '
            f'style="position:absolute; inset:0; width:100%; height:100%; object-fit:cover"></video></div>')
    (d / "index.html").write_text(hf.page("#cam { will-change: transform; }", body, "\n".join(js), b - a, fonts,
                                          bg="#000000", w=W, h=H), encoding="utf-8")
    mp4 = d / f"zoom-{i:02d}.mp4"
    if render:
        hf.render(d, mp4, "mp4", "high")
    return mp4


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--cutlist")
    ap.add_argument("--settings")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    stage.init(work, a.settings)
    import build as bld
    cut = Path(a.cutlist) if a.cutlist else bld.find_cutlist(work)
    if cut is None:
        raise SystemExit("нужен --cutlist (в export/ их несколько или нет)")
    d = timeline.load(cut)
    sp = timeline.spans(d)
    scan = json.loads((work / "scan.json").read_text(encoding="utf-8"))
    heads = timeline.src_spans_to_tl(sp, scan["head"])
    cj = work / "clips.json"
    clips = json.loads(cj.read_text(encoding="utf-8")) if cj.exists() else []
    cuts = timeline.cut_points(sp)
    regs = regions(heads, covers(clips))
    out, total = [], 0.0
    for i, (ra, rb, before, after) in enumerate(regs):
        org = origin_for(scan, sp, ra, rb)
        js, rows = plan(ra, rb, before, after, cuts, org)
        mp4 = build(work, d, i, ra, rb, js, a.render)
        total += rb - ra
        out.append({"name": f"zoom-{i:02d}", "type": "З", "start": ra, "dur": round(rb - ra, 3),
                    "file": str(mp4.relative_to(work)), "lane": 1, "what": f"зум на голове ({org})"})
        print(f"zoom-{i:02d} {timeline.mmss(ra)}–{timeline.mmss(rb)} ({rb - ra:4.1f} с) до: {before}, после: {after}; "
              + "; ".join(r[2] for r in rows[:4]) + (" …" if len(rows) > 4 else ""))
    (work / "zoom.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"кусков с зумом: {len(regs)}, {total / 60:.1f} мин → {work / 'zoom.json'}")


if __name__ == "__main__":
    main()
