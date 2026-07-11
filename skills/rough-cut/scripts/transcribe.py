#!/usr/bin/env python3
"""Пословный транскрипт: mlx-whisper (Apple Silicon) / faster-whisper (остальные).

Сам перезапускает себя через uv с нужной зависимостью — вызывать можно
голым python3. Первый запуск скачивает модель (~1.5 ГБ, разово).
"""
import argparse
import json
import os
import platform
import sys

DEFAULT_MODEL = {"mlx": "mlx-community/whisper-large-v3-turbo", "faster": "large-v3"}
DEP = {"mlx": "mlx-whisper", "faster": "faster-whisper"}


def pick_backend(plat=sys.platform, machine=platform.machine(), override="auto"):
    if override != "auto":
        return override
    return "mlx" if plat == "darwin" and machine == "arm64" else "faster"


def normalize_mlx(result):
    words = [{"word": w["word"].strip(), "start": round(float(w["start"]), 3),
              "end": round(float(w["end"]), 3)}
             for seg in result["segments"] for w in seg.get("words", [])]
    return {"text": result["text"].strip(), "words": words}


def normalize_faster(segments):
    segments = list(segments)
    words = [{"word": w.word.strip(), "start": round(float(w.start), 3),
              "end": round(float(w.end), 3)}
             for seg in segments for w in (seg.words or [])]
    text = " ".join(seg.text.strip() for seg in segments)
    return {"text": text, "words": words}


def run(audio, backend, model):
    if backend == "mlx":
        import mlx_whisper
        return normalize_mlx(mlx_whisper.transcribe(
            str(audio), path_or_hf_repo=model, word_timestamps=True))
    from faster_whisper import WhisperModel
    segs, _info = WhisperModel(model).transcribe(str(audio), word_timestamps=True)
    return normalize_faster(segs)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("audio")
    ap.add_argument("--backend", choices=["auto", "mlx", "faster"], default="auto")
    ap.add_argument("--model", default=None)
    ap.add_argument("--_direct", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    backend = pick_backend(override=args.backend)
    model = args.model or DEFAULT_MODEL[backend]
    if not getattr(args, "_direct"):
        os.execvp("uv", ["uv", "run", "--with", DEP[backend], "python3",
                         os.path.abspath(__file__), args.audio,
                         "--backend", backend, "--model", model, "--_direct"])
    result = run(args.audio, backend, model)
    out_path = str(args.audio) + ".words.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
