#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy"]
# ///
"""Один проход по кадрам записи → scan.json: переходы зумов, голова на весь кадр, «висящий экран».
Время — секунды ЗАПИСИ (cut-list не нужен, поэтому скан идёт фоном вместе с расшифровкой).

Зачем:
  • переходы зумов — на них не режем (zoom_guard.py); проверяем всегда, чем бы ни снимали:
    у FocuSee зумы вшиты в экспорт, у OBS их нет — но «мало ли» (автор 2026-10-20);
  • голова на весь кадр — там лёгкий зум, где нет графики (head_zoom.py), и панели wide_drawer;
  • висящий экран — экран стоит ≥ 7 с, а речь идёт: место под вставку (в news-reposter
    нашлось 64 места на 16 мин, взято 21 — где автор объясняет понятие).

Как:
  • кадры 10 к/с в 160×90 серым → сетка 16×9; клетка «изменилась», если средняя разница с прошлым
    кадром > CELL_THR. Доля изменившихся клеток по всему кадру — движение всего кадра (зум, смена
    раскладки, прокрутка). Клетки, которые меняются почти всегда (кружок камеры поверх экрана), —
    маска: для «висящего экрана» они не считаются;
  • лицо — Apple Vision 1 к/с; ширина рамки ≥ HEAD_W доли кадра — голова на весь кадр
    (лицо в кружке камеры — 0,03–0,06). Не macOS — голова не ищется (сказать вслух).

  uv run scan.py <запись.mp4> [-o export/монтаж/scan.json]
"""
import argparse
import csv
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CACHE = Path.home() / ".cache" / "youtube-edit"
FPS, GW, GH, CELL = 10, 16, 9, 10            # 160×90 → клетки 10×10
CELL_THR = 1.5        # средняя разница клетки (0–255), выше — изменилась
MOVE_ALL = 0.55       # доля клеток — «двигается весь кадр»
MOVE_MIN, MOVE_MAX = 0.2, 3.0                # переход зума длится 0,3–1,5 с; прокрутка — дольше (тоже не режем, но не зум)
MASK_SHARE = 0.25     # пока экран стоит (≤ 6 % клеток), клетка меняется в ≥ четверти кадров — кружок камеры
MASK_STILL = 0.06
STATIC_FRAC = 0.02    # ≤ 2 % клеток экрана (курсор, мигающий курсор) — экран стоит
STATIC_MIN, STATIC_BLIP = 7.0, 0.4           # висит ≥ 7 с; дрожь короче 0,4 с не рвёт кусок
HEAD_W, HEAD_MIN, HEAD_GAP = 0.12, 2.0, 2.0  # голова: рамка лица ≥ 12 % ширины, кусок ≥ 2 с, дыры ≤ 2 с сшиваются


def runs(flags, fps, min_len=0.0, max_len=None, merge_gap=0.0):
    """Булев ряд (шаг 1/fps) → [(a, b)] секунд: куски True длиной в [min_len, max_len];
    куски, разделённые дырой ≤ merge_gap, сшиваются до проверки длины."""
    out, start = [], None
    for i, f in enumerate(list(flags) + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append([start / fps, i / fps])
            start = None
    merged = []
    for a, b in out:
        if merged and a - merged[-1][1] <= merge_gap:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(round(a, 2), round(b, 2)) for a, b in merged
            if b - a >= min_len - 1e-9 and (max_len is None or b - a <= max_len + 1e-9)]


def cell_changes(prev, cur):
    """Два кадра GH*CELL × GW*CELL → булева сетка GH×GW: где клетка изменилась."""
    d = np.abs(cur.astype(np.int16) - prev.astype(np.int16))
    return d.reshape(GH, CELL, GW, CELL).mean(axis=(1, 3)) > CELL_THR


def in_any(t, spans):
    return any(a <= t < b for a, b in spans)


def motion(changes, head_spans, fps=FPS):
    """changes: [N, GH, GW] bool → переходы (движение всего кадра вне головы), маска, висящий экран."""
    n = len(changes)
    t = np.arange(n) / fps
    head = np.array([in_any(x, head_spans) for x in t]) if n else np.zeros(0, bool)
    frac_all = changes.reshape(n, -1).mean(axis=1) if n else np.zeros(0)
    screen = ~head
    base = screen & (frac_all <= MASK_STILL)                    # экран стоит — меняется только кружок камеры
    mask = (changes[base].mean(axis=0) >= MASK_SHARE) if base.sum() >= 50 else np.zeros((GH, GW), bool)
    keep = ~mask.reshape(-1)
    frac_screen = changes.reshape(n, -1)[:, keep].mean(axis=1) if n and keep.any() else np.zeros(n)
    trans = runs((frac_all >= MOVE_ALL) & screen, fps, MOVE_MIN, MOVE_MAX)
    moving = runs(frac_all >= MOVE_ALL, fps, MOVE_MIN)          # всё, где двигается весь кадр (и длинная прокрутка)
    still = frac_screen <= STATIC_FRAC
    static = [s for s in runs(still & screen, fps, 0.0, merge_gap=STATIC_BLIP) if s[1] - s[0] >= STATIC_MIN]
    return {"transitions": trans, "moving": moving, "static": static, "mask_cells": int(mask.sum()),
            "frac_all": [round(float(x), 3) for x in frac_all], "frac_screen": [round(float(x), 3) for x in frac_screen]}


