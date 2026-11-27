#!/usr/bin/env python3
"""Ищет в новом тексте фразы, повторяющие образцы автора дословно.

Образцы показывают, КАК автор строит фразы, а не банк готовых фраз. Совпадение
4 слов подряд с файлом образцов или 3 слов с фразой в «ёлочках» (двухсловная —
целиком) — сигнал: фраза взята оттуда.
Её нужно переписать своей на том же приёме — если только автор не надиктовал
её сам в этой сессии.

Запуск:
    python3 ngram_check.py ТЕКСТ.txt ОБРАЗЦЫ.md [ЕЩЁ.md ...] [-n 4]
    echo "текст" | python3 ngram_check.py - ОБРАЗЦЫ.md
"""
import argparse
import re
import sys

WORD = re.compile(r"[\wё]+", re.IGNORECASE)
QUOTE = re.compile(r"«([^»]{3,200})»")


def words(text):
    return [w.lower().replace("ё", "е") for w in WORD.findall(text)]


def ngrams(ws, n):
    return {tuple(ws[i:i + n]) for i in range(len(ws) - n + 1)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", help="файл с новым текстом или - для stdin")
    ap.add_argument("samples", nargs="+", help="файлы образцов")
    ap.add_argument("-n", type=int, default=4, help="длина совпадения в словах (4)")
    a = ap.parse_args()

    text = sys.stdin.read() if a.text == "-" else open(a.text, encoding="utf-8").read()
    sample_grams = set()   # 4 слова подряд по всему файлу образцов
    short_grams = set()    # фирменные фразы в «ёлочках»: по 3 слова, двухсловные целиком
    for f in a.samples:
        raw = open(f, encoding="utf-8").read()
        sample_grams |= ngrams(words(raw), a.n)
        for q in QUOTE.findall(raw):
            qw = words(q)
            short_grams |= ngrams(qw, 3) if len(qw) >= 3 else ({tuple(qw)} if len(qw) == 2 else set())

    ws = words(text)
    hits = []
    for i in range(len(ws)):
        if tuple(ws[i:i + a.n]) in sample_grams:
            hits.append((i, a.n))
        elif tuple(ws[i:i + 3]) in short_grams:
            hits.append((i, 3))
        elif tuple(ws[i:i + 2]) in short_grams:
            hits.append((i, 2))
    if not hits:
        print("Повторов нет")
        return
    # склеиваем соседние совпадения в фразы
    spans, (start, ln) = [], hits[0]
    end = start + ln
    for i, ln in hits[1:]:
        if i <= end:
            end = max(end, i + ln)
        else:
            spans.append((start, end))
            start, end = i, i + ln
    spans.append((start, end))
    print(f"Совпадения с образцами ({len(spans)}):")
    for s, e in spans:
        print("  «" + " ".join(ws[s:e]) + "»")


if __name__ == "__main__":
    main()
