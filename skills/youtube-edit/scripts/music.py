#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy"]
# ///
"""Музыка длинного ролика: пробы в начале работы и подложка под весь таймлайн.

Почему пробы в начале: в news-reposter музыку выбирали в конце, и первая (энергичная, 140 BPM)
спорила с экраном — «зритель должен спокойно, размеренно смотреть». Выбор ушами на одном куске —
минуты; переделка подложки после сборки — круг.

  uv run music.py probe <cutlist> [--tracks a.mp3 b.mp3 …] [--at С] [--dur 40] [--format скринкаст|голова]
      → export/монтаж/music/проба-N <трек>.mp4: кусок таймлайна (видео + голос) с музыкой на уровне
        формата. Треки — из --tracks или настроек (ютуб.пробы_музыки: файлы и папки), до трёх.
  uv run music.py bed <cutlist> [--track …] [--format …] [--loop A B] [--rel LU] [--lift dB]
      → export/монтаж/music/bed.wav — трек по кругу с кроссфейдом под длину таймлайна; уровень — на rel LU
        ниже голоса; в паузах речи +lift dB (0 — ровно). Без --track — из настроек (ютуб.музыка.<формат>).

Форматы (настройки перебивают): скринкаст — −28 LU, без подъёмов (автор: «проба №3 просто
безупречная» — KL7H, 80 BPM); голова — −20 LU, +4 dB в паузах (энергичная — только здесь).
Права проверять до публикации (сток с лицензией или загрузка с ограниченным доступом на Content ID).
"""
import argparse
import json
import math
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SKILLS / "rough-cut" / "scripts"))
sys.path.insert(0, str(SKILLS / "reel" / "scripts"))
import cutlist   # noqa: E402  (rough-cut)
import timeline  # noqa: E402

AUDIO_EXT = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")
FORMATS = {"скринкаст": {"уровень_LU_к_голосу": -28.0, "подъём_в_паузах_dB": 0.0, "кроссфейд_с": 4.0},
           "голова": {"уровень_LU_к_голосу": -20.0, "подъём_в_паузах_dB": 4.0, "кроссфейд_с": 4.0}}
LIMIT = 0.84          # −1,5 dBFS после AAC; alimiter level=false — иначе сам дотягивает до 0 dBFS
MASTER = f"volume={-20 * math.log10(LIMIT):.2f}dB,alimiter=limit={LIMIT}:level=false"


def recipe(section, fmt, track=None, loop=None, rel=None, lift=None):
    """Рецепт подложки: формат по умолчанию ← настройки (ютуб.музыка.<формат>) ← ключи командной строки."""
    r = dict(FORMATS[fmt])
    r.update(((section.get("музыка") or {}).get(fmt)) or {})
    if track:                         # другой трек — цикл из настроек к нему не относится
        r["трек"] = track
        r.pop("цикл", None)
    if loop:
        r["цикл"] = list(loop)
    if rel is not None:
        r["уровень_LU_к_голосу"] = rel
    if lift is not None:
        r["подъём_в_паузах_dB"] = lift
    return r


def dur_of(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))


