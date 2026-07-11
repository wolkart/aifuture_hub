#!/usr/bin/env python3
"""Интервалы тишины через ffmpeg silencedetect. Только stdlib."""
import argparse
import json
import re
import subprocess


def detect(path, noise_db=-35.0, min_dur=0.8):
    p = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path),
         "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}",
         "-f", "null", "-"],
        capture_output=True, text=True)
    starts = [float(m) for m in re.findall(r"silence_start: (-?[\d.]+)", p.stderr)]
    ends = [float(m) for m in re.findall(r"silence_end: (-?[\d.]+)", p.stderr)]
    return [{"start": max(0.0, round(s, 3)), "end": round(e, 3)}
            for s, e in zip(starts, ends)]


def to_cuts(intervals, pad=0.15, min_cut=0.4):
    """Паддинг внутрь (дыхание вокруг речи), слишком короткое не режем."""
    cuts = []
    for iv in intervals:
        s, e = iv["start"] + pad, iv["end"] - pad
        if e - s >= min_cut:
            cuts.append({"start": round(s, 3), "end": round(e, 3)})
    return cuts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("audio")
    ap.add_argument("--noise-db", type=float, default=-35.0)
    ap.add_argument("--min-dur", type=float, default=0.8)
    ap.add_argument("--pad", type=float, default=0.15)
    ap.add_argument("--min-cut", type=float, default=0.4)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    silences = detect(args.audio, args.noise_db, args.min_dur)
    print(json.dumps(
        {"silences": silences,
         "cuts": to_cuts(silences, args.pad, args.min_cut)},
        ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