def head_spans(face_rows, thr=HEAD_W):
    """[(t, w|None, …)] шаг 1 с → куски головы на весь кадр."""
    if not face_rows:
        return []
    step = face_rows[1][0] - face_rows[0][0] if len(face_rows) > 1 else 1.0
    flags = [r[1] is not None and r[1] >= thr for r in face_rows]
    return runs(flags, 1 / step, HEAD_MIN, merge_gap=HEAD_GAP)


def face_tool():
    if sys.platform != "darwin" or not shutil.which("swiftc"):
        return None
    src, binp = HERE / "face_box.swift", CACHE / "face_box"
    if not binp.exists() or binp.stat().st_mtime < src.stat().st_mtime:
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", "-o", str(binp), str(src)], check=True, capture_output=True)
    return binp


def faces(tool, frames_dir):
    out = subprocess.run([str(tool), str(frames_dir)], check=True, capture_output=True, text=True).stdout
    rows = []
    for r in csv.DictReader(io.StringIO(out)):
        n = int(r["name"].split("_")[1].split(".")[0])
        rows.append((float(n - 1), float(r["w"]) if r["w"] else None,
                     float(r["cx"]) if r["cx"] else None, float(r["cy"]) if r["cy"] else None))
    return sorted(rows)


def decode(video, frames_dir):
    """Один проход ffmpeg: серые 160×90 10 к/с в трубу + PNG 1 к/с для лица. → [N, GH, GW] bool."""
    w, h = GW * CELL, GH * CELL
    cmd = ["ffmpeg", "-v", "error", "-i", str(video), "-filter_complex",
           f"[0:v]split=2[a][b];[a]fps={FPS},scale={w}:{h},format=gray[g];[b]fps=1,scale=640:-2[f]",
           "-map", "[g]", "-f", "rawvideo", "pipe:1"]
    if frames_dir:
        cmd += ["-map", "[f]", str(Path(frames_dir) / "f_%06d.png")]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size, prev, out = w * h, None, []
    while True:
        raw = p.stdout.read(size)
        if len(raw) < size:
            break
        cur = np.frombuffer(raw, np.uint8).reshape(h, w)
        out.append(cell_changes(prev, cur) if prev is not None else np.zeros((GH, GW), bool))
        prev = cur
    if p.wait():
        raise SystemExit(f"ffmpeg упал на {video}")
    return np.array(out) if out else np.zeros((0, GH, GW), bool)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--head-w", type=float, default=HEAD_W, help="порог ширины лица (доля кадра)")
    a = ap.parse_args()
    video = Path(a.video).resolve()
    out = Path(a.out) if a.out else video.parent / "export" / "монтаж" / "scan.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    tool = face_tool()
    tmp = Path(tempfile.mkdtemp(prefix="yt-scan-")) if tool else None
    try:
        changes = decode(video, tmp)
        rows = faces(tool, tmp) if tool else []
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    heads = head_spans(rows, a.head_w)
    m = motion(changes, heads)
    ws = sorted(r[1] for r in rows if r[1])
    res = {"video": str(video), "duration": round(len(changes) / FPS, 2), "fps": FPS,
           "head": heads, "transitions": m["transitions"], "moving": m["moving"], "static": m["static"],
           "mask_cells": m["mask_cells"], "head_w": a.head_w,
           "faces": [list(r) for r in rows], "frac_all": m["frac_all"], "frac_screen": m["frac_screen"]}
    out.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    pct = (lambda q: f"{ws[int(q * (len(ws) - 1))]:.3f}") if ws else (lambda q: "—")
    print(f"скан: {res['duration'] / 60:.1f} мин · переходов зума {len(m['transitions'])} · голова {len(heads)} кусков "
          f"({sum(b - a for a, b in heads) / 60:.1f} мин) · висящий экран {len(m['static'])} мест "
          f"({sum(b - a for a, b in m['static']) / 60:.1f} мин) · маска кружка {m['mask_cells']} клеток → {out}")
    print(f"  ширина лица: p10 {pct(.1)} · p50 {pct(.5)} · p90 {pct(.9)} (порог головы {a.head_w})"
          + ("" if tool else " — лицо не искали: нужен macOS со swiftc"))


if __name__ == "__main__":
    main()
