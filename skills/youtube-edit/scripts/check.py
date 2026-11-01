#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy"]
# ///
"""Гейт проверок графики — до показа автору, не на его глазах. Выход ≠ 0 — таймлайн не отдаём.

  uv run check.py pre  <export/монтаж> [имя …]   — до рендера (по проектам, секунды–минуты):
      • паузы внутри сцен > 2,0 с («картинка висит и ждёт»);
      • «мелькнуло»: элемент на экране < 0,8 с — появился под самый уход (проба 2026-10-20: чип DeepSeek жил 0,2 с);
      • наложения и вылеты за край на КАЖДОЙ границе твина (hyperframes inspect --at-transitions):
        text_occluded / content_overlap / canvas_overflow дольше 0,3 с. Обычный inspect берёт 9 точек
        на сцену, и 3-секундное наложение в 70-секундной вставке туда не попадает (news-reposter, images);
      • якоря на вырезанных словах (взято ближайшее — проверь, что смысл не уехал);
      • нахлёсты вставок одной дорожки (хвост предыдущей длиннее 0,45 с налезает на следующую).
  uv run check.py post <export/монтаж> [имя …]  — после рендера:
      • пустая треть кадра у сцен на весь кадр («всё ушло вправо, слева пустота»);
      • контактные листы: _check/<имя>.jpg — 8 кадров клипа (с альфой — на шахматке); смотри их сам.
"""
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "reel" / "scripts"))
import hf  # noqa: E402

CODES = ("text_occluded", "content_overlap", "canvas_overflow")
MIN_MS = 300          # мигнуло на кадр при входе/выходе — не наложение
MAX_GAP = 2.0         # пауза внутри сцены, с
OVERLAP = 0.45        # нахлёст вставок одной дорожки, с
BW, BH, BFPS = 192, 108, 2


def inspect(project):
    cmd = ["npx", "--yes", f"hyperframes@{hf.HF_VERSION}", "inspect", str(project), "--at-transitions", "--json", "--max-issues", "200"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        issues = json.loads(r.stdout)["issues"]
    except (ValueError, KeyError):
        return project.name, None, (r.stderr or r.stdout).strip()[-300:]
    return project.name, [i for i in issues if i["code"] in CODES and (i.get("heldMs") or 0) >= MIN_MS], ""


def overlaps(clips):
    """Нахлёсты на одной дорожке: [(a, b, сколько)]."""
    out = []
    by = {}
    for c in sorted(clips, key=lambda c: c["start"]):
        by.setdefault(c["lane"], []).append(c)
    for lane in by.values():
        for x, y in zip(lane, lane[1:]):
            over = x["start"] + (x["dur"] or 0) - y["start"]
            if over > OVERLAP:
                out.append((x["name"], y["name"], round(over, 2)))
    return out


def pre(work, names):
    import build
    import stage
    stage.init(work)
    items = [sc for sc, _ in build.collect(work, names)]
    bad = 0
    for sc in items:
        for sel, t, vis in stage.brief(sc):
            bad += 1
            print(f"✗ мелькнуло {sc['name']}: {sel} в {t:.1f} с — на экране {vis:.1f} с")
        if sc["kind"] == "tpl":
            continue
        for g0, g1 in stage.idle_gaps(sc, MAX_GAP):
            bad += 1
            print(f"✗ пауза  {sc['name']}: {g0:.1f}–{g1:.1f} с ({g1 - g0:.1f} с) «{stage.WORDS.said(sc['s0'] + g0, sc['s0'] + g1)}»")
    projects = [work / "clips" / sc["name"] for sc in items if (work / "clips" / sc["name"] / "index.html").exists()]
    with ThreadPoolExecutor(3) as ex:
        for name, issues, err in ex.map(inspect, projects):
            if issues is None:
                bad += 1
                print(f"✗ inspect {name}: не отработал — {err}")
                continue
            for i in issues:
                bad += 1
                other = i.get("containerSelector") or ""
                print(f"✗ {i['code']:15s} {name}: {i['firstSeen']:.2f}–{i['lastSeen']:.2f} с ({i['heldMs'] / 1000:.1f} с) "
                      f"{i['selector']} ← {other} «{(i.get('text') or '')[:40]}»")
    for n, k, w, how in sorted(set(stage.WORDS.misses)):
        print(f"⚠ якорь ({n}, {k}) «{w}» вырезан → {how}")
    cj = work / "clips.json"
    if cj.exists():
        for x, y, over in overlaps(json.loads(cj.read_text(encoding="utf-8"))):
            bad += 1
            print(f"✗ нахлёст {x} → {y}: {over:.2f} с")
    print(f"проверка до рендера: {len(items)} сцен, проблем {bad}, якорей заменено {len(set(stage.WORDS.misses))}")
    return bad


def frames(mp4, fps=BFPS):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vf", f"fps={fps},scale={BW}:{BH},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, BH, BW).astype(np.int16)


