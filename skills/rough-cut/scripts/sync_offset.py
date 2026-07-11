# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "scipy"]
# ///
"""Смещение между двумя записями по кросс-корреляции звука.

ref — звук видео (камера), target — чистый звук (OBS).
offset_s: audio_time = video_time + offset_s (может быть отрицательным).

confidence 0..1 — насколько пик корреляции УНИКАЛЕН (peak-to-sidelobe):
1 − (второй по величине пик вне защитной зоны) / (главный пик). Не зависит
от разности тембров микрофонов — только от однозначности выравнивания.
< 0.5 — синхрону не верить, просить хлопок в начале записи/ручное смещение.
"""
import argparse
import json
import subprocess

import numpy as np
from scipy import signal

SR = 8000


def extract_pcm(path, sr=SR, max_seconds=600):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-t", str(max_seconds),
         "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def find_offset(ref, target, sr=SR, guard_s=0.25):
    c = np.abs(signal.correlate(target, ref, mode="full", method="fft"))
    idx = int(np.argmax(c))
    peak = float(c[idx])
    lag = idx - (len(ref) - 1)
    if peak <= 0:
        return lag / sr, 0.0
    guard = int(guard_s * sr)
    masked = c.copy()
    masked[max(0, idx - guard):idx + guard + 1] = 0.0
    second = float(masked.max()) if masked.size else 0.0
    confidence = max(0.0, min(1.0, 1.0 - second / peak))
    return lag / sr, confidence


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref", required=True, help="видео (его звуковая дорожка)")
    ap.add_argument("--target", required=True, help="чистый звук (OBS)")
    ap.add_argument("--max-seconds", type=int, default=600)
    args = ap.parse_args()
    off, conf = find_offset(extract_pcm(args.ref, max_seconds=args.max_seconds),
                            extract_pcm(args.target, max_seconds=args.max_seconds))
    print(json.dumps({"offset_s": round(off, 4), "confidence": round(conf, 3)}))


if __name__ == "__main__":
    main()
