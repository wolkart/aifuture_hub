#!/usr/bin/env python3
"""Взгляд на склейках: кусок говорящей головы начинается, когда спикер уже смотрит
в камеру, и не тянет хвост, когда он опустил глаза в сценарий. Только stdlib + ffmpeg,
лицо — Apple Vision (macOS). Речь не режется никогда.

Зачем: спикер, читающий сценарий с экрана между фразами, на склейке ещё 0.1–0.6 с
смотрит вниз (дочитывает), а после последнего слова сразу опускает глаза. Порог
тишины этого не видит — звук там уже/ещё есть (вдох) или паддинг.

Как решает:
  • границы речи куска — первый/последний 10-мс кадр звука громче --speech-db
    (по чистому звуку cut-list, с учётом sync.offset_s);
  • «смотрит вниз» = наклон головы > (поза «в камеру» + --down-delta); поза «в камеру» —
    20-й перцентиль наклона в серединах кусков (во время речи голова гуляет, медиана
    завышена; нижний квантиль — это взгляд в объектив), считается для каждого ролика;
  • начало куска → первый кадр, с которого 2 кадра подряд взгляд не вниз, но не
    позже (начало речи − --guard); конец → первый кадр взгляда вниз после конца
    речи, но не раньше (конец речи + --guard);
  • лицо не найдено — нет улик, край не трогаем.
Срезанное становится сегментом cut с source "gaze". Исходный cut-list сохраняется
рядом как *.pregaze.json.

usage: gaze_trim.py <cutlist.json> [--down-delta 3] [--guard 0.03] [--speech-db -38] [--dry-run]
"""
import argparse
import array
import csv
import json
import math
import shutil
import statistics
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import cutlist

FPS = 30
HERE = Path(__file__).resolve().parent
CACHE = Path.home() / ".cache" / "rough-cut"


def trim_edges(start, end, onset, offset, head, tail, down, guard):
    """Чистая логика (тестируется без видео).

    head/tail: [(t, pitch|None)] по возрастанию t — кадры от start до onset и от
    offset до end. Возвращает (new_start, new_end, notes)."""
    is_down = lambda p: p is not None and p > down
    notes = []
    latest = max(start, onset - guard)  # позже нельзя: дальше уже речь
    new_start = latest  # взгляд так и не поднялся до речи — режем весь «взгляд вниз»
    for (t, p), (_, p2) in zip(head, head[1:] + [(None, None)]):
        if t > latest:
            break
        if not is_down(p) and not is_down(p2):
            new_start = t
            break
    if not head:
        new_start = start  # кадров нет — нет улик
    new_start = min(max(new_start, start), latest)
    if new_start - start < 1 / FPS:  # первый же кадр — уже в камеру
        new_start = start
    if new_start - start > 0.005:
        notes.append(f"начало +{new_start - start:.2f} с: смотрел в сценарий")
    if any(is_down(p) for t, p in head if onset + 0.05 <= t <= onset + 0.2):
        notes.append("⚠ заговорил, не подняв глаза")
    new_end = end
    for t, p in tail:
        if t >= offset + guard and is_down(p):
            new_end = max(offset + guard, t)
            break
    new_end = max(min(new_end, end), new_start + 0.05)
    if end - new_end > 0.005:
        notes.append(f"конец −{end - new_end:.2f} с: ушёл в сценарий")
    return round(new_start, 3), round(new_end, 3), notes


def speech_bounds(db_at, start, end, speech_db, step=0.01):
    ts = [start + i * step for i in range(int((end - start) / step))]
    loud = [t for t in ts if db_at(t) > speech_db]
    return (loud[0], loud[-1] + step) if loud else (None, None)


def audio_db(path, offset):
    """dB-громкость 10-мс окна в момент t ВИДЕО (audio_time = t + offset)."""
    tmp = Path(tempfile.mkdtemp()) / "a.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-vn", "-ac", "1",
                    "-ar", "16000", "-c:a", "pcm_s16le", str(tmp)], check=True)
    with wave.open(str(tmp)) as w:
        sr, pcm = w.getframerate(), array.array("h", w.readframes(w.getnframes()))

    def db_at(t):
        i = int((t + offset) * sr)
        ch = pcm[max(i, 0):max(i, 0) + sr // 100]
        if not ch:
            return -120.0
        rms = math.sqrt(sum(x * x for x in ch) / len(ch))
        return 20 * math.log10(rms / 32768) if rms > 0 else -120.0
    return db_at


def face_tool():
    """Скомпилировать face_pitch.swift один раз в ~/.cache/rough-cut. None — не macOS."""
    if sys.platform != "darwin" or not shutil.which("swiftc"):
        return None
    src, binp = HERE / "face_pitch.swift", CACHE / "face_pitch"
    if not binp.exists() or binp.stat().st_mtime < src.stat().st_mtime:
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", "-o", str(binp), str(src)], check=True,
                       capture_output=True)
    return binp


