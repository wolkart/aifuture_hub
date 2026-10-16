#!/usr/bin/env python3
"""Пословный транскрипт через ElevenLabs Scribe (облако). Только stdlib + ffmpeg.

Зачем, если есть локальный Whisper: Whisper «чистит» речь и запинки («э-э», «м-м»)
в транскрипт обычно не пишет — тогда стадия Decide их не видит и на длинной записи
они остаются. Scribe по умолчанию пишет речь дословно, с запинками; флаг
no_verbatim (вычистить их) явно выключен. Плюс неречевые звуки — отдельным
списком events («(смех)», «(кашель)»).

Цена (прайс ElevenLabs, 2026-10): scribe_v2 — $0.22 за час звука; рилс — доли цента,
часовой ролик — ~22 цента. Звук уходит в облако ElevenLabs; нужен интернет и ключ
ELEVENLABS_API_KEY (окружение или .env рядом со скиллом). Перед отправкой звук
сжимается в моно Opus 32 кбит/с: час ≈ 14 МБ.

Выход — тот же формат, что у transcribe.py: {text, words:[{word,start,end}], events, backend}.
"""
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

URL = "https://api.elevenlabs.io/v1/speech-to-text"
MODEL = "scribe_v2"
PRICE_PER_HOUR = 0.22
SKILL_ROOT = Path(__file__).resolve().parent.parent


def api_key(env_file=None):
    """ELEVENLABS_API_KEY из окружения, иначе из .env рядом со скиллом."""
    if os.environ.get("ELEVENLABS_API_KEY"):
        return os.environ["ELEVENLABS_API_KEY"]
    p = Path(env_file) if env_file else SKILL_ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            k, _, v = line.strip().partition("=")
            if k.strip() == "ELEVENLABS_API_KEY" and v.strip():
                return v.strip().strip("\"'")
    return None


def multipart(fields, file_field, file_name, file_bytes, content_type="audio/ogg"):
    """Тело multipart/form-data → (bytes, заголовок Content-Type)."""
    boundary = uuid.uuid4().hex
    out = bytearray()
    for name, value in fields.items():
        out += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                f"{value}\r\n").encode("utf-8")
    out += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
            f"filename=\"{file_name}\"\r\nContent-Type: {content_type}\r\n\r\n").encode("utf-8")
    out += file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def fields(language=None):
    f = {"model_id": MODEL, "timestamps_granularity": "word", "tag_audio_events": "true",
         "no_verbatim": "false"}
    if language:
        f["language_code"] = language
    return f


def normalize(resp):
    """Ответ Scribe → формат transcribe.py. spacing (паузы) не нужны — они видны по
    промежуткам между словами; audio_event — отдельным списком."""
    words, events = [], []
    for w in resp.get("words", []):
        if w.get("start") is None or w.get("end") is None:
            continue
        item = {"word": w["text"].strip(), "start": round(float(w["start"]), 3),
                "end": round(float(w["end"]), 3)}
        if w.get("type") == "word" and item["word"]:
            words.append(item)
        elif w.get("type") == "audio_event":
            events.append(item)
    return {"text": resp.get("text", "").strip(), "words": words, "events": events, "backend": "scribe"}


def cost(seconds):
    return round(seconds / 3600 * PRICE_PER_HOUR, 4)


def compress(src):
    """Звук → моно Opus 32 кбит/с во временный файл (для загрузки)."""
    out = Path(tempfile.mkdtemp()) / "audio.ogg"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000",
                    "-c:a", "libopus", "-b:a", "32k", str(out)], check=True)
    return out


RETRY = (5, 15, 30, 60)   # пауза перед повтором, с: 429 «system busy» и 5xx у них бывают днём


def retriable(code):
    return code == 429 or 500 <= code < 600


def post(body, ctype, key, timeout, sleep=time.sleep, opener=urllib.request.urlopen):
    """POST с повторами при перегрузке сервера; 4xx кроме 429 — сразу ошибка (ключ, формат)."""
    for attempt, wait in enumerate(list(RETRY) + [None]):
        req = urllib.request.Request(URL, data=body, method="POST",
                                     headers={"xi-api-key": key, "Content-Type": ctype})
        try:
            with opener(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:500]
            if wait is None or not retriable(e.code):
                raise SystemExit(f"scribe: HTTP {e.code} — {msg}")
            print(f"scribe: HTTP {e.code}, повтор через {wait} с (попытка {attempt + 2})", flush=True)
            sleep(wait)


def run(audio, language=None, key=None, timeout=1800):
    key = key or api_key()
    if not key:
        raise SystemExit("scribe: нет ELEVENLABS_API_KEY (окружение или .env рядом со скиллом, "
                         "шаблон — .env.template). Без ключа — локальный whisper: --backend auto")
    ogg = compress(audio)
    body, ctype = multipart(fields(language), "file", ogg.name, ogg.read_bytes())
    resp = post(body, ctype, key, timeout)
    out = normalize(resp)
    secs = float(resp.get("audio_duration_secs") or (out["words"][-1]["end"] if out["words"] else 0))
    out["cost_usd"] = cost(secs)
    return out
