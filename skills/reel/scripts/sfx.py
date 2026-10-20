#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy"]
# ///
"""Звуки монтажа: синтез (без чужих файлов и лицензий) и дорожка звуков по словам плана.

Каталог (у каждого — свой жест или событие в кадре):
  whoosh — вжух: наезд камеры, панель въезжает;      swish  — свист: смахнул рукой;
  down   — «шшш» вниз: опустил субтитры, стянул шторку; up — то же вверх;
  impact — удар: предмет приземлился, слово-печать;   pop    — щелчок: наклейка, карточка;
  type   — печать клавиш (длина — dur);                tap    — тап по кнопке/ссылке;
  snip   — ножницы: кусок вырезан;                    select — выбран вариант (зелёная галочка);
  reward — переливчатый «приз»: крупная цифра, итог, особое появление.
Своя папка звуков в настройках (папки.звуки) перебивает синтез по имени файла: whoosh.wav и т. д.
Вариации: pop.wav, pop-2.wav, pop-3.wav … — звучат по очереди (одинаковые появления подряд не
звучат одинаково, как у монтажёров с библиотекой звуков).

В plan.json:
  "sfx": [{"at": <якорь>, "sound": "whoosh", "db": -8, "dur": 0.6, "shift": 0.0}]
  "sound" — имя из каталога или путь к своему 16-бит WAV («ту-ду-ду» под мем и т. п.).
db — пик звука в dBFS (по умолчанию −10); голос в финале −14 LUFS, звуки ложатся под него.

usage: uv run sfx.py bed <папка варианта> [--settings reel.settings.json]
       → <вариант>/sfx.wav на всю длину ролика (её подмешивает composite.py final)
       uv run sfx.py cues <cues.json> --out <файл.wav> --total <секунд> [--settings …]
       → звуки сцены motion-assets по её событиям: cues.json — [[t, звук, dB], …]
"""
import argparse
import json
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000
SOUNDS = ("whoosh", "swish", "down", "up", "impact", "pop", "type", "tap", "snip", "select", "reward")


