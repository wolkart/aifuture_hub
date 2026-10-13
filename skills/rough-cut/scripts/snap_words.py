#!/usr/bin/env python3
"""Подтягивает пословные таймкоды Whisper к реальному звуку. Только stdlib + ffmpeg.

Зачем: после паузы Whisper ставит первое слово фразы в тишину перед ним — на
0.3–0.4 с раньше голоса. Для резки это терпимо, для субтитров и графики, привязанных
к словам, — нет: подпись выскакивает до того, как человек заговорил.

Как: если первые 40 мс слова тише --quiet, начало сдвигается на первый 10-мс кадр
громче --loud (минус 20 мс на атаку); хвост, ушедший в тишину дольше 0.1 с,
подрезается до последнего громкого кадра. Слова, начавшиеся в речи, не трогаются.

usage: snap_words.py <words.json> <audio|video> [-o out.json] [--loud -38] [--quiet -48]
words.json — выход transcribe.py ({text, words:[{word,start,end}]}); поле text
у слова тоже принимается.
"""
import argparse
import array
import json
import math
import subprocess
import tempfile
import wave
from pathlib import Path

STEP = 0.01


def snap(words, db_at, loud=-38.0, quiet=-48.0):
    """Чистая логика: words [{start,end,…}] → новый список, сколько сдвинуто."""
    out, moved = [dict(w) for w in words], 0
    for w in out:
        if max(db_at(w["start"] + k * STEP) for k in range(4)) < quiet:
            t = w["start"]
            while t < w["end"] - 0.05 and db_at(t) < loud:
                t += STEP
            if t - w["start"] > 0.03:
                w["start"] = round(t - 0.02, 3)
                moved += 1
        t = w["end"]
        while t > w["start"] + 0.08 and db_at(t - STEP) < quiet:
            t -= STEP
        if w["end"] - t > 0.1:
            w["end"] = round(t + 0.05, 3)
    for a, b in zip(out, out[1:]):
        if b["start"] < a["end"]:
            a["end"] = b["start"]
    return out, moved


def db_reader(path):
    tmp = Path(tempfile.mkdtemp()) / "a.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-vn", "-ac", "1",
                    "-ar", "16000", "-c:a", "pcm_s16le", str(tmp)], check=True)
    with wave.open(str(tmp)) as w:
        sr, pcm = w.getframerate(), array.array("h", w.readframes(w.getnframes()))

    def db_at(t):
        i = max(int(t * sr), 0)
        ch = pcm[i:i + int(sr * STEP)]
        if not ch:
            return -120.0
        rms = math.sqrt(sum(x * x for x in ch) / len(ch))
        return 20 * math.log10(rms / 32768) if rms > 0 else -120.0
    return db_at


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words_json")
    ap.add_argument("audio")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--loud", type=float, default=-38.0)
    ap.add_argument("--quiet", type=float, default=-48.0)
    args = ap.parse_args()
    d = json.load(open(args.words_json, encoding="utf-8"))
    words, moved = snap(d["words"], db_reader(args.audio), args.loud, args.quiet)
    d["words"] = words
    out = Path(args.out or args.words_json)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"snap: сдвинуто к звуку {moved} из {len(words)} слов → {out}")


if __name__ == "__main__":
    main()
