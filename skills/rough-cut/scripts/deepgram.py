#!/usr/bin/env python3
"""Пословный транскрипт через Deepgram Nova-3 (облако). Только stdlib + ffmpeg.

Запасной облачный путь, когда Scribe недоступен (кончились кредиты ElevenLabs): тоже
точные пословные времена — по ним рез посреди фразы не попадает в слово, в отличие от
локального Whisper, который сбивает время после пауз. Русский поддерживается.
Запинки: включён filler_words, но для русского Deepgram их пишет хуже Scribe —
проверено не было, поэтому дубли и «ух» всё равно сверять по звуку.

Цена (обзоры, 2026-10): Nova-3 pre-recorded ≈ $0.0043 за минуту (~$0.26 за час); при
регистрации дают $200 кредита. Звук уходит в облако Deepgram; ключ DEEPGRAM_API_KEY
(окружение или .env рядом со скиллом). Перед отправкой звук сжимается в моно Opus 32 кбит/с.

Выход — тот же формат, что у transcribe.py: {text, words:[{word,start,end}], events, backend}.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import scribe  # compress() и разбор .env — общие

URL = "https://api.deepgram.com/v1/listen"
MODEL = "nova-3"
PRICE_PER_HOUR = 0.26
SKILL_ROOT = Path(__file__).resolve().parent.parent
RETRY = (5, 15, 30, 60)


def api_key(env_file=None):
    """DEEPGRAM_API_KEY из окружения, иначе из .env рядом со скиллом."""
    if os.environ.get("DEEPGRAM_API_KEY"):
        return os.environ["DEEPGRAM_API_KEY"]
    p = Path(env_file) if env_file else SKILL_ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            k, _, v = line.strip().partition("=")
            if k.strip() == "DEEPGRAM_API_KEY" and v.strip():
                return v.strip().strip("\"'")
    return None


def params(language=None):
    q = {"model": MODEL, "punctuate": "true", "filler_words": "true", "smart_format": "false"}
    q["language"] = language or "ru"
    return q


def normalize(resp):
    """Ответ Deepgram → формат transcribe.py. Слово с пунктуацией — punctuated_word."""
    alt = resp["results"]["channels"][0]["alternatives"][0]
    words = []
    for w in alt.get("words", []):
        text = (w.get("punctuated_word") or w.get("word") or "").strip()
        if not text or w.get("start") is None or w.get("end") is None:
            continue
        words.append({"word": text, "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3)})
    return {"text": alt.get("transcript", "").strip(), "words": words, "events": [], "backend": "deepgram"}


def cost(seconds):
    return round(seconds / 3600 * PRICE_PER_HOUR, 4)


def post(body, key, query, timeout, sleep=time.sleep, opener=urllib.request.urlopen):
    url = URL + "?" + urllib.parse.urlencode(query)
    for attempt, wait in enumerate(list(RETRY) + [None]):
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Authorization": f"Token {key}", "Content-Type": "audio/ogg"})
        try:
            with opener(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:500]
            if wait is None or not scribe.retriable(e.code):
                raise SystemExit(f"deepgram: HTTP {e.code} — {msg}")
            print(f"deepgram: HTTP {e.code}, повтор через {wait} с (попытка {attempt + 2})", flush=True)
            sleep(wait)


def run(audio, language=None, key=None, timeout=1800):
    key = key or api_key()
    if not key:
        raise SystemExit("deepgram: нет DEEPGRAM_API_KEY (окружение или .env рядом со скиллом, "
                         "шаблон — .env.template). Без ключа — локальный whisper: --backend auto")
    ogg = scribe.compress(audio)
    resp = post(ogg.read_bytes(), key, params(language), timeout)
    out = normalize(resp)
    secs = float(resp.get("metadata", {}).get("duration") or (out["words"][-1]["end"] if out["words"] else 0))
    out["cost_usd"] = cost(secs)
    return out