def sample_pitch(tool, video, windows):
    """windows: {key: (a, b)} → {key: [(t, pitch|None)]}. Кадры 540px, FPS кадров/с."""
    tmp = Path(tempfile.mkdtemp())
    for key, (a, b) in windows.items():
        if b - a < 1 / FPS:
            continue
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}",
                        "-i", str(video), "-vf", f"fps={FPS},scale=540:-2",
                        str(tmp / f"{key}_%04d.png")], check=True)
    out = subprocess.run([str(tool), str(tmp)], check=True, capture_output=True, text=True).stdout
    res = {k: [] for k in windows}
    for row in csv.DictReader(out.splitlines()):
        key, n = row["name"].rsplit("_", 1)
        t = windows[key][0] + (int(n.split(".")[0]) - 1) / FPS
        res[key].append((round(t, 3), float(row["pitch"]) if row["pitch"] else None))
    shutil.rmtree(tmp, ignore_errors=True)
    return {k: sorted(v) for k, v in res.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cutlist_path")
    ap.add_argument("--down-delta", type=float, default=3.0,
                    help="на сколько градусов ниже обычной позы — уже «смотрит в сценарий»")
    ap.add_argument("--guard", type=float, default=0.03, help="запас до/после речи, с")
    ap.add_argument("--speech-db", type=float, default=-38.0, help="порог речи, dB RMS")
    ap.add_argument("--dry-run", action="store_true", help="только отчёт, cut-list не менять")
    args = ap.parse_args()

    tool = face_tool()
    if tool is None:
        print("взгляд: пропущено — нужен macOS со swiftc (Apple Vision). Cut-list не изменён.")
        return
    path = Path(args.cutlist_path)
    d = cutlist.load(path)
    video = d["inputs"]["video"]
    audio = d["inputs"].get("audio") or video
    off = d.get("sync", {}).get("offset_s", 0.0) if d["inputs"].get("audio") else 0.0
    db_at = audio_db(audio, off)

    keeps = [s for s in d["segments"] if s["action"] == "keep"]
    bounds, windows = {}, {}
    for i, k in enumerate(keeps):
        on, of = speech_bounds(db_at, k["start"], k["end"], args.speech_db)
        if on is None:
            continue
        bounds[i] = (on, of)
        windows[f"h{i:03d}"] = (k["start"], on + 0.25)
        windows[f"t{i:03d}"] = (of, k["end"])
        mid = (on + of) / 2
        windows[f"m{i:03d}"] = (mid - 0.3, mid + 0.3)
    samples = sample_pitch(tool, video, windows)
    mids = [p for k, v in samples.items() if k.startswith("m") for _, p in v if p is not None]
    if not mids:
        print("взгляд: лицо не найдено в кадре — стадия неприменима. Cut-list не изменён.")
        return
    base = statistics.quantiles(mids, n=5)[0] if len(mids) >= 5 else min(mids)
    down = base + args.down_delta
    print(f"взгляд: поза «в камеру» {base:+.1f}°, «в сценарий» — наклон > {down:+.1f}°")

    new_segs, changed = [], 0
    print(f"{'#':>2} | {'кусок':>15} | {'речь':>15} | изменения")
    for i, k in enumerate(keeps):
        s, e, notes = k["start"], k["end"], []
        if i in bounds:
            on, of = bounds[i]
            s, e, notes = trim_edges(k["start"], k["end"], on, of,
                                     samples.get(f"h{i:03d}", []), samples.get(f"t{i:03d}", []),
                                     down, args.guard)
            print(f"{i:2d} | {k['start']:6.2f}–{k['end']:6.2f} | {on:6.2f}–{of:6.2f} | {'; '.join(notes) or '—'}")
        changed += bool(notes)
        k["new"] = (s, e, notes)
    for seg in d["segments"]:
        if seg["action"] != "keep" or "new" not in seg:
            new_segs.append(seg)
            continue
        s, e, notes = seg.pop("new")
        if s > seg["start"] + 1e-3:
            new_segs.append({"start": seg["start"], "end": s, "action": "cut", "source": "gaze",
                             "reason": "смотрит в сценарий до фразы", "confidence": 0.85})
        new_segs.append({**seg, "start": s, "end": e})
        if e < seg["end"] - 1e-3:
            new_segs.append({"start": e, "end": seg["end"], "action": "cut", "source": "gaze",
                             "reason": "смотрит в сценарий после фразы", "confidence": 0.85})
    d["segments"] = new_segs
    cutlist.validate(d)
    if args.dry_run:
        print(f"dry-run: изменилось бы кусков {changed}")
        return
    backup = path.with_name(path.name.replace(".cutlist.json", "") + ".cutlist.pregaze.json")
    if not backup.exists():
        shutil.copy(path, backup)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"взгляд: изменено кусков {changed} из {len(keeps)}; до правки — {backup.name}")


if __name__ == "__main__":
    main()