def _env(n, attack, release):
    """Огибающая: подъём attack, спад release (доли длины), синусоидальные края."""
    t = np.linspace(0, 1, n)
    e = np.ones(n)
    a, r = max(1, int(n * attack)), max(1, int(n * release))
    e[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    e[-r:] = np.cos(np.linspace(0, np.pi / 2, r)) ** 2
    return e * (0.6 + 0.4 * np.sin(np.pi * t))


def _sweep_noise(dur, f0, f1, f2=None, width=0.55, seed=1):
    """Шум, у которого «окно» частот едет f0 → f1 (→ f2): так звучит пролёт мимо уха."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    hop, win = 256, 1024
    x = rng.standard_normal(n + win)
    out = np.zeros(n + win)
    w = np.hanning(win)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    frames = range(0, n, hop)
    for k, i in enumerate(frames):
        p = i / max(1, n - 1)
        if f2 is None:
            fc = f0 * (f1 / f0) ** p
        else:
            fc = f0 * (f1 / f0) ** (2 * p) if p < 0.5 else f1 * (f2 / f1) ** (2 * p - 1)
        spec = np.fft.rfft(x[i:i + win] * w)
        band = np.exp(-0.5 * (np.log(np.maximum(freqs, 1) / fc) / width) ** 2)
        out[i:i + win] += np.fft.irfft(spec * band) * w
    y = out[:n]
    return y / (np.abs(y).max() + 1e-9)


def _pan(y, l0, l1):
    """Моно → стерео с переездом слева направо (l — доля левого канала)."""
    lt = np.linspace(l0, l1, len(y))
    return np.stack([y * np.sqrt(lt), y * np.sqrt(1 - lt)], axis=1)


def _sub(dur, f0, f1, f2):
    """Суб-тон: синус, частота f0 → f1 → f2 — низ, который слышно на телефоне как «тело»."""
    n = int(dur * SR)
    p = np.linspace(0, 1, n)
    f = np.where(p < 0.5, f0 + (f1 - f0) * p * 2, f1 + (f2 - f1) * (p - 0.5) * 2)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def _click(n_ms=5, f=3000, seed=0):
    rng = np.random.default_rng(seed)
    n = int(n_ms / 1000 * SR)
    t = np.arange(n) / SR
    y = rng.standard_normal(n) * np.exp(-t * 900) + 0.6 * np.sin(2 * np.pi * f * t) * np.exp(-t * 700)
    return y / (np.abs(y).max() + 1e-9)


def synth(name, dur=None):
    """→ стерео float32 [-1, 1]."""
    if name == "whoosh":   # верх — воздух, низ — тело: без низа вжух звучит тонко
        d = dur or 0.42
        n = int(d * SR)
        hi = _sweep_noise(d, 250, 2600, 700, seed=3)
        lo = _sweep_noise(d, 55, 320, 90, width=0.8, seed=4)
        y = (0.55 * hi + 1.0 * lo + 0.45 * _sub(d, 48, 95, 52)) * _env(n, 0.45, 0.4)
        return _pan(y / (np.abs(y).max() + 1e-9), 0.75, 0.25)
    if name == "swish":
        d = dur or 0.3
        n = int(d * SR)
        hi = _sweep_noise(d, 1200, 6000, width=0.45, seed=5)
        lo = _sweep_noise(d, 90, 500, width=0.7, seed=6)
        y = (0.6 * hi + 0.8 * lo + 0.3 * _sub(d, 70, 120, 70)) * _env(n, 0.3, 0.55)
        return _pan(y / (np.abs(y).max() + 1e-9), 0.85, 0.15)
    if name in ("down", "up"):
        d = dur or 0.5
        n = int(d * SR)
        f = (2800, 220) if name == "down" else (220, 2800)
        lo_f = (380, 50) if name == "down" else (50, 380)
        y = (0.6 * _sweep_noise(d, *f, width=0.5, seed=7) + 0.9 * _sweep_noise(d, *lo_f, width=0.8, seed=8)
             + 0.35 * _sub(d, *((110, 45, 45) if name == "down" else (45, 110, 110)))) * _env(n, 0.2, 0.5)
        return _pan(y / (np.abs(y).max() + 1e-9), 0.5, 0.5)
    if name == "impact":
        d = dur or 0.6
        n = int(d * SR)
        t = np.arange(n) / SR
        f = 45 + 45 * np.exp(-t * 18)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
        hit = np.zeros(n)
        c = _click(12, 1800, seed=9)
        hit[:len(c)] = c * 0.5
        noise = np.random.default_rng(11).standard_normal(n) * np.exp(-t * 25) * 0.15
        y = body + hit + noise
        return _pan(y / np.abs(y).max(), 0.5, 0.5)
    if name == "pop":
        d = dur or 0.13
        n = int(d * SR)
        t = np.arange(n) / SR
        f = 380 + 700 * np.exp(-t * 60)
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32)
        c = _click(3, 4000, seed=13)
        y[:len(c)] += c * 0.3
        return _pan(y / np.abs(y).max(), 0.5, 0.5)
    if name in ("tap", "snip"):
        n = int((dur or (0.09 if name == "tap" else 0.16)) * SR)
        y = np.zeros(n)
        c = _click(6 if name == "tap" else 4, 2200 if name == "tap" else 5200, seed=17)
        y[:len(c)] += c
        if name == "snip":
            k = int(0.045 * SR)
            y[k:k + len(c)] += c * 0.8
        return _pan(y, 0.5, 0.5)
    if name == "type":
        d = dur or 0.8
        n = int(d * SR)
        y = np.zeros(n)
        rng = np.random.default_rng(19)
        i = 0
        while i < n:
            c = _click(rng.uniform(4, 7), rng.uniform(2200, 3600), seed=int(rng.integers(1e6)))
            g = rng.uniform(0.55, 1.0)
            y[i:i + len(c)] += c[:max(0, min(len(c), n - i))] * g
            i += int(rng.uniform(0.055, 0.095) * SR)
        return _pan(y / (np.abs(y).max() + 1e-9), 0.5, 0.5)
    if name == "select":   # мягкий «тук» + короткая восходящая пара нот
        n = int((dur or 0.32) * SR)
        t = np.arange(n) / SR
        y = np.zeros(n)
        c = _click(5, 1500, seed=23)
        y[:len(c)] += c * 0.35
        for f0, at in ((1046.5, 0.0), (1568.0, 0.055)):
            k = int(at * SR)
            tt = t[:n - k]
            y[k:] += (np.sin(2 * np.pi * f0 * tt) + 0.25 * np.sin(2 * np.pi * 2 * f0 * tt)) * np.exp(-tt * 22) * 0.6
        return _pan(y / (np.abs(y).max() + 1e-9), 0.5, 0.5)
    if name == "reward":   # колокольчики вверх по арпеджио + искры: «открыл сундук»
        d = dur or 1.1
        n = int(d * SR)
        t = np.arange(n) / SR
        L, R = np.zeros(n), np.zeros(n)
        notes = (1318.5, 1661.2, 1975.5, 2637.0, 3322.4)        # ми-мажор вверх
        for i, f0 in enumerate(notes):
            k = int(i * 0.055 * SR)
            tt = t[:n - k]
            bell = sum(a * np.sin(2 * np.pi * f0 * m * tt) * np.exp(-tt * dk)
                       for m, a, dk in ((1, 1.0, 5.5), (2.76, 0.35, 9), (5.4, 0.12, 14)))
            pan = 0.3 + 0.4 * i / (len(notes) - 1)
            L[k:] += bell * (1 - pan) * (0.9 if i < len(notes) - 1 else 1.1)
            R[k:] += bell * pan * (0.9 if i < len(notes) - 1 else 1.1)
        rng = np.random.default_rng(29)
        for _ in range(16):                                      # искры
            k = int(rng.uniform(0.12, 0.75) * SR)
            f0 = rng.uniform(4200, 7800)
            tt = t[:min(n - k, int(0.12 * SR))]
            sp = np.sin(2 * np.pi * f0 * tt) * np.exp(-tt * 45) * rng.uniform(0.08, 0.2)
            side = rng.uniform(0, 1)
            L[k:k + len(tt)] += sp * (1 - side)
            R[k:k + len(tt)] += sp * side
        y = np.stack([L, R], axis=1) * _env(n, 0.01, 0.35)[:, None]
        return y / (np.abs(y).max() + 1e-9)
    raise ValueError(f"звук {name!r}: есть {', '.join(SOUNDS)}")


def read_wav(path):
    with wave.open(str(path)) as f:
        ch, sw, sr, n = f.getnchannels(), f.getsampwidth(), f.getframerate(), f.getnframes()
        raw = f.readframes(n)
    if sw != 2:
        raise ValueError(f"{path}: нужен 16-бит WAV")
    y = np.frombuffer(raw, np.int16).astype(np.float32).reshape(-1, ch) / 32768
    if ch == 1:
        y = np.repeat(y, 2, axis=1)
    if sr != SR:
        idx = np.linspace(0, len(y) - 1, int(len(y) * SR / sr))
        y = np.stack([np.interp(idx, np.arange(len(y)), y[:, k]) for k in range(2)], axis=1)
    return y


def variants(name, folder):
    """Свои файлы звука по очереди: name.wav, затем name-2.wav, name-3.wav …"""
    if not folder:
        return []
    f = Path(folder)
    extra = sorted(f.glob(f"{name}-*.wav"), key=lambda p: (len(p.stem), p.stem))
    return ([f / f"{name}.wav"] if (f / f"{name}.wav").exists() else []) + extra


def sound(name, dur=None, folder=None, k=0):
    """Путь к WAV — этот файл; свой файл из папки звуков (k-я вариация по кругу), если есть; иначе синтез."""
    if str(name).lower().endswith(".wav"):
        return read_wav(Path(name).expanduser())
    vs = variants(name, folder)
    if vs:
        return read_wav(vs[k % len(vs)])
    return synth(name, dur)


def place(events, total, folder=None):
    """events: [(t, name, db, dur)] → стерео дорожка длиной total секунд; вариации звука — по очереди."""
    bed = np.zeros((int(total * SR) + SR, 2), np.float32)
    seen = {}
    for t, name, db, dur in sorted(events, key=lambda e: e[0]):
        k = seen.get(name, 0)
        seen[name] = k + 1
        y = sound(name, dur, folder, k)
        y = y / (np.abs(y).max() + 1e-9) * 10 ** (db / 20)
        i = max(0, int(t * SR))
        j = min(len(bed), i + len(y))
        bed[i:j] += y[:j - i]
    return bed[:int(total * SR)]


def write_wav(path, y):
    y = np.clip(y, -1, 1)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((y * 32767).astype(np.int16).tobytes())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("op", choices=["bed", "demo", "cues"])
    ap.add_argument("variant", help="bed — папка варианта; demo — файл .wav; cues — cues.json")
    ap.add_argument("--settings", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--total", type=float, default=None)
    args = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if args.op == "cues":   # звуки сцены motion-assets: [[t, звук, dB], …]
        import settings as settings_mod
        s = settings_mod.load(args.settings) or settings_mod.default()
        folder = (s.get("folders") or {}).get("sfx")
        cues = json.loads(Path(args.variant).read_text(encoding="utf-8"))
        evs = [(float(c[0]), c[1], float(c[2]) if len(c) > 2 else -12.0, None) for c in cues]
        total = args.total or (max((e[0] for e in evs), default=0) + 1.5)
        write_wav(args.out, place(evs, total, folder))
        print(f"звуки сцены: {len(evs)} → {args.out}")
        return
    if args.op == "demo":   # все звуки подряд — послушать
        out = Path(args.variant)
        evs, t = [], 0.3
        for name in SOUNDS:
            evs.append((t, name, -6, None))
            t += 1.0
        write_wav(out, place(evs, t + 0.5))
        print(f"демо звуков: {out} ({', '.join(SOUNDS)})")
        return
    import hf
    import settings as settings_mod
    import words as wmod
    from layout import Build
    b = Build(args.variant)
    plan = b.load_plan()
    s = settings_mod.load(args.settings) or settings_mod.default()
    folder = (s.get("folders") or {}).get("sfx")
    words = wmod.load(b.transcript)
    dur = round(hf.duration(b.roughcut) - 0.02, 3)
    evs = []
    for e in plan.get("sfx", []):
        t = round(wmod.at(words, e["at"]) + float(e.get("shift", 0)), 3)
        evs.append((t, e["sound"], float(e.get("db", -10)), e.get("dur")))
    out = b.var / "sfx.wav"
    write_wav(out, place(evs, dur, folder))
    for t, name, db, _ in sorted(evs):
        print(f"  {t:6.2f}  {Path(str(name)).stem:7s} {db:+.0f} dBFS")
    print(f"звуки: {len(evs)} → {out}")


if __name__ == "__main__":
    main()