def empty_third(fr, fps=BFPS, min_len=2.0):
    """Кадры сцены → [(a, b, сторона)]: треть кадра пустая (< 1 %), а в противоположной графика (> 6 %), дольше min_len.
    Фон — первый кадр (элементы ещё не появились)."""
    if not len(fr):
        return []
    bg, out, run = fr[0], [], []
    for i, f in enumerate(fr):
        m = np.abs(f - bg) > 14
        left, right = m[:, :BW // 3].mean(), m[:, 2 * BW // 3:].mean()
        bad = (left < 0.01 and right > 0.06) or (right < 0.01 and left > 0.06)
        if bad:
            run.append((i / fps, "слева пусто" if left < right else "справа пусто"))
        if (not bad or i == len(fr) - 1) and run:
            if run[-1][0] - run[0][0] >= min_len:
                out.append((run[0][0], run[-1][0], run[0][1]))
            run = []
    return out


def sheet(clip, out, n=8):
    """8 кадров клипа одной картинкой (4×2); прозрачное — на шахматке."""
    dur = hf.duration(clip)
    step = dur / (n + 1)
    vf = (f"fps=1/{step:.3f},scale=480:-2" + (",format=rgba" if clip.suffix == ".mov" else "") + f",tile=4x{(n + 3) // 4}")
    src = ["-i", str(clip)]
    if clip.suffix == ".mov":
        fc = (f"color=c=#888888:s=1920x1080:d={dur:.3f}[g];[g]drawgrid=w=60:h=60:t=fill:c=#AAAAAA@1[bg];"
              f"[bg][0:v]overlay=shortest=1,{vf}")
        cmd = ["ffmpeg", "-v", "error", "-y", *src, "-filter_complex", fc, "-frames:v", "1", str(out)]
    else:
        cmd = ["ffmpeg", "-v", "error", "-y", *src, "-vf", vf, "-frames:v", "1", str(out)]
    subprocess.run(cmd, check=True)
    return out


def post(work, names):
    cj = work / "clips.json"
    clips = json.loads(cj.read_text(encoding="utf-8")) if cj.exists() else []
    clips = [c for c in clips if not names or c["name"] in names]
    out = work / "_check"
    out.mkdir(exist_ok=True)
    bad, sheets = 0, []
    for c in clips:
        if not c.get("file") or not (work / c["file"]).exists():
            bad += 1
            print(f"✗ нет клипа {c['name']} — рендер не сделан")
            continue
        clip = work / c["file"]
        if c["type"] == "Д" and c["layout"] == "full":
            for a, b, side in empty_third(frames(clip)):
                bad += 1
                print(f"✗ композиция {c['name']}: {a:.1f}–{b:.1f} с — {side}")
        sheets.append(sheet(clip, out / f"{c['name']}.jpg"))
    print(f"проверка после рендера: {len(clips)} клипов, проблем {bad}; листы ({len(sheets)}) — {out} (посмотри каждый)")
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=("pre", "post"))
    ap.add_argument("work")
    ap.add_argument("names", nargs="*")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    bad = pre(work, a.names) if a.stage == "pre" else post(work, a.names)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
