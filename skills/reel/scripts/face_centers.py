#!/usr/bin/env python3
"""Центр лица по времени → faces.csv (t,cx,cy). Только stdlib + ffmpeg; лицо — Apple Vision.

Наезд масштабирует кадр вокруг лица, поэтому лицо не уезжает. Кадры берутся 10 к/с в
540 px — для медианы по куску этого хватает, а Vision на 10 к/с работает секунды.
Не macOS — стадия пропускается: наезды пойдут от центра кадра (0.5, 0.45).
Запасная ONNX-ветка для Linux/Windows — открытый вопрос (спецификация, раздел «Открытые»).

usage: face_centers.py <видео> [-o faces.csv] [--fps 10]
"""
import argparse
import csv
import io
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = Path.home() / ".cache" / "reel"


def tool():
    """Скомпилировать face_center.swift один раз в ~/.cache/reel. None — не macOS."""
    if sys.platform != "darwin" or not shutil.which("swiftc"):
        return None
    src, binp = HERE / "face_center.swift", CACHE / "face_center"
    if not binp.exists() or binp.stat().st_mtime < src.stat().st_mtime:
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", "-o", str(binp), str(src)], check=True, capture_output=True)
    return binp


def rows_to_times(csv_text, fps):
    """name f_0001.png → t = (n−1)/fps. → [(t, cx|None, cy|None)]"""
    out = []
    for r in csv.DictReader(io.StringIO(csv_text)):
        n = int(r["name"].split("_")[1].split(".")[0])
        cx = float(r["cx"]) if r["cx"] else None
        cy = float(r["cy"]) if r["cy"] else None
        out.append((round((n - 1) / fps, 3), cx, cy))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--fps", type=float, default=10.0)
    args = ap.parse_args()
    t = tool()
    if t is None:
        print("лицо: пропущено — нужен macOS со swiftc (Apple Vision). Наезды — от центра кадра.")
        return
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", args.video, "-vf", f"fps={args.fps},scale=540:-2",
                    str(tmp / "f_%05d.png")], check=True)
    out = subprocess.run([str(t), str(tmp)], check=True, capture_output=True, text=True).stdout
    shutil.rmtree(tmp, ignore_errors=True)
    rows = rows_to_times(out, args.fps)
    dst = Path(args.out or Path(args.video).with_name("faces.csv"))
    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "cx", "cy"])
        for tt, cx, cy in rows:
            w.writerow([tt, "" if cx is None else cx, "" if cy is None else cy])
    found = sum(1 for _, cx, _ in rows if cx is not None)
    print(f"лицо: найдено в {found} из {len(rows)} кадров → {dst}")


if __name__ == "__main__":
    main()