def loudness(path, extra=()):
    err = subprocess.run(["ffmpeg", "-hide_banner", *extra, "-i", str(path), "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(json.loads(err[err.rindex("{"):err.rindex("}") + 1])["input_i"])


def loop_count(total, a, b, xfade):
    """Сколько повторов куска [a, b) нужно, чтобы с первым (с начала трека до b) и кроссфейдами покрыть total."""
    return max(1, math.ceil((total + xfade - b) / (b - a - xfade)) + 1) if b - a > xfade else 1


def loop_cmd(track, total, loop, xfade, out):
    """ffmpeg: трек [0, b) + повторы [a, b) с кроссфейдом → total с, затухание 4 с в конце, 48 кГц."""
    a, b = loop if loop else (0.0, dur_of(track))
    n = loop_count(total, a, b, xfade)
    ins = sum([["-i", str(track)] for _ in range(n)], [])
    chain = [f"[0:a]atrim=0:{b},asetpts=PTS-STARTPTS[s0]"] + [f"[{i}:a]atrim={a}:{b},asetpts=PTS-STARTPTS[s{i}]" for i in range(1, n)]
    last = "[s0]"
    for i in range(1, n):
        chain.append(f"{last}[s{i}]acrossfade=d={xfade}:c1=qsin:c2=qsin[x{i}]")
        last = f"[x{i}]"
    fade_out = min(4.0, total / 4)
    chain.append(f"{last}atrim=0:{total:.3f},asetpts=PTS-STARTPTS,afade=t=in:d={min(2.0, total / 4):.2f},"
                 f"afade=t=out:st={total - fade_out:.3f}:d={fade_out:.2f},aresample=48000[o]")
    return ["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(chain), "-map", "[o]", "-ac", "2", "-c:a", "pcm_s16le", str(out)]


def envelope_points(keys):
    """[(t, db, ramp)] (composite.auto_levels) → узлы кусочно-линейной кривой."""
    xs, ys, prev = [0.0], [0.0], 0.0
    for t, db, ramp in sorted(keys):
        ramp = max(0.01, float(ramp or 0.01))
        xs += [t, t + ramp]
        ys += [prev, db]
        prev = db
    xs.append(1e9)
    ys.append(prev)
    return np.array(xs), np.array(ys)


def apply_gain(src, dst, gain_db, keys=()):
    """Усиление + огибающая подъёмов — блоками по 10 с (выражение ffmpeg на 40 минут не влезает в eval)."""
    xs, ys = envelope_points(keys)
    with wave.open(str(src)) as fi, wave.open(str(dst), "wb") as fo:
        ch, sr = fi.getnchannels(), fi.getframerate()
        fo.setnchannels(ch)
        fo.setsampwidth(2)
        fo.setframerate(sr)
        pos = 0
        while True:
            raw = fi.readframes(sr * 10)
            if not raw:
                break
            y = np.frombuffer(raw, np.int16).astype(np.float32).reshape(-1, ch)
            t = (pos + np.arange(len(y))) / sr
            g = 10 ** ((gain_db + np.interp(t, xs, ys)) / 20)
            fo.writeframes(np.clip(y * g[:, None], -32768, 32767).astype(np.int16).tobytes())
            pos += len(y)


def voice_lufs(d, work):
    """Громкость голоса — по звуку монтажа (отдельная запись или звук видео), кеш по времени файла."""
    src = Path(d["inputs"].get("audio") or d["inputs"]["video"])
    cache = work / "music" / "_voice-lufs.json"
    key = f"{src}:{src.stat().st_mtime:.0f}"
    if cache.exists() and json.loads(cache.read_text()).get("key") == key:
        return json.loads(cache.read_text())["lufs"]
    v = loudness(src, ["-vn"] if src.suffix.lower() not in AUDIO_EXT else [])
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"key": key, "lufs": v}))
    return v


def make_bed(track, total, rec, voice, out, words=None):
    tmp = Path(tempfile.mkdtemp(prefix="yt-music-")) / "loop.wav"
    subprocess.run(loop_cmd(track, total, rec.get("цикл"), float(rec["кроссфейд_с"]), tmp), check=True)
    gain = voice + float(rec["уровень_LU_к_голосу"]) - loudness(tmp)
    keys = []
    lift = float(rec["подъём_в_паузах_dB"])
    if lift > 0 and words:
        import composite
        keys = composite.auto_levels(words, total, lift_db=lift, min_gap=1.2)
    apply_gain(tmp, out, gain, keys)
    tmp.unlink()
    return gain, len(keys) // 2


def tl_words(work):
    p = work / "words.json"
    if not p.exists():
        return []
    return [{"text": w[0], "start": w[1], "end": w[2]} for ph in json.loads(p.read_text(encoding="utf-8"))
            for w in ph["words"] if w[1] is not None]


