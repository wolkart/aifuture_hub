# rough-cut Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Публичный hub-скилл `rough-cut` — черновой монтаж: синхронизация звука OBS с видео камеры, вырезание тишины/филлеров/дублей, скринкаст-таймлапсы; выход — cut-list JSON → FCPXML (Resolve) и/или ffmpeg-рендер (mp4).

**Architecture:** Детерминированные Python-скрипты (механика: доктор, probe, синхрон, тишина, транскрипт, кадры, экспортёры) + Claude в сессии как «мозг» стадии Decide (дубли по транскрипту, решения по кадрам скринкаста). Канонический артефакт — cut-list JSON; вся логика в скриптах, SKILL.md — только оркестрация. Спек: `docs/superpowers/specs/2026-07-11-rough-cut-skill-design.md`.

**Tech Stack:** Python ≥3.10, ffmpeg/ffprobe, uv (PEP 723 инлайн-зависимости), numpy/scipy (только синхрон), mlx-whisper / faster-whisper (транскрипт), pytest (тесты).

## Global Constraints

- Ветка: `rough-cut-skill` (уже создана, спек закоммичен). Работаем в `/Users/wolkart/AI/aifuture_hub`.
- Скрипты — stdlib-only, где возможно; сторонние зависимости только через PEP 723 блок `# /// script` + запуск `uv run`.
- `check_env.py` обязан работать на голом `python3` (никаких сторонних импортов, никакого uv).
- Каждый скрипт — CLI, результат — JSON в stdout (флаги и человекочитаемый вывод — поверх, но JSON всегда доступен).
- **Страж: исходники никогда не перезаписываются.** Все артефакты — новые файлы; рендер отказывается писать в существующий файл без `--force` и никогда — в путь, совпадающий со входом.
- Скилл обезличенный (публичный хаб): никаких личных путей/ниш/CTA; пороги — параметры с дефолтами.
- Все тексты скилла (SKILL.md, references, README, сообщения скриптов) — на русском, стиль остальных скиллов хаба.
- Тесты: `cd /Users/wolkart/AI/aifuture_hub/skills/rough-cut && uv run --with pytest --with numpy --with scipy python -m pytest tests -v`.
- Времена в cut-list — секунды (float) в системе координат **основного видео**; `sync.offset_s`: `audio_time = video_time + offset_s`.
- Коммит после каждой задачи.

---

### Task 1: Скелет скилла + доктор `check_env.py`

**Files:**
- Create: `skills/rough-cut/scripts/check_env.py`
- Test: `skills/rough-cut/tests/test_check_env.py`

**Interfaces:**
- Produces: CLI `python3 scripts/check_env.py --json` → `{"ok": bool, "platform": str, "whisper_backend": "mlx-whisper"|"faster-whisper", "whisper_note": str, "missing": [{"name": str, "install": str}]}`; функции `whisper_backend(plat, machine)`, `report()`.

- [ ] **Step 1: Написать падающий тест**

`skills/rough-cut/tests/test_check_env.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_env  # noqa: E402


def test_whisper_backend_apple_silicon():
    assert check_env.whisper_backend("darwin", "arm64") == "mlx-whisper"


def test_whisper_backend_other_platforms():
    assert check_env.whisper_backend("darwin", "x86_64") == "faster-whisper"
    assert check_env.whisper_backend("linux", "x86_64") == "faster-whisper"
    assert check_env.whisper_backend("win32", "AMD64") == "faster-whisper"


def test_report_structure():
    r = check_env.report()
    assert set(r) >= {"ok", "platform", "whisper_backend", "whisper_note", "missing"}
    for m in r["missing"]:
        assert m["name"] and m["install"]


def test_cli_json_on_bare_python():
    """Доктор обязан работать на голом python3 без сторонних пакетов."""
    p = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_env.py"), "--json"],
        capture_output=True, text=True)
    assert p.returncode == 0
    data = json.loads(p.stdout)
    assert isinstance(data["ok"], bool)
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `cd /Users/wolkart/AI/aifuture_hub/skills/rough-cut && uv run --with pytest --with numpy --with scipy python -m pytest tests -v`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'check_env'`

- [ ] **Step 3: Реализация**

`skills/rough-cut/scripts/check_env.py`:

```python
#!/usr/bin/env python3
"""Доктор rough-cut: что есть, чего не хватает, как поставить. Только stdlib."""
import argparse
import json
import platform
import shutil
import sys

INSTALL = {
    "darwin": {"ffmpeg": "brew install ffmpeg", "uv": "brew install uv"},
    "linux": {"ffmpeg": "sudo apt install ffmpeg",
              "uv": "curl -LsSf https://astral.sh/uv/install.sh | sh"},
    "win32": {"ffmpeg": "winget install Gyan.FFmpeg",
              "uv": "winget install astral-sh.uv"},
}


def os_key(plat=sys.platform):
    if plat.startswith("linux"):
        return "linux"
    return plat if plat in INSTALL else "linux"


def whisper_backend(plat=sys.platform, machine=platform.machine()):
    """mlx-whisper только на Apple Silicon, иначе кроссплатформенный faster-whisper."""
    return "mlx-whisper" if plat == "darwin" and machine == "arm64" else "faster-whisper"


def report():
    cmds = INSTALL[os_key()]
    missing = [{"name": t, "install": cmds[t]}
               for t in ("ffmpeg", "uv") if shutil.which(t) is None]
    return {
        "ok": not missing,
        "platform": f"{sys.platform}/{platform.machine()}",
        "whisper_backend": whisper_backend(),
        "whisper_note": ("модель whisper скачается при первом транскрипте "
                         "(~1.5 ГБ, разово); без транскрипта доступен режим "
                         "«только тишина»"),
        "missing": missing,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="только JSON")
    args = ap.parse_args()
    r = report()
    if args.json:
        print(json.dumps(r, ensure_ascii=False))
        return
    print(f"Платформа: {r['platform']}  |  whisper-бэкенд: {r['whisper_backend']}")
    if r["ok"]:
        print("Окружение готово. " + r["whisper_note"])
    else:
        print("Не хватает:")
        for m in r["missing"]:
            print(f"  {m['name']}: {m['install']}")
        print(r["whisper_note"])
    print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Тесты зелёные**

Run: та же команда из Step 2.
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add skills/rough-cut && git commit -m "rough-cut: скелет + доктор check_env (проверка окружения, платформенные команды установки, выбор whisper-бэкенда)"
```

---

### Task 2: Тестовые фикстуры (conftest) + `probe.py`

