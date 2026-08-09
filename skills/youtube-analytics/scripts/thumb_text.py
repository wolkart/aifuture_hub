#!/usr/bin/env python3
"""Текст на превью: разбор вывода OCR и срез признаков. Только stdlib.

Замер 2026-08-09 (Vibecoder School, 47 превью): на превью работает та же
ось, что в тайтле — цена, имя инструмента, конкретика. Расхожий совет
«2–4 слова на превью» не подтвердился: короткие дали 0.89 против 1.27.
"""
import re
import statistics

MIN_GROUP = 5
SHORT_TEXT_WORDS = 4

FEATURES = {
    "бесплатно": r"бесплатн|\bfree\b|0\s*₽|даром",
    "имя инструмента": (r"cursor|claude|chatgpt|\bgpt\b|midjourney|copilot|"
                        r"gemini|windsurf|figma|notion|canva|n8n|codex"),
    "цифра": r"\d",
    "запрет": r"перестань|хватит|забудь|больше не|\bstop\b|don'?t",
}

_HEADER = re.compile(r"^===\s+(.+?)(?:\.[A-Za-z0-9]+)?\s*$")


def parse_ocr_output(text):
    """Вывод ocr-cards.sh → {video_id: [строки]}.

    Блок начинается с '=== <файл>'. Строка на '!!' — сообщение об ошибке
    Vision, а не распознанный текст: такой блок остаётся пустым.
    """
    blocks = {}
    current = None
    for line in (text or "").splitlines():
        m = _HEADER.match(line.strip())
        if m:
            current = m.group(1)
            blocks[current] = []
            continue
        clean = line.strip()
        if current is None or not clean or clean.startswith("!!"):
            continue
        blocks[current].append(clean)
    return blocks


def features(text):
    text = text or ""
    return {name: bool(re.search(pattern, text, re.I))
            for name, pattern in FEATURES.items()}


def word_count(lines):
    return len(" ".join(lines or []).split())


def _median(values):
    return round(statistics.median(values), 2) if values else None


def _pair(records, ids_yes, ids_no):
    yes = [records[i]["median_multiple"] for i in ids_yes
           if records.get(i, {}).get("median_multiple") is not None]
    no = [records[i]["median_multiple"] for i in ids_no
          if records.get(i, {}).get("median_multiple") is not None]
    return {"n": len(yes), "median_multiple": _median(yes),
            "median_without": _median(no), "reliable": len(yes) >= MIN_GROUP}


def slice_by_feature(records, blocks):
    """Срез по каждому признаку + по длине текста. records: {id: {...}}."""
    known = [i for i in blocks if i in records]
    out = {}
    for name in FEATURES:
        yes = [i for i in known if features(" ".join(blocks[i]))[name]]
        no = [i for i in known if not features(" ".join(blocks[i]))[name]]
        out[name] = _pair(records, yes, no)

    short = [i for i in known if 0 < word_count(blocks[i]) <= SHORT_TEXT_WORDS]
    long_ = [i for i in known if word_count(blocks[i]) > SHORT_TEXT_WORDS]
    out["текст ≤%d слов" % SHORT_TEXT_WORDS] = _pair(records, short, long_)
    return out