def chunk_cutlist(d, at, dur):
    """cut-list только с куском таймлайна [at, at+dur) — для рендера пробы через rough-cut render.py."""
    keep = []
    for ta, tb, sa, sb, r in timeline.spans(d):
        lo, hi = max(at, ta), min(at + dur, tb)
        if hi - lo > 0.05:
            keep.append((round(sa + (lo - ta) * r, 3), round(sa + (hi - ta) * r, 3)))
    cuts, cur = [], 0.0
    for a, b in keep:
        if a - cur > 0.02:
            cuts.append({"start": round(cur, 3), "end": a, "action": "cut", "source": "user", "reason": "вне пробы"})
        cur = b
    if d["duration_s"] - cur > 0.02:
        cuts.append({"start": round(cur, 3), "end": d["duration_s"], "action": "cut", "source": "user", "reason": "вне пробы"})
    meta = {k: d[k] for k in d if k not in ("version", "segments")}
    return cutlist.from_cuts(meta, cuts)


def candidates(section, given):
    out = []
    for x in (given or section.get("пробы_музыки") or []):
        p = Path(x).expanduser()
        if p.is_dir():
            out += sorted(q for q in p.iterdir() if q.suffix.lower() in AUDIO_EXT)
        elif p.exists():
            out.append(p)
    return out[:3]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("op", choices=("probe", "bed"))
    ap.add_argument("cutlist")
    ap.add_argument("--tracks", nargs="*")
    ap.add_argument("--track")
    ap.add_argument("--at", type=float)
    ap.add_argument("--dur", type=float, default=40.0)
    ap.add_argument("--format", choices=tuple(FORMATS), default="скринкаст")
    ap.add_argument("--loop", type=float, nargs=2)
    ap.add_argument("--rel", type=float)
    ap.add_argument("--lift", type=float)
    ap.add_argument("--settings")
    a = ap.parse_args()
    import stage
    d = timeline.load(a.cutlist)
    work = timeline.work_dir(a.cutlist)
    stage.init(work, a.settings)
    sec = stage.section()
    mdir = work / "music"
    mdir.mkdir(exist_ok=True)
    total = timeline.total(timeline.spans(d))
    if a.op == "probe":
        tracks = candidates(sec, a.tracks)
        if not tracks:
            raise SystemExit("нет треков для проб: --tracks или ютуб.пробы_музыки в настройках")
        at = a.at if a.at is not None else round(total * 0.25, 1)
        dur = min(a.dur, total - at)
        import render
        base = mdir / "_проба-основа.mp4"
        subprocess.run(render.build_cmd(chunk_cutlist(d, at, dur), base), check=True)
        voice = loudness(base, ["-vn"])
        for i, t in enumerate(tracks, 1):
            rec = recipe(sec, a.format, track=str(t), rel=a.rel, lift=0.0)
            bed = mdir / f"_проба-{i}.wav"
            make_bed(t, dur, rec, voice, bed)
            out = mdir / f"проба-{i} {t.stem}.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(base), "-i", str(bed), "-filter_complex",
                            f"[0:a][1:a]amix=inputs=2:normalize=0:duration=first,{MASTER}[a]", "-map", "0:v", "-map", "[a]",
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out)], check=True)
            bed.unlink()
            print(f"проба {i}: {out}")
        base.unlink()
        print(f"кусок таймлайна {timeline.mmss(at)}–{timeline.mmss(at + dur)}, музыка на {recipe(sec, a.format, rel=a.rel)['уровень_LU_к_голосу']:.0f} LU "
              f"к голосу ({a.format}). Права — проверить до публикации.")
        return
    rec = recipe(sec, a.format, a.track, a.loop, a.rel, a.lift)
    if not rec.get("трек"):
        raise SystemExit(f"нет трека: --track или ютуб.музыка.{a.format}.трек в настройках")
    track = Path(rec["трек"]).expanduser()
    if not track.is_absolute() and stage.settings_path():
        track = Path(stage.settings_path()).parent / track
    out = mdir / "bed.wav"
    gain, lifts = make_bed(track, total, rec, voice_lufs(d, work), out, tl_words(work))
    meta = {"track": str(track), "format": a.format, "rel_lu": rec["уровень_LU_к_голосу"], "lift_db": rec["подъём_в_паузах_dB"],
            "loop": rec.get("цикл"), "total": total}
    (mdir / "bed.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"подложка: {track.name} · {rec['уровень_LU_к_голосу']:.0f} LU к голосу · подъёмов {lifts} · {timeline.mmss(total)} → {out}")


if __name__ == "__main__":
    main()
