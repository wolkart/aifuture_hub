#!/usr/bin/env python3
"""Пословный транскрипт: mlx-whisper (Apple Silicon) / faster-whisper (остальные) /
ElevenLabs Scribe (облако, --backend scribe).

Локальный Whisper сам перезапускает себя через uv с нужной зависимостью — вызывать
можно голым python3. Первый запуск скачивает модель (~1.5 ГБ, разово).
Scribe — когда в записи много запинок («э-э», «м-м»): Whisper их обычно не пишет,
Scribe пишет дословно. Облако, ~$0.22 за час звука, нужен ELEVENLABS_API_KEY (scribe.py).
"""
import argparse
import json
import os
import platform
import sys
from pathlib import Path

import cutlist

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
    ap.add_argument("--backend", choices=["auto", "mlx", "faster", "scribe"], default="auto")
    ap.add_argument("--language", default=None, help="код языка для scribe (ru); пусто — автоопределение")
    ap.add_argument("--model", default=None)
    ap.add_argument("-o", "--out", default=None, help="куда писать words.json (по умолчанию export/)")
    ap.add_argument("--_direct", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    if args.backend == "scribe":
        import scribe
        result = scribe.run(args.audio, args.language)
        write(result, args)
        print(f"scribe: слов {len(result['words'])}, событий {len(result['events'])}, "
              f"≈ ${result['cost_usd']}", file=sys.stderr)
        return
    backend = pick_backend(override=args.backend)
    model = args.model or DEFAULT_MODEL[backend]
    if not getattr(args, "_direct"):
        os.execvp("uv", ["uv", "run", "--with", DEP[backend], "python3",
                         os.path.abspath(__file__), args.audio,
                         "--backend", backend, "--model", model, "--_direct"]
                 + (["--out", os.path.abspath(args.out)] if args.out else []))
    write(run(args.audio, backend, model), args)


def write(result, args):
    out_path = (Path(args.out) if args.out
                else cutlist.export_dir(args.audio) / (Path(args.audio).name + ".words.json"))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
