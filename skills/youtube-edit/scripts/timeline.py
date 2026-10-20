#!/usr/bin/env python3
"""Время записи ⇄ время таймлайна через cut-list rough-cut. Только stdlib + ffmpeg.

Таймлайн резки — мой, поэтому время каждого слова в готовом ролике известно сразу: шага
«расшифровать экспорт из Resolve и сопоставить слова» (align.py в news-reposter) нет.

  timeline.py words <cutlist> <words.json> [--offset S] [-o export/монтаж/words.json]
      → фразы той же нумерации, что в отчёте резки (longform.py lines), время — таймлайна;
        вырезанное слово — [текст, null, null] (сцена возьмёт ближайшее уцелевшее, в отчёт).
        --offset по умолчанию — sync.offset_s cut-list, если звук записан отдельно (как у longform.py).
  timeline.py piece <cutlist> <с> <длина> -o кусок.mp4
      → кусок ТАЙМЛАЙНА видеофайлом (склейки внутри — как в ролике), 1920×1080, без звука, crf 10:
        лицо автора в панелях wide_drawer, фон зума на голове.
  timeline.py show <cutlist>   → куски и склейки на таймлайне
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RC = HERE.parents[1] / "rough-cut" / "scripts"
sys.path.insert(0, str(RC))
import cutlist   # noqa: E402  (rough-cut)
import longform  # noqa: E402  (rough-cut: нумерация фраз)

W, H = 1920, 1080          # таймлайн и графика
EPS = 1e-6


def load(path):
    return cutlist.load(path)


def spans(d):
    """Куски таймлайна по порядку: [(tl_a, tl_b, src_a, src_b, rate)] — keep (rate 1) и speedup."""
    out, tl = [], 0.0
    for s in cutlist.timeline(d):
        rate = s.get("rate", 1.0) if s["action"] == "speedup" else 1.0
        dur = (s["end"] - s["start"]) / rate
        out.append((round(tl, 4), round(tl + dur, 4), s["start"], s["end"], rate))
        tl += dur
    return out


def total(sp):
    return sp[-1][1] if sp else 0.0


def to_tl(sp, t):
    """Секунда записи → секунда таймлайна; None — вырезано."""
    for a, b, sa, sb, r in sp:
        if sa - EPS <= t < sb + EPS:
            return round(a + (min(t, sb) - sa) / r, 4)
    return None


def to_src(sp, t):
    """Секунда таймлайна → секунда записи."""
    for a, b, sa, sb, r in sp:
        if a - EPS <= t < b + EPS:
            return round(sa + (min(t, b) - a) * r, 4)
    return sp[-1][3] if sp else 0.0


def cut_points(sp):
    """Склейки на таймлайне — где кончается один кусок и начинается следующий."""
    return [round(b, 3) for (a, b, *_) in sp[:-1]]


def src_spans_to_tl(sp, items):
    """Куски записи [(a, b)] → куски таймлайна (пересечение с оставленным, склеенное подряд)."""
    out = []
    for a, b in items:
        for ta, tb, sa, sb, r in sp:
            lo, hi = max(a, sa), min(b, sb)
            if hi - lo > EPS:
                x, y = ta + (lo - sa) / r, ta + (hi - sa) / r
                if out and abs(out[-1][1] - x) < 0.05:
                    out[-1][1] = y
                else:
                    out.append([x, y])
    return [(round(a, 3), round(b, 3)) for a, b in out]


def span_of(sp, t):
    for i, (a, b, sa, sb, r) in enumerate(sp):
        if sa - EPS <= t < sb + EPS:
            return i
    return None


def word_tl(sp, s, e):
    """Слово [s, e) записи → (начало, конец) на таймлайне или (None, None), если вырезано.
    Края слов у распознавания неточные, а резы тишины ложатся с полями — поэтому слово живо, если
    жива его середина; начало — не раньше начала куска, конец — не позже его конца."""
    i = span_of(sp, (s + e) / 2)
    if i is None:
        return None, None
    a, b, sa, sb, r = sp[i]
    return round(a + (max(s, sa) - sa) / r, 4), round(a + (min(e, sb) - sa) / r, 4)


def words(d, words_path, offset):
    """Фразы (нумерация longform.py lines) → время таймлайна. Вырезанное слово — без времени:
    сцена на нём не стоит (ближайшее уцелевшее — stage.Words, случай — в отчёт)."""
    sp = spans(d)
    phr = longform.phrases(longform.load_words(words_path, offset))
    out = []
    for p in phr:
        ws = []
        for w in p["words"]:
            a, b = word_tl(sp, w["start"], w["end"])
            ws.append([w["text"], a, b])
        alive = [w for w in ws if w[1] is not None]
        out.append({"n": p["n"], "a": alive[0][1] if alive else None, "b": alive[-1][2] if alive else None,
                    "src": [p["a"], p["b"]], "text": p["text"], "words": ws})
    return out


def piece_cmd(d, a, dur, out, w=W, h=H, crf=10):
    """ffmpeg: кусок таймлайна [a, a+dur) из записи — по кускам cut-list, склейка concat."""
    sp, video = spans(d), d["inputs"]["video"]
    parts = []
    for ta, tb, sa, sb, r in sp:
        lo, hi = max(a, ta), min(a + dur, tb)
        if hi - lo > 1 / 60:
            parts.append((sa + (lo - ta) * r, (hi - lo) * r, r))
    if not parts:
        raise ValueError(f"piece: на таймлайне нет {a:.2f}+{dur:.2f}")
    cmd, fc = ["ffmpeg", "-v", "error", "-y"], []
    for i, (s, ln, r) in enumerate(parts):
        cmd += ["-ss", f"{s:.3f}", "-t", f"{ln:.3f}", "-i", str(video)]
        speed = f",setpts=PTS/{r}" if r != 1 else ""
        fc.append(f"[{i}:v]setpts=PTS-STARTPTS{speed},scale={w}:{h}:force_original_aspect_ratio=increase,"
                  f"crop={w}:{h},setsar=1,fps={d['fps']['num']}/{d['fps']['den']}[v{i}]")
    fc.append("".join(f"[v{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=0[o]")
    return cmd + ["-filter_complex", ";".join(fc), "-map", "[o]", "-an", "-c:v", "libx264", "-preset", "veryfast",
                  "-crf", str(crf), "-pix_fmt", "yuv420p", str(out)]


def piece(d, a, dur, out, **kw):
    subprocess.run(piece_cmd(d, a, dur, out, **kw), check=True)
    return Path(out)


def default_offset(d):
    return d.get("sync", {}).get("offset_s", 0.0) if d["inputs"].get("audio") else 0.0


def work_dir(cutlist_path):
    """export/монтаж/ рядом с cut-list."""
    p = Path(cutlist_path).resolve().parent / "монтаж"
    p.mkdir(exist_ok=True)
    return p


def mmss(t):
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("words")
    a.add_argument("cutlist")
    a.add_argument("words")
    a.add_argument("--offset", type=float, default=None)
    a.add_argument("-o", "--out")
    b = sub.add_parser("piece")
    b.add_argument("cutlist")
    b.add_argument("start", type=float)
    b.add_argument("dur", type=float)
    b.add_argument("-o", "--out", required=True)
    c = sub.add_parser("show")
    c.add_argument("cutlist")
    args = ap.parse_args()
    d = load(args.cutlist)
    if args.cmd == "words":
        off = default_offset(d) if args.offset is None else args.offset
        res = words(d, args.words, off)
        out = Path(args.out) if args.out else work_dir(args.cutlist) / "words.json"
        out.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        nw = sum(len(p["words"]) for p in res)
        cut = sum(1 for p in res for w in p["words"] if w[1] is None)
        print(f"фраз {len(res)}, слов {nw}, вырезано {cut} (сдвиг звука {off:+.3f} с) → {out}")
    elif args.cmd == "piece":
        print(piece(d, args.start, args.dur, args.out))
    else:
        sp = spans(d)
        print(f"таймлайн {mmss(total(sp))} из {mmss(d['duration_s'])} записи · кусков {len(sp)} · склеек {len(sp) - 1}")


if __name__ == "__main__":
    main()
