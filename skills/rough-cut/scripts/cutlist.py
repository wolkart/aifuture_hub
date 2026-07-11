#!/usr/bin/env python3
"""Cut-list v1 — канонический артефакт rough-cut. Только stdlib.

Времена — секунды в координатах основного видео.
sync.offset_s: audio_time = video_time + offset_s.
"""
import json

EPS = 0.02
ACTIONS = {"keep", "cut", "speedup"}
SOURCES = {"silence", "filler", "retake", "screencast", "user"}
SCENARIOS = {"camera_plus_audio", "screencast", "multicam"}
PROFILES = {"light", "full"}


def validate(d):
    if d.get("version") != 1:
        raise ValueError("cut-list: ожидается version 1")
    if d.get("scenario") not in SCENARIOS:
        raise ValueError(f"cut-list: неизвестный scenario {d.get('scenario')!r}")
    if d.get("profile") not in PROFILES:
        raise ValueError(f"cut-list: неизвестный profile {d.get('profile')!r}")
    segs, dur = d["segments"], d["duration_s"]
    if not segs:
        raise ValueError("cut-list: пустой список сегментов")
    prev_end = 0.0
    for s in segs:
        if s["action"] not in ACTIONS:
            raise ValueError(f"cut-list: неизвестное action {s['action']!r}")
        if s["end"] <= s["start"]:
            raise ValueError(f"cut-list: сегмент {s['start']}–{s['end']} пуст")
        if abs(s["start"] - prev_end) > EPS:
            raise ValueError(
                f"cut-list: дыра/пересечение на {prev_end}–{s['start']}")
        if s["action"] == "speedup" and not s.get("rate", 0) > 1:
            raise ValueError("cut-list: speedup требует rate > 1")
        if s["action"] in ("cut", "speedup") and s.get("source") not in SOURCES:
            raise ValueError(f"cut-list: {s['action']} требует source из {SOURCES}")
        prev_end = s["end"]
    if abs(prev_end - dur) > EPS:
        raise ValueError(f"cut-list: сегменты кончаются на {prev_end}, "
                         f"а длительность {dur}")


def load(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    validate(d)
    return d


def timeline(d):
    """Сегменты, попадающие на таймлайн (keep + speedup), по порядку."""
    return [s for s in d["segments"] if s["action"] != "cut"]


def from_cuts(meta, cut_segments):
    """Полный тайлинг: дыры между cut/speedup-сегментами заполняются keep."""
    segs, cursor = [], 0.0
    for c in sorted(cut_segments, key=lambda s: s["start"]):
        if c["start"] - cursor > EPS:
            segs.append({"start": round(cursor, 3), "end": round(c["start"], 3),
                         "action": "keep"})
        segs.append(dict(c))
        cursor = c["end"]
    if meta["duration_s"] - cursor > EPS:
        segs.append({"start": round(cursor, 3),
                     "end": round(meta["duration_s"], 3), "action": "keep"})
    d = {"version": 1, **meta, "segments": segs}
    validate(d)
    return d
