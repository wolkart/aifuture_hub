#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy", "scipy"]
# ///
"""Музыкальная подложка под длину ролика по рецепту трека из настроек.

Рецепт (музыка.рецепт): старт → до конца цикла → цикл A–B ×k → хвост в тихую зону,
не доходя до вокала. Конец попадает в тихое место трека, а не обрезается посреди
фразы: обрез на пике автор слышит сразу. Стыки — равномощный кроссфейд (30 мс).
Короткий ролик — без цикла: начало сдвигается позже (но не раньше мин_старт).
Нет рецепта, есть готовая длинная подложка — режется по длине с затуханием.

usage: uv run music_bed.py <out.m4a> --duration 36.6 [--settings reel.settings.json]
       uv run music_bed.py <out.m4a> --long 11      длинная подложка: 11 циклов
"""
import argparse
import math
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import settings as settings_mod  # noqa: E402


def plan(duration, r):
    """Куски оригинала [(a, b)], сумма = duration. r: {start, loop: [A, B], quiet_end: [вход, вокал], min_start}."""
    start, (la, lb), (brk, vocal) = r["start"], r["loop"], r["quiet_end"]
    min_start = r.get("min_start", 0.0)
    a_len, l_len = lb - start, lb - la
    b_min, b_max = brk - lb + 0.4, vocal - lb      # хвост — в тихой зоне
    if duration < a_len + b_min:                   # короткий ролик: без цикла, конец в тишине
        end = min(vocal, max(brk + 0.4, start + duration))
        s = max(min_start, end - duration)
        return [(round(s, 3), round(s + duration, 3))]
    k = max(0, math.ceil((duration - a_len - b_max) / l_len))
    rest = duration - a_len - k * l_len
    if rest < b_min:                               # не хватает до тишины — начать раньше
        start = max(min_start, start - (b_min - rest))
        rest = duration - (lb - start) - k * l_len
    return ([(round(start, 3), lb)] + [(la, lb)] * k + [(lb, round(lb + rest, 3))])


def long_plan(loops, r):
    return [(r["start"], r["loop"][1])] + [tuple(r["loop"])] * loops + [(r["loop"][1], r["quiet_end"][1] - 0.3)]


def render(src, segs, out, xfade=0.03, fade_out=1.5, fade_in=0.25):
    import numpy as np
    from scipy.io import wavfile
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ac", "2", "-ar", "44100",
                    "-c:a", "pcm_f32le", str(tmp / "s.wav")], check=True)
    sr, x = wavfile.read(tmp / "s.wav")
    n = int(xfade * sr)
    ramp = np.sin(np.linspace(0, np.pi / 2, n))[:, None]
    y = None
    for a, b in segs:
        piece = x[int(a * sr):int(b * sr) + n].copy()
        if y is None:
            y = piece
        else:  # равномощный кроссфейд на стыке
            y[-n:] = y[-n:] * ramp[::-1] + piece[:n] * ramp
            y = np.concatenate([y, piece[n:]])
    y = y[:int(sum(b - a for a, b in segs) * sr)]
    fi, fo = int(fade_in * sr), int(fade_out * sr)
    y[:fi] *= np.linspace(0, 1, fi)[:, None]
    y[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    wavfile.write(tmp / "o.wav", sr, y.astype(np.float32))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp / "o.wav"), "-c:a", "aac", "-b:a", "256k",
                    str(out)], check=True)


def trim_bed(src, duration, out, fade_out=1.5):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-t", f"{duration:.3f}", "-af",
                    f"afade=t=in:d=0.25,afade=t=out:st={max(0, duration - fade_out):.3f}:d={fade_out}",
                    "-c:a", "aac", "-b:a", "256k", str(out)], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--duration", type=float)
    g.add_argument("--long", type=int, metavar="ЦИКЛОВ")
    ap.add_argument("--settings", default=None)
    ap.add_argument("--track", default=None, help="другой трек вместо трека из настроек")
    args = ap.parse_args()
    s = settings_mod.load(args.settings)
    m = s["music"] if s else {"track": None, "bed": None, "recipe": None}
    track, r = Path(args.track) if args.track else m["track"], m["recipe"]
    if r and track and track.exists():
        segs = long_plan(args.long, r) if args.long else plan(args.duration, r)
        render(track, segs, args.out, r.get("xfade", 0.03), fade_out=2.5 if args.long else 1.5)
        print(f"{args.out}: {sum(b - a for a, b in segs):.1f} с | куски: "
              + " + ".join(f"[{a:.2f}–{b:.2f}]" for a, b in segs) + f" | конец в тихой зоне {r['quiet_end']}")
    elif m.get("bed") and Path(m["bed"]).exists() and args.duration:
        trim_bed(m["bed"], args.duration, args.out)
        print(f"{args.out}: {args.duration:.1f} с — готовая подложка обрезана с затуханием (рецепта нет)")
    else:
        raise SystemExit("music_bed: в настройках нет трека с рецептом или готовой подложки (музыка.*)")


if __name__ == "__main__":
    main()
