#!/usr/bin/env python3
"""Кадры из тихих участков скринкаста (начало/середина/конец). Только stdlib."""
import argparse
import json
import subprocess
from pathlib import Path


def frame_times(start, end, edge=0.2):
    if end - start <= 2 * edge:
        return [round((start + end) / 2, 3)]
    return [round(start + edge, 3), round((start + end) / 2, 3),
            round(end - edge, 3)]


def extract(video, intervals, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = []
    for i, iv in enumerate(intervals):
        frames = []
        for t in frame_times(iv["start"], iv["end"]):
            p = out_dir / f"gap{i:03d}_t{t:07.2f}.png"
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-ss", str(t),
                 "-i", str(video), "-frames:v", "1", str(p)], check=True)
            frames.append(str(p))
        result.append({"interval": iv, "frames": frames})
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video")
    ap.add_argument("--intervals", required=True, help="JSON: [{start,end},...]")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    res = extract(args.video, json.loads(args.intervals), args.out_dir)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