**Files:**
- Create: `skills/rough-cut/tests/conftest.py`
- Create: `skills/rough-cut/scripts/probe.py`
- Test: `skills/rough-cut/tests/test_probe.py`

**Interfaces:**
- Produces: fixture `media_dir` (session-scoped): `tone_gap.wav` (тон 1с + тишина 3с + тон 1с, 16 кГц), `sync_ref.wav` (шум 4с), `sync_shifted.wav` (тишина 1.5с + тот же шум), `clip.mp4` (testsrc 6с 320×240 30fps + синус-тон).
- Produces: `probe.probe(path) -> dict` c ключами `path, duration_s, has_video, has_audio` (+ для видео: `fps: {num, den}, width, height`); CLI `probe.py FILE... --json` → список таких dict.

- [ ] **Step 1: conftest с фикстурами**

`skills/rough-cut/tests/conftest.py`:

```python
import math
import random
import struct
import subprocess
import sys
import wave
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

SR = 16000


def write_wav(path, chunks):
    """chunks: [(kind, seconds)], kind ∈ {'tone','silence','noise'}. Детерминированно."""
    rnd = random.Random(42)
    frames = bytearray()
    for kind, sec in chunks:
        for i in range(int(SR * sec)):
            if kind == "tone":
                v = int(12000 * math.sin(2 * math.pi * 440 * i / SR))
            elif kind == "noise":
                v = rnd.randint(-12000, 12000)
            else:
                v = 0
            frames += struct.pack("<h", v)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))


@pytest.fixture(scope="session")
def media_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("media")
    write_wav(d / "tone_gap.wav", [("tone", 1), ("silence", 3), ("tone", 1)])
    write_wav(d / "sync_ref.wav", [("noise", 4)])
    write_wav(d / "sync_shifted.wav", [("silence", 1.5), ("noise", 4)])
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", "testsrc=duration=6:size=320x240:rate=30",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(d / "clip.mp4")],
        check=True)
    return d
```

- [ ] **Step 2: Падающий тест probe**

`skills/rough-cut/tests/test_probe.py`:

```python
import probe


def test_probe_video(media_dir):
    info = probe.probe(media_dir / "clip.mp4")
    assert info["has_video"] and info["has_audio"]
    assert info["fps"] == {"num": 30, "den": 1}
    assert info["width"] == 320 and info["height"] == 240
    assert abs(info["duration_s"] - 6.0) < 0.5


def test_probe_audio_only(media_dir):
    info = probe.probe(media_dir / "tone_gap.wav")
    assert info["has_audio"] and not info["has_video"]
    assert abs(info["duration_s"] - 5.0) < 0.1
```

Run: `cd /Users/wolkart/AI/aifuture_hub/skills/rough-cut && uv run --with pytest --with numpy --with scipy python -m pytest tests/test_probe.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'probe'`

- [ ] **Step 3: Реализация**

`skills/rough-cut/scripts/probe.py`:

```python
#!/usr/bin/env python3
"""ffprobe → компактный JSON о медиафайле. Только stdlib."""
import argparse
import json
import subprocess
from fractions import Fraction


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    info = {"path": str(path),
            "duration_s": float(data["format"]["duration"]),
            "has_video": False, "has_audio": False}
    for st in data["streams"]:
        if st["codec_type"] == "video" and not info["has_video"]:
            fr = Fraction(st["r_frame_rate"])
            info.update(has_video=True,
                        fps={"num": fr.numerator, "den": fr.denominator},
                        width=st["width"], height=st["height"])
        elif st["codec_type"] == "audio":
            info["has_audio"] = True
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    print(json.dumps([probe(f) for f in args.files], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Тесты зелёные**

Run: полный прогон `uv run --with pytest --with numpy --with scipy python -m pytest tests -v`
Expected: все passed (включая Task 1).

- [ ] **Step 5: Commit**

```bash
git add skills/rough-cut && git commit -m "rough-cut: probe (ffprobe → JSON) + тестовые фикстуры (wav-генератор, testsrc-клип)"
```

---

### Task 3: `detect_silence.py`

**Files:**
- Create: `skills/rough-cut/scripts/detect_silence.py`
- Test: `skills/rough-cut/tests/test_detect_silence.py`

**Interfaces:**
- Produces: `detect(path, noise_db=-35.0, min_dur=0.8) -> [{"start", "end"}]` (сырые интервалы тишины); `to_cuts(intervals, pad=0.15, min_cut=0.4) -> [{"start", "end"}]` (интервалы под вырезание: паддинг внутрь, короткие отброшены). CLI: `detect_silence.py AUDIO [--noise-db -35] [--min-dur 0.8] [--pad 0.15] --json` → `{"silences": [...], "cuts": [...]}`.

- [ ] **Step 1: Падающий тест**

`skills/rough-cut/tests/test_detect_silence.py`:

```python
import detect_silence


def test_detect_finds_gap(media_dir):
    ivs = detect_silence.detect(media_dir / "tone_gap.wav")
    assert len(ivs) == 1
    assert abs(ivs[0]["start"] - 1.0) < 0.3
    assert abs(ivs[0]["end"] - 4.0) < 0.3


def test_to_cuts_pads_inward():
    cuts = detect_silence.to_cuts([{"start": 1.0, "end": 4.0}], pad=0.15)
    assert cuts == [{"start": 1.15, "end": 3.85}]


def test_to_cuts_drops_short():
    assert detect_silence.to_cuts([{"start": 1.0, "end": 1.5}], pad=0.15,
                                  min_cut=0.4) == []
```

Run: `uv run --with pytest --with numpy --with scipy python -m pytest tests/test_detect_silence.py -v`
Expected: FAIL — модуль не существует.

- [ ] **Step 2: Реализация**

`skills/rough-cut/scripts/detect_silence.py`:

```python
#!/usr/bin/env python3
"""Интервалы тишины через ffmpeg silencedetect. Только stdlib."""
import argparse
import json
import re
import subprocess


def detect(path, noise_db=-35.0, min_dur=0.8):
    p = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path),
         "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}",
         "-f", "null", "-"],
        capture_output=True, text=True)
    starts = [float(m) for m in re.findall(r"silence_start: (-?[\d.]+)", p.stderr)]
    ends = [float(m) for m in re.findall(r"silence_end: (-?[\d.]+)", p.stderr)]
    return [{"start": max(0.0, round(s, 3)), "end": round(e, 3)}
            for s, e in zip(starts, ends)]


