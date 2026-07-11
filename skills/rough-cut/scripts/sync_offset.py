# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "scipy"]
# ///
"""Смещение между двумя записями по кросс-корреляции звука.

ref — звук видео (камера), target — чистый звук (OBS).
offset_s: audio_time = video_time + offset_s (может быть отрицательным).
confidence 0..1; < 0.2 — синхрону не верить, просить хлопок/ручное смещение.
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


def find_offset(ref, target, sr=SR):
    c = signal.correlate(target, ref, mode="full", method="fft")
    idx = int(np.argmax(np.abs(c)))
    lag = idx - (len(ref) - 1)
    denom = float(np.sqrt(np.sum(ref ** 2) * np.sum(target ** 2))) or 1.0
    confidence = min(1.0, float(np.abs(c[idx]) / denom))
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
