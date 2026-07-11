#!/usr/bin/env python3
"""cut-list → готовый mp4 (H.264+AAC) через ffmpeg. Только stdlib.

Исходники не перезаписываются никогда: выход не может совпадать со входом,
существующий файл — только с --force. speedup: видео ускоряется, звук на
этом участке — тишина (у таймлапса нет осмысленного звука).
"""
import argparse
import subprocess
from pathlib import Path

import cutlist


def build_cmd(d, out_path):
    video = d["inputs"]["video"]
    audio = d["inputs"].get("audio")
    out_path = Path(out_path)
    inputs_paths = {Path(video).resolve()} | (
        {Path(audio).resolve()} if audio else set())
    if out_path.resolve() in inputs_paths:
        raise ValueError("render: выход совпадает со входом — исходники "
                         "не перезаписываются")
    off = d.get("sync", {}).get("offset_s", 0.0) if audio else 0.0
    a_in = "1:a" if audio else "0:a"
    parts, pairs, n = [], [], 0
    for seg in cutlist.timeline(d):
        s, e = seg["start"], seg["end"]
        if seg["action"] == "keep":
            parts.append(f"[0:v]trim=start={s}:end={e},"
                         f"setpts=PTS-STARTPTS[v{n}]")
            parts.append(f"[{a_in}]atrim=start={s + off}:end={e + off},"
                         f"asetpts=PTS-STARTPTS[a{n}]")
        else:  # speedup
            rate = seg["rate"]
            parts.append(f"[0:v]trim=start={s}:end={e},"
                         f"setpts=(PTS-STARTPTS)/{rate}[v{n}]")
            parts.append(f"aevalsrc=0:d={(e - s) / rate}:s=48000[a{n}]")
        pairs.append(f"[v{n}][a{n}]")
        n += 1
    fc = (";".join(parts) + ";" + "".join(pairs)
          + f"concat=n={n}:v=1:a=1[vo][ao]")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(video)]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-filter_complex", fc, "-map", "[vo]", "-map", "[ao]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", str(out_path)]
    return cmd


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cutlist_path")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    d = cutlist.load(args.cutlist_path)
    if args.out:
        out = Path(args.out)
    else:
        v = Path(d["inputs"]["video"])
        out = v.with_name(v.stem + ".roughcut.mp4")
    if out.exists() and not args.force:
        raise SystemExit(f"render: {out} уже существует (перезапись — --force)")
    subprocess.run(build_cmd(d, out), check=True)
    print(f"Рендер: {out}")


if __name__ == "__main__":
    main()