def to_cuts(intervals, pad=0.15, min_cut=0.4):
    """Паддинг внутрь (дыхание вокруг речи), слишком короткое не режем."""
    cuts = []
    for iv in intervals:
        s, e = iv["start"] + pad, iv["end"] - pad
        if e - s >= min_cut:
            cuts.append({"start": round(s, 3), "end": round(e, 3)})
    return cuts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("audio")
    ap.add_argument("--noise-db", type=float, default=-35.0)
    ap.add_argument("--min-dur", type=float, default=0.8)
    ap.add_argument("--pad", type=float, default=0.15)
    ap.add_argument("--min-cut", type=float, default=0.4)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    silences = detect(args.audio, args.noise_db, args.min_dur)
    print(json.dumps(
        {"silences": silences,
         "cuts": to_cuts(silences, args.pad, args.min_cut)},
        ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Тесты зелёные**

Run: полный прогон. Expected: все passed. Если детект на фикстуре даёт границы за пределами допуска 0.3 — крутить только допуск теста НЕЛЬЗЯ; проверить параметры silencedetect (уровень тона фикстуры −8 дБ, порог −35 дБ должен срабатывать чётко).

- [ ] **Step 4: Commit**

```bash
git add skills/rough-cut && git commit -m "rough-cut: detect_silence (ffmpeg silencedetect → интервалы + паддинг под резку)"
```

---

### Task 4: `sync_offset.py`

**Files:**
- Create: `skills/rough-cut/scripts/sync_offset.py`
- Test: `skills/rough-cut/tests/test_sync_offset.py`

**Interfaces:**
- Consumes: фикстуры `sync_ref.wav` / `sync_shifted.wav`.
- Produces: `find_offset(ref: np.ndarray, target: np.ndarray, sr) -> (offset_s: float, confidence: float)`; `extract_pcm(path, sr=8000, max_seconds=600) -> np.ndarray`. Семантика: `target[t + offset_s] ≈ ref[t]`, т.е. **ref = звук видео, target = чистый звук OBS, audio_time = video_time + offset_s**. CLI: `uv run sync_offset.py --ref video.mp4 --target audio.wav` → `{"offset_s": ..., "confidence": ...}`. Confidence — нормированный коэффициент корреляции в пике, 0..1; порог тревоги < 0.2 (задокументировать в docstring).

- [ ] **Step 1: Падающий тест**

`skills/rough-cut/tests/test_sync_offset.py`:

```python
import sync_offset


def test_offset_found(media_dir):
    ref = sync_offset.extract_pcm(media_dir / "sync_ref.wav")
    target = sync_offset.extract_pcm(media_dir / "sync_shifted.wav")
    off, conf = sync_offset.find_offset(ref, target)
    assert abs(off - 1.5) < 0.05
    assert conf > 0.5


def test_offset_zero_for_identical(media_dir):
    ref = sync_offset.extract_pcm(media_dir / "sync_ref.wav")
    off, conf = sync_offset.find_offset(ref, ref)
    assert abs(off) < 0.01
    assert conf > 0.9
```

Run: `uv run --with pytest --with numpy --with scipy python -m pytest tests/test_sync_offset.py -v`
Expected: FAIL — модуль не существует.

- [ ] **Step 2: Реализация**

`skills/rough-cut/scripts/sync_offset.py`:

```python
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
```

- [ ] **Step 3: Тесты зелёные**

Run: полный прогон. Expected: все passed.

- [ ] **Step 4: Проверить самодостаточность через uv**

Run: `cd /Users/wolkart/AI/aifuture_hub/skills/rough-cut && uv run scripts/sync_offset.py --help`
Expected: uv сам ставит numpy/scipy (PEP 723), печатается help без ошибок.

- [ ] **Step 5: Commit**

```bash
git add skills/rough-cut && git commit -m "rough-cut: sync_offset (кросс-корреляция звука камеры и OBS → смещение + confidence)"
```

---

### Task 5: `transcribe.py` (абстракция whisper-бэкенда)

**Files:**
- Create: `skills/rough-cut/scripts/transcribe.py`
- Test: `skills/rough-cut/tests/test_transcribe.py`

**Interfaces:**
- Consumes: `check_env.whisper_backend()` — та же логика выбора (дублируем локально, скрипт самодостаточен).
- Produces: CLI `python3 scripts/transcribe.py AUDIO [--backend auto|mlx|faster] [--model NAME]` → `{"text": str, "words": [{"word": str, "start": float, "end": float}]}` в stdout (файл `<AUDIO>.words.json` рядом — тоже пишется). Функции: `pick_backend(plat, machine, override="auto") -> "mlx"|"faster"`, `normalize_mlx(result) -> dict`, `normalize_faster(segments) -> dict`.
- Механика запуска: скрипт без зависимостей в PEP 723; при запуске сам перезапускает себя через `uv run --with <mlx-whisper|faster-whisper>` (флаг `--_direct` останавливает рекурсию). Реальная транскрипция в тестах НЕ гоняется (модель ~1.5 ГБ) — тестируются выбор бэкенда и нормализация.

- [ ] **Step 1: Падающий тест**

`skills/rough-cut/tests/test_transcribe.py`:

```python
import transcribe


def test_pick_backend():
    assert transcribe.pick_backend("darwin", "arm64") == "mlx"
    assert transcribe.pick_backend("darwin", "x86_64") == "faster"
    assert transcribe.pick_backend("linux", "x86_64") == "faster"
    assert transcribe.pick_backend("linux", "x86_64", override="mlx") == "mlx"


def test_normalize_mlx():
    raw = {"text": " привет мир",
           "segments": [{"words": [
               {"word": " привет", "start": 0.1, "end": 0.5},
               {"word": " мир", "start": 0.6, "end": 0.9}]}]}
    out = transcribe.normalize_mlx(raw)
    assert out["words"] == [{"word": "привет", "start": 0.1, "end": 0.5},
                            {"word": "мир", "start": 0.6, "end": 0.9}]


def test_normalize_faster():
    class W:
        def __init__(self, word, start, end):
            self.word, self.start, self.end = word, start, end

    class S:
        def __init__(self, text, words):
            self.text, self.words = text, words

    segs = [S(" привет мир", [W(" привет", 0.1, 0.5), W(" мир", 0.6, 0.9)])]
    out = transcribe.normalize_faster(segs)
    assert out["text"] == "привет мир"
    assert out["words"][1] == {"word": "мир", "start": 0.6, "end": 0.9}
```

Run: `uv run --with pytest --with numpy --with scipy python -m pytest tests/test_transcribe.py -v`
Expected: FAIL — модуль не существует.

- [ ] **Step 2: Реализация**

`skills/rough-cut/scripts/transcribe.py`:

```python
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
    if not args._direct:
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
```

Примечание: `args._direct` — argparse кладёт `--_direct` в атрибут `_direct`; проверить обращением `getattr(args, "_direct")` если линтер ругается — использовать `getattr`.

- [ ] **Step 3: Тесты зелёные**

Run: полный прогон. Expected: все passed.

- [ ] **Step 4: Commit**

```bash
git add skills/rough-cut && git commit -m "rough-cut: transcribe (пословный транскрипт, авто-выбор mlx/faster-whisper, самоперезапуск через uv)"
```

---

### Task 6: `extract_frames.py`

**Files:**
- Create: `skills/rough-cut/scripts/extract_frames.py`
- Test: `skills/rough-cut/tests/test_extract_frames.py`

**Interfaces:**
- Produces: `frame_times(start, end, edge=0.2) -> [float]` (1 кадр для коротких, 3 — начало/середина/конец); `extract(video, intervals, out_dir) -> [{"interval": {...}, "frames": [paths]}]`. CLI: `extract_frames.py VIDEO --intervals '[{"start":1,"end":5}]' --out-dir DIR` → JSON. Используется ТОЛЬКО в полном профиле (скринкаст).

- [ ] **Step 1: Падающий тест**

`skills/rough-cut/tests/test_extract_frames.py`:

```python
from pathlib import Path

import extract_frames


def test_frame_times_three_for_long():
    assert extract_frames.frame_times(1.0, 5.0) == [1.2, 3.0, 4.8]


def test_frame_times_one_for_short():
    assert extract_frames.frame_times(1.0, 1.3) == [1.15]


def test_extract_writes_frames(media_dir, tmp_path):
    res = extract_frames.extract(media_dir / "clip.mp4",
                                 [{"start": 1.0, "end": 5.0}], tmp_path)
    assert len(res) == 1
    assert len(res[0]["frames"]) == 3
    for p in res[0]["frames"]:
        assert Path(p).stat().st_size > 0
```

Run: `uv run --with pytest --with numpy --with scipy python -m pytest tests/test_extract_frames.py -v`
Expected: FAIL — модуль не существует.

- [ ] **Step 2: Реализация**

`skills/rough-cut/scripts/extract_frames.py`:

```python
#!/usr/bin/env python3
"""Кадры из тихих участков скринкаста (начало/середина/конец). Только stdlib."""
import argparse
import json
import subprocess
from pathlib import Path


def frame_times(start, end, edge=0.2):
    if end - start <= 2 * edge:
        return [round((start + end) / 2, 3)]
    return [round(start + edge, 3), round((start + end) / 2, 3),
            round(end - edge, 3)]


def extract(video, intervals, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = []
    for i, iv in enumerate(intervals):
        frames = []
        for t in frame_times(iv["start"], iv["end"]):
            p = out_dir / f"gap{i:03d}_t{t:07.2f}.png"
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-ss", str(t),
                 "-i", str(video), "-frames:v", "1", str(p)], check=True)
            frames.append(str(p))
        result.append({"interval": iv, "frames": frames})
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video")
    ap.add_argument("--intervals", required=True, help="JSON: [{start,end},...]")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    res = extract(args.video, json.loads(args.intervals), args.out_dir)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Тесты зелёные**

Run: полный прогон. Expected: все passed.

- [ ] **Step 4: Commit**

```bash
git add skills/rough-cut && git commit -m "rough-cut: extract_frames (кадры тихих участков для визуальных решений по скринкасту)"
```

---

### Task 7: `cutlist.py` (схема, валидация, тайлинг)

**Files:**
- Create: `skills/rough-cut/scripts/cutlist.py`
- Test: `skills/rough-cut/tests/test_cutlist.py`

**Interfaces:**
- Produces (схема cut-list v1, канон для экспортёров):

```json
{
  "version": 1,
  "profile": "light",
  "scenario": "camera_plus_audio",
  "inputs": {"video": "cam.mp4", "audio": "obs.wav", "video2": null},
  "sync": {"offset_s": 1.5, "confidence": 0.92},
  "fps": {"num": 30, "den": 1},
  "width": 1920, "height": 1080,
  "duration_s": 812.4,
  "segments": [
    {"start": 0.0, "end": 12.4, "action": "keep"},
    {"start": 12.4, "end": 16.1, "action": "cut", "source": "silence",
     "reason": "тишина 3.7с", "confidence": 0.95},
    {"start": 16.1, "end": 100.0, "action": "keep"},
    {"start": 100.0, "end": 130.0, "action": "speedup", "rate": 8,
     "source": "screencast", "reason": "идёт загрузка", "confidence": 0.7},
    {"start": 130.0, "end": 812.4, "action": "keep"}
  ]
}
```

- Правила: `scenario ∈ {camera_plus_audio, screencast, multicam}`; `profile ∈ {light, full}`; сегменты сортированы, покрывают `[0, duration_s]` сплошным тайлингом (допуск стыков/краёв 0.02с), не пересекаются; `action ∈ {keep, cut, speedup}`; для `speedup` обязателен `rate > 1`; для `cut`/`speedup` обязателен `source ∈ {silence, filler, retake, screencast, user}`. Времена — координаты основного видео.
- Функции: `validate(d)` (ValueError с внятным русским сообщением), `load(path)` (json + validate), `timeline(d) -> [seg]` (keep+speedup по порядку — то, что попадает на таймлайн), `from_cuts(meta, cut_segments) -> dict` (строит полный тайлинг: дыры между cut/speedup заполняются keep).

- [ ] **Step 1: Падающий тест**

`skills/rough-cut/tests/test_cutlist.py`:

```python
import pytest

import cutlist


def make_meta():
    return {"profile": "light", "scenario": "camera_plus_audio",
            "inputs": {"video": "cam.mp4", "audio": "obs.wav", "video2": None},
            "sync": {"offset_s": 1.5, "confidence": 0.9},
            "fps": {"num": 30, "den": 1}, "width": 1920, "height": 1080,
            "duration_s": 10.0}


def test_from_cuts_tiles_full_duration():
    d = cutlist.from_cuts(make_meta(), [
        {"start": 2.0, "end": 4.0, "action": "cut", "source": "silence",
         "reason": "тишина", "confidence": 0.95}])
    acts = [(s["start"], s["end"], s["action"]) for s in d["segments"]]
    assert acts == [(0.0, 2.0, "keep"), (2.0, 4.0, "cut"), (4.0, 10.0, "keep")]
    cutlist.validate(d)  # не бросает


def test_validate_rejects_overlap():
    d = cutlist.from_cuts(make_meta(), [])
    d["segments"] = [{"start": 0.0, "end": 6.0, "action": "keep"},
                     {"start": 5.0, "end": 10.0, "action": "keep"}]
    with pytest.raises(ValueError):
        cutlist.validate(d)


def test_validate_rejects_gap():
    d = cutlist.from_cuts(make_meta(), [])
    d["segments"] = [{"start": 0.0, "end": 4.0, "action": "keep"},
                     {"start": 6.0, "end": 10.0, "action": "keep"}]
    with pytest.raises(ValueError):
        cutlist.validate(d)


def test_validate_requires_rate_for_speedup():
    d = cutlist.from_cuts(make_meta(), [])
    d["segments"] = [{"start": 0.0, "end": 10.0, "action": "speedup",
                      "source": "screencast", "reason": "x", "confidence": 1}]
    with pytest.raises(ValueError):
        cutlist.validate(d)


def test_timeline_skips_cuts():
    d = cutlist.from_cuts(make_meta(), [
        {"start": 2.0, "end": 4.0, "action": "cut", "source": "silence",
         "reason": "тишина", "confidence": 0.95}])
    assert [s["start"] for s in cutlist.timeline(d)] == [0.0, 4.0]
```

Run: `uv run --with pytest --with numpy --with scipy python -m pytest tests/test_cutlist.py -v`
Expected: FAIL — модуль не существует.

- [ ] **Step 2: Реализация**

`skills/rough-cut/scripts/cutlist.py`:

```python
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
```

- [ ] **Step 3: Тесты зелёные**

Run: полный прогон. Expected: все passed.

- [ ] **Step 4: Commit**

```bash
git add skills/rough-cut && git commit -m "rough-cut: cutlist (схема v1, валидация тайлинга, сборка из резов)"
```

---

### Task 8: `export_fcpxml.py`

**Files:**
- Create: `skills/rough-cut/scripts/export_fcpxml.py`
- Test: `skills/rough-cut/tests/test_export_fcpxml.py`

**Interfaces:**
- Consumes: `cutlist.load(path)`, `cutlist.timeline(d)`.
- Produces: `rt(seconds, num, den) -> str` (рациональное время, выровненное по кадру: `"{frames*den}/{num}s"`); `build(d) -> xml.etree.ElementTree.Element`; CLI: `export_fcpxml.py CUTLIST.json [-o OUT.fcpxml]` (дефолт: рядом с cut-list, та же основа имени). Решения: speedup-сегменты кладутся как обычные клипы **с маркером** `SPEEDUP ×N (rough-cut)` — ретайм пользователь делает в Resolve сам (импорт timeMap ненадёжен); отдельный звук — connected clip `lane="-1"` со сдвигом `sync.offset_s`; мультикам (`inputs.video2`) — connected clip `lane="1"` с теми же резами.

- [ ] **Step 1: Падающий тест**

`skills/rough-cut/tests/test_export_fcpxml.py`:

```python
import xml.etree.ElementTree as ET

import cutlist
import export_fcpxml


def make_cutlist():
    meta = {"profile": "full", "scenario": "camera_plus_audio",
            "inputs": {"video": "cam.mp4", "audio": "obs.wav", "video2": None},
            "sync": {"offset_s": 1.5, "confidence": 0.9},
            "fps": {"num": 30, "den": 1}, "width": 1920, "height": 1080,
            "duration_s": 10.0}
    return cutlist.from_cuts(meta, [
        {"start": 2.0, "end": 4.0, "action": "cut", "source": "silence",
         "reason": "тишина", "confidence": 0.95},
        {"start": 6.0, "end": 8.0, "action": "speedup", "rate": 8,
         "source": "screencast", "reason": "загрузка", "confidence": 0.7}])


def test_rt_frame_aligned():
    assert export_fcpxml.rt(1.0, 30, 1) == "30/30s"
    assert export_fcpxml.rt(0.5, 30000, 1001) == "15015/30000s"  # 15 кадров NTSC


def test_build_valid_xml():
    root = export_fcpxml.build(make_cutlist())
    assert root.tag == "fcpxml" and root.get("version") == "1.9"
    # спорное место — перечитываем сериализацию
    ET.fromstring(ET.tostring(root))


def test_spine_clips_match_timeline():
    root = export_fcpxml.build(make_cutlist())
    spine = root.find(".//spine")
    clips = spine.findall("asset-clip")
    assert len(clips) == 3  # keep, keep, speedup (cut выброшен)


def test_speedup_gets_marker():
    root = export_fcpxml.build(make_cutlist())
    markers = root.findall(".//asset-clip/marker")
    assert len(markers) == 1
    assert "SPEEDUP ×8" in markers[0].get("value")


def test_audio_connected_with_offset():
    root = export_fcpxml.build(make_cutlist())
    laned = [c for c in root.findall(".//asset-clip/asset-clip")
             if c.get("lane") == "-1"]
    assert len(laned) == 3  # звук приклеен к каждому клипу таймлайна
```

Run: `uv run --with pytest --with numpy --with scipy python -m pytest tests/test_export_fcpxml.py -v`
Expected: FAIL — модуль не существует.

- [ ] **Step 2: Реализация**

`skills/rough-cut/scripts/export_fcpxml.py`:

```python
#!/usr/bin/env python3
"""cut-list → FCPXML 1.9 (импорт в DaVinci Resolve). Только stdlib.

Резы «мягкие»: клипы ссылаются на исходники, границы двигаются в Resolve.
speedup — обычный клип + маркер SPEEDUP ×N (ретайм руками: импорт timeMap
в Resolve ненадёжен). Отдельный звук — connected clip lane=-1 со сдвигом
sync.offset_s. Мультикам (inputs.video2) — connected clip lane=1.
"""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import cutlist


def rt(seconds, num, den):
    """Секунды → рациональное время FCPXML, выровненное по границе кадра."""
    frames = round(seconds * num / den)
    return f"{frames * den}/{num}s"


def build(d):
    num, den = d["fps"]["num"], d["fps"]["den"]
    fx = ET.Element("fcpxml", version="1.9")
    res = ET.SubElement(fx, "resources")
    ET.SubElement(res, "format", id="r1", frameDuration=f"{den}/{num}s",
                  width=str(d["width"]), height=str(d["height"]))
    total = rt(d["duration_s"], num, den)
    ET.SubElement(res, "asset", id="r2",
                  src=Path(d["inputs"]["video"]).resolve().as_uri(),
                  hasVideo="1", hasAudio="1", format="r1",
                  start="0s", duration=total)
    audio = d["inputs"].get("audio")
    if audio:
        ET.SubElement(res, "asset", id="r3",
                      src=Path(audio).resolve().as_uri(),
                      hasAudio="1", start="0s", duration=total)
    video2 = d["inputs"].get("video2")
    if video2:
        ET.SubElement(res, "asset", id="r4",
                      src=Path(video2).resolve().as_uri(),
                      hasVideo="1", format="r1", start="0s", duration=total)

    seq = ET.SubElement(
        ET.SubElement(
            ET.SubElement(
                ET.SubElement(ET.SubElement(fx, "library"), "event",
                              name="rough-cut"),
                "project", name="rough-cut"),
            "sequence", format="r1"),
        "spine")

    off_s = d.get("sync", {}).get("offset_s", 0.0)
    tl = 0.0
    for seg in cutlist.timeline(d):
        dur = seg["end"] - seg["start"]
        clip = ET.SubElement(seq, "asset-clip", ref="r2", name="rough-cut",
                             offset=rt(tl, num, den),
                             start=rt(seg["start"], num, den),
                             duration=rt(dur, num, den))
        if seg["action"] == "speedup":
            ET.SubElement(clip, "marker", start=rt(seg["start"], num, den),
                          duration=rt(min(dur, 1.0), num, den),
                          value=f"SPEEDUP ×{seg['rate']} (rough-cut): "
                                f"{seg.get('reason', '')}")
        if audio:
            ET.SubElement(clip, "asset-clip", ref="r3", lane="-1",
                          offset=rt(seg["start"], num, den),
                          start=rt(seg["start"] + off_s, num, den),
                          duration=rt(dur, num, den))
        if video2:
            ET.SubElement(clip, "asset-clip", ref="r4", lane="1",
                          offset=rt(seg["start"], num, den),
                          start=rt(seg["start"], num, den),
                          duration=rt(dur, num, den))
        tl += dur
    return fx


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cutlist_path")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    d = cutlist.load(args.cutlist_path)
    out = Path(args.out or Path(args.cutlist_path).with_suffix(".fcpxml"))
    tree = ET.ElementTree(build(d))
    ET.indent(tree)
    tree.write(out, encoding="utf-8", xml_declaration=True)
    doctype_body = out.read_text(encoding="utf-8").split("\n", 1)
    out.write_text(doctype_body[0] + "\n<!DOCTYPE fcpxml>\n" + doctype_body[1],
                   encoding="utf-8")
    print(f"FCPXML: {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Тесты зелёные**

Run: полный прогон. Expected: все passed.

- [ ] **Step 4: Ручная проверка в Resolve (разово, вне тестов)**

Сгенерировать FCPXML из фикстурного cut-list на реальном `clip.mp4` и импортировать в DaVinci Resolve (`File → Import → Timeline`). Ожидается: таймлайн с 3 клипами, звук на lane ниже, маркер на speedup-клипе. Если Resolve ругается на схему — зафиксировать точную ошибку в `references/fcpxml-notes.md` и поправить экспортёр (частые причины: отсутствие DOCTYPE, `start` вне диапазона asset). Это единственный шаг с ручной проверкой — автоматизировать импорт в Resolve нельзя.

- [ ] **Step 5: Commit**

```bash
git add skills/rough-cut && git commit -m "rough-cut: export_fcpxml (cut-list → FCPXML 1.9: мягкие резы, connected-звук со сдвигом, маркеры SPEEDUP, мультикам lane=1)"
```

---

### Task 9: `render.py` + сквозной e2e-тест

**Files:**
- Create: `skills/rough-cut/scripts/render.py`
- Test: `skills/rough-cut/tests/test_render.py`

**Interfaces:**
- Consumes: `cutlist.load/timeline`.
- Produces: `build_cmd(d, out_path) -> [str]` (полная команда ffmpeg); CLI `render.py CUTLIST.json [-o OUT.mp4] [--force]`. Правила: `keep` — trim видео + atrim звука (со сдвигом `offset_s`; если отдельного звука нет — звук из видео); `speedup` — `setpts/(rate)`, звук заменяется тишиной той же (ускоренной) длительности; конкат всех сегментов; выход H.264+AAC. Стражи: отказ, если `out` совпадает с любым входом; отказ, если `out` существует и нет `--force`. Дефолт выхода: `<видео-стем>.roughcut.mp4`.

- [ ] **Step 1: Падающий тест**

`skills/rough-cut/tests/test_render.py`:

```python
import subprocess

import pytest

import cutlist
import probe
import render


def make_cutlist(media_dir, cuts):
    info = probe.probe(media_dir / "clip.mp4")
    meta = {"profile": "light", "scenario": "screencast",
            "inputs": {"video": str(media_dir / "clip.mp4"),
                       "audio": None, "video2": None},
            "sync": {"offset_s": 0.0, "confidence": 1.0},
            "fps": info["fps"], "width": info["width"],
            "height": info["height"],
            "duration_s": round(info["duration_s"], 3)}
    return cutlist.from_cuts(meta, cuts)


def test_render_cuts_duration(media_dir, tmp_path):
    d = make_cutlist(media_dir, [
        {"start": 2.0, "end": 4.0, "action": "cut", "source": "silence",
         "reason": "тишина", "confidence": 0.95}])
    out = tmp_path / "out.mp4"
    subprocess.run(render.build_cmd(d, out), check=True)
    assert abs(probe.probe(out)["duration_s"] - 4.0) < 0.3


def test_render_speedup_shrinks(media_dir, tmp_path):
    d = make_cutlist(media_dir, [
        {"start": 2.0, "end": 6.0, "action": "speedup", "rate": 4,
         "source": "screencast", "reason": "загрузка", "confidence": 0.8}])
    out = tmp_path / "out.mp4"
    subprocess.run(render.build_cmd(d, out), check=True)
    # 2с как есть + 4с/4 = 3с
    assert abs(probe.probe(out)["duration_s"] - 3.0) < 0.3


def test_render_refuses_overwrite_input(media_dir):
    d = make_cutlist(media_dir, [])
    with pytest.raises(ValueError):
        render.build_cmd(d, media_dir / "clip.mp4")
```

Run: `uv run --with pytest --with numpy --with scipy python -m pytest tests/test_render.py -v`
Expected: FAIL — модуль не существует.

- [ ] **Step 2: Реализация**

`skills/rough-cut/scripts/render.py`:

```python
#!/usr/bin/env python3
"""cut-list → готовый mp4 (H.264+AAC) через ffmpeg. Только stdlib.

Исходники не перезаписываются никогда: выход не может совпадать со входом,
существующий файл — только с --force. speedup: видео ускоряется, звук на
этом участке — тишина (у таймлапса нет осмысленного звука).
"""
import argparse
import subprocess
from pathlib import Path

import cutlist


def build_cmd(d, out_path):
    video = d["inputs"]["video"]
    audio = d["inputs"].get("audio")
    out_path = Path(out_path)
    inputs_paths = {Path(video).resolve()} | (
        {Path(audio).resolve()} if audio else set())
    if out_path.resolve() in inputs_paths:
        raise ValueError("render: выход совпадает со входом — исходники "
                         "не перезаписываются")
    off = d.get("sync", {}).get("offset_s", 0.0) if audio else 0.0
    a_in = "1:a" if audio else "0:a"
    parts, pairs, n = [], [], 0
    for seg in cutlist.timeline(d):
        s, e = seg["start"], seg["end"]
        if seg["action"] == "keep":
            parts.append(f"[0:v]trim=start={s}:end={e},"
                         f"setpts=PTS-STARTPTS[v{n}]")
            parts.append(f"[{a_in}]atrim=start={s + off}:end={e + off},"
                         f"asetpts=PTS-STARTPTS[a{n}]")
        else:  # speedup
            rate = seg["rate"]
            parts.append(f"[0:v]trim=start={s}:end={e},"
                         f"setpts=(PTS-STARTPTS)/{rate}[v{n}]")
            parts.append(f"aevalsrc=0:d={(e - s) / rate}:s=48000[a{n}]")
        pairs.append(f"[v{n}][a{n}]")
        n += 1
    fc = (";".join(parts) + ";" + "".join(pairs)
          + f"concat=n={n}:v=1:a=1[vo][ao]")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(video)]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-filter_complex", fc, "-map", "[vo]", "-map", "[ao]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", str(out_path)]
    return cmd


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cutlist_path")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    d = cutlist.load(args.cutlist_path)
    out = Path(args.out or
               Path(d["inputs"]["video"]).with_suffix("")).with_name(
        Path(args.out or d["inputs"]["video"]).stem + ".roughcut.mp4") \
        if args.out is None else Path(args.out)
    if out.exists() and not args.force:
        raise SystemExit(f"render: {out} уже существует (перезапись — --force)")
    subprocess.run(build_cmd(d, out), check=True)
    print(f"Рендер: {out}")


if __name__ == "__main__":
    main()
```

Примечание: выражение для дефолтного `out` в `main()` громоздкое — допустимо упростить до:

```python
    if args.out:
        out = Path(args.out)
    else:
        v = Path(d["inputs"]["video"])
        out = v.with_name(v.stem + ".roughcut.mp4")
```

Использовать простой вариант.

- [ ] **Step 3: Тесты зелёные (весь набор — это и есть e2e: probe → cutlist → render)**

Run: `uv run --with pytest --with numpy --with scipy python -m pytest tests -v`
Expected: все passed.

- [ ] **Step 4: Commit**

```bash
git add skills/rough-cut && git commit -m "rough-cut: render (cut-list → mp4: конкат keep-кусков, таймлапс с тишиной, стражи от перезаписи)"
```

---

### Task 10: SKILL.md + references + README + витрина + evals

**Files:**
- Create: `skills/rough-cut/SKILL.md`
- Create: `skills/rough-cut/references/thresholds.md`
- Create: `skills/rough-cut/references/decide-rules.md`
- Create: `skills/rough-cut/references/fcpxml-notes.md`
- Create: `skills/rough-cut/README.md`
- Create: `skills/rough-cut/evals/evals.json`
- Modify: `skills/README.md` (добавить строку в таблицу-витрину)

**Interfaces:**
- Consumes: все CLI из задач 1–9 (точные вызовы — в тексте SKILL.md).
- Produces: полный публичный скилл.

- [ ] **Step 1: SKILL.md**

Frontmatter (стиль хаба, триггер в description):

```markdown
---
name: rough-cut
description: >-
  Черновой монтаж записей: синхронизирует отдельно записанный звук (OBS) с
  видео камеры по звуковой волне, вырезает тишину, филлеры («э-э», «пык-мык»),
  заикания и запоротые дубли; для скринкастов смотрит кадры тихих участков и
  решает — вырезать, оставить или таймлапс. Используй этот скилл всегда, когда
  пользователь хочет «обработай запись», «порежь тишину», «синхронизируй звук
  и видео», «убери заикания/дубли», «сделай черновой монтаж», «подготовь
  запись к монтажу». Выход: cut-list JSON → FCPXML-таймлайн для DaVinci
  Resolve и/или готовый mp4 (CapCut, рилсы, веб). НЕ пишет сценарии
  (reels-script) и НЕ качает чужие видео (instagram-downloader).
---
```

Тело SKILL.md — разделы (компактно, вся логика уже в скриптах):

1. **Роль**: монтажёр черновой сборки; последнее слово за пользователем.
2. **Шаг 0 — доктор**: всегда первым `python3 scripts/check_env.py --json`; если `missing` непуст — показать команды и размеры, ставить только после согласия; без whisper предложить режим «только тишина».
3. **Определение сценария и профиля**: по входным файлам (видео+отдельный звук → `camera_plus_audio`; один файл экран+звук → `screencast`; два видео + звук → `multicam`). Профиль: `light` по умолчанию для camera_plus_audio; для скринкаста — если пользователь не сказал, задать ОДИН вопрос: «смотреть на экран для таймлапсов (полный) или просто порезать по звуку (лёгкий)?»
4. **Пайплайн** — точные команды по стадиям:
   - `uv run scripts/probe.py <файлы> --json`
   - `uv run scripts/sync_offset.py --ref <видео> --target <звук>` (только при отдельном звуке; при confidence < 0.2 — честно сказать и спросить хлопок/ручное смещение)
   - `uv run scripts/detect_silence.py <чистый звук> --json`
   - `python3 scripts/transcribe.py <чистый звук>` (кроме режима «только тишина»)
   - стадия Decide (сам Claude, правила — `references/decide-rules.md`): из транскрипта — филлеры/заикания/дубли; для профиля full — `uv run scripts/extract_frames.py ...` и решения по кадрам
   - собрать cut-list (схема — docstring `scripts/cutlist.py`; тайлинг строит `cutlist.from_cuts`), сохранить `<видео-стем>.cutlist.json` РЯДОМ с исходниками
5. **Отчёт**: таблица «таймкод | длительность | что нашёл | решение | уверенность», спорные строки помечены ⚠; дождаться правок пользователя («в 02:15 верни» = правка cut-list, анализ не перегонять).
6. **Экспорт** (по выбору пользователя): `uv run scripts/export_fcpxml.py <cutlist>` и/или `uv run scripts/render.py <cutlist>`.
7. **Стражи**: исходники не перезаписывать; ничего не ставить без согласия; при неуверенности — помечать, а не резать молча.

- [ ] **Step 2: references**

`references/thresholds.md` — дефолты и когда крутить: `noise_db` −35 (шумный фон → −30), `min_dur` 0.8 (быстрая речь → 0.5–0.6), `pad` 0.15, `min_cut` 0.4; порог confidence синхрона 0.2; edge кадров 0.2.

`references/decide-rules.md` — правила стадии Decide:
- **Филлеры**: слова-паразиты и звуки («э-э», «м-м», «ну это», обрывки) — cut c `source: filler`; окно реза — по таймкодам слов ± 0.05с.
- **Дубли**: фраза оборвана + следующая начинается лексически похоже (≥60% общих первых слов) → вырезать ВСЕ варианты кроме последнего завершённого, `source: retake`; если непонятно, какой дубль финальный — пометить `confidence ≤ 0.5` и НЕ резать, отдать пользователю.
- **Скринкаст-тишина** (по 3 кадрам gap-а): кадры идентичны на глаз → `cut`; видна прогрессия (загрузка, скролл, ввод) → `speedup` (rate: 4 для <30с, 8 для длиннее); пауза < 2.5с после осмысленного действия → `keep`.
- Всегда: `reason` — по-русски, коротко, конкретно; `confidence` честный.

`references/fcpxml-notes.md` — что генерим (FCPXML 1.9, DOCTYPE, frame-aligned rational times, connected lanes, маркеры SPEEDUP), известные грабли импорта в Resolve + сюда же записывать результаты ручной проверки из Task 8 Step 4.

- [ ] **Step 3: README.md скилла**

Разделы: что делает (3 предложения), **Требования** (ffmpeg, uv; whisper-модель ~1.5 ГБ разово; всё локально, ничего не уходит в сеть), примеры вызова («обработай запись: видео …, звук …»), сценарии/профили, формат выхода, «Под себя» (пороги в references/thresholds.md).

- [ ] **Step 4: evals/evals.json**

```json
{
  "skill_name": "rough-cut",
  "evals": [
    {
      "id": 1,
      "prompt": "обработай запись: видео ~/rec/cam.mp4, звук ~/rec/obs.wav — порежь тишину и заикания",
      "expected_output": "Активируется rough-cut: доктор → probe → синхрон по волне → тишина+транскрипт → отчёт-таблица решений; профиль light (кадры не извлекаются), спорное помечено",
      "files": []
    },
    {
      "id": 2,
      "prompt": "вот скринкаст ~/rec/screen.mp4 — почисти, но там есть места, где идёт загрузка, их хочу таймлапсом",
      "expected_output": "Сценарий screencast: уточняет/принимает профиль full, извлекает кадры тихих участков, решает cut/speedup/keep с причинами, спорное помечает",
      "files": []
    },
    {
      "id": 3,
      "prompt": "я записал рилс на камеру, звук отдельно — просто вырежи тишину и пык-мык, ничего не ускоряй",
      "expected_output": "Профиль light без визуального анализа (extract_frames не вызывается), синхрон + тишина + филлеры, на выходе предлагает FCPXML или готовый mp4",
      "files": []
    },
    {
      "id": 4,
      "prompt": "в 02:15 ты зря вырезал — верни этот кусок и переэкспортируй",
      "expected_output": "Правит существующий cutlist.json (сегмент → keep), анализ заново НЕ гоняет, перезапускает только экспортёр",
      "files": []
    },
    {
      "id": 5,
      "prompt": "скачай этот рилс с инстаграма и переупакуй под меня",
      "expected_output": "rough-cut НЕ активируется — это instagram-downloader",
      "files": []
    },
    {
      "id": 6,
      "prompt": "у меня нет ffmpeg, но обработай запись test.mp4",
      "expected_output": "Доктор перечисляет недостающее с командами установки под платформу, НЕ ставит без согласия; без whisper предлагает режим «только тишина», а не отказ",
      "files": []
    }
  ]
}
```

- [ ] **Step 5: Витрина**

В таблицу `skills/README.md` добавить строку (в алфавитно-логичное место, рядом с другими):

```markdown
| [rough-cut/](rough-cut/) | Черновой монтаж: синхрон звука OBS с камерой по волне, вырезание тишины/филлеров/дублей (LLM по транскрипту), скринкаст-таймлапсы по кадрам; cut-list JSON → FCPXML (Resolve) и/или готовый mp4 (CapCut/рилсы) |
```

- [ ] **Step 6: Проверка триггера и полный прогон тестов**

Run: `uv run --with pytest --with numpy --with scipy python -m pytest tests -v` — все passed.
Прочитать SKILL.md глазами на предмет: (а) все команды совпадают с реальными CLI скриптов; (б) нет личного/приватного; (в) description содержит триггерные фразы из evals 1–3 и отсечки 5.

- [ ] **Step 7: Commit**

```bash
git add skills/rough-cut skills/README.md && git commit -m "rough-cut: SKILL.md (оркестрация пайплайна), references (пороги/правила Decide/FCPXML), README, evals, витрина"
```

---

### Task 11: Подключение глобально + финальная сверка со спеком

**Files:**
- Modify: (ничего в репо — запуск скрипта установки симлинков)

- [ ] **Step 1: Симлинк в ~/.claude/skills**

Run: `bash /Users/wolkart/AI/aifuture_hub/skills/install-skills.sh`
Expected: создан симлинк `~/.claude/skills/rough-cut`, существующие не тронуты. Проверить: `ls -la ~/.claude/skills/ | grep rough-cut`.

- [ ] **Step 2: Сверка со спеком**

Пройтись по `docs/superpowers/specs/2026-07-11-rough-cut-skill-design.md` секция за секцией и отметить, что реализовано: 5 стадий + доктор; 2 профиля; 3 сценария; cut-list схема; 2 экспортёра; онбординг (5 пунктов); стражи; evals. Расхождения — починить или явно зафиксировать в коммите.

- [ ] **Step 3: Финальный прогон и коммит хвостов**

Run: `cd /Users/wolkart/AI/aifuture_hub/skills/rough-cut && uv run --with pytest --with numpy --with scipy python -m pytest tests -v`
Expected: все passed. Если были правки — закоммитить:

```bash
git add -A skills/rough-cut && git commit -m "rough-cut: финальная сверка со спеком"
```

После этого — скилл superpowers:finishing-a-development-branch (PR в main).
