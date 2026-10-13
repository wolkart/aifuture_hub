"""Слова расшифровки и якоря плана. Только stdlib.

Всё в плане привязано к словам, а не к секундам: «вставка на слове „сервер“, второе
вхождение, на 0,1 с раньше». Тогда план переносится на любой дубль и переживает
пересборку чернового — секунды после неё съезжают, слова остаются.

Якорь в plan.json — число (секунды ролика) или объект:
  {"word": "сервер", "n": 2, "shift": -0.1, "edge": "start"}
  n — номер вхождения (с 1), shift — сдвиг в секундах, edge — start|end слова.
"""
import json
import re
from pathlib import Path


def norm(text):
    """Слово для сравнения: нижний регистр, ё→е, без пунктуации по краям, дефис внутри
    сохраняется («телеграм-канал»)."""
    t = str(text).lower().replace("ё", "е")
    return re.sub(r"^[^\w]+|[^\w-]+$", "", t).strip("-")


def load(path):
    """transcript.json → [{"text", "start", "end"}]. Принимает и поле word (Whisper)."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for w in d["words"]:
        out.append({"text": (w.get("text") or w.get("word") or "").strip(),
                    "start": float(w["start"]), "end": float(w["end"])})
    return out


def find(words, text, n=1):
    target, k = norm(text), 0
    for w in words:
        if norm(w["text"]) == target:
            k += 1
            if k == n:
                return w
    raise KeyError(f"нет слова «{text}» (вхождение {n}); найдено вхождений: {k}")


def at(words, anchor):
    """Якорь → секунды ролика."""
    if anchor is None:
        return None
    if isinstance(anchor, (int, float)):
        return float(anchor)
    if isinstance(anchor, str):
        anchor = {"word": anchor}
    w = find(words, anchor["word"], int(anchor.get("n", anchor.get("nth", 1))))
    base = w["end"] if anchor.get("edge") == "end" else w["start"]
    return round(base + float(anchor.get("shift", 0.0)), 3)


def label(anchor):
    """Короткая подпись якоря для PLAN.md: «сервер»#2."""
    if isinstance(anchor, (int, float)):
        return f"{float(anchor):.2f} с"
    if isinstance(anchor, str):
        return f"«{anchor}»"
    n = int(anchor.get("n", anchor.get("nth", 1)))
    return f"«{anchor['word']}»" + (f"#{n}" if n > 1 else "")


def first_at_or_after(words, t, tol=0.05):
    return next((w for w in words if w["start"] >= t - tol), None)
