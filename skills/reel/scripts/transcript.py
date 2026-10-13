#!/usr/bin/env python3
"""Расшифровка смонтированного ролика → transcript.json. Только stdlib + ffmpeg.

Что делает по порядку:
  1. словарь замен из настроек (+ разовые --replace): «клод код» → «Claude Code»; ключ может быть
     из нескольких слов («RSS ленты» → «RSS-ленты»), пунктуация на конце сохраняется;
  2. склейка слов, которые Whisper разорвал на дефисе («телеграм» + «-канал»);
  3. если есть сценарий — обрезка «хвоста» после последнего слова сценария (Whisper
     дописывает в тишине то, чего не было) и список расхождений;
  4. подгонка слов к звуку — snap_words из rough-cut: после пауз Whisper ставит слово
     на 0,3–0,4 с раньше голоса, а субтитры и вставки по словам выскочат до звука.

usage: transcript.py <words.raw.json> <смонтированный mp4> [-o transcript.json]
                     [--settings reel.settings.json] [--script сценарий.txt]
                     [--replace "было=стало" …]
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import settings as settings_mod  # noqa: E402
from words import norm  # noqa: E402


def rough_cut_scripts():
    """Скрипты соседнего скилла rough-cut (резка — первая стадия /reel)."""
    for cand in (HERE.parents[1] / "rough-cut" / "scripts",
                 Path.home() / ".claude" / "skills" / "rough-cut" / "scripts"):
        if (cand / "snap_words.py").exists():
            return cand
    raise SystemExit("transcript: не найден скилл rough-cut рядом (нужен snap_words.py)")


def to_words(raw):
    return [{"text": (w.get("text") or w.get("word") or "").strip(),
             "start": float(w["start"]), "end": float(w["end"])} for w in raw["words"]
            if (w.get("text") or w.get("word") or "").strip()]


def _tail_punct(text):
    m = re.search(r"[^\w-]+$", text)
    return m.group(0) if m else ""


def apply_dictionary(words, mapping):
    """Замены по словарю: ключи сравниваются нормализованно, длинные ключи — первыми.
    Возвращает (новый список, сколько замен)."""
    keys = sorted(((tuple(norm(t) for t in k.split()), v) for k, v in mapping.items() if k.strip()),
                  key=lambda kv: -len(kv[0]))
    out, i, n = [], 0, 0
    while i < len(words):
        for key, value in keys:
            span = words[i:i + len(key)]
            if len(span) == len(key) and tuple(norm(w["text"]) for w in span) == key:
                tail = _tail_punct(span[-1]["text"])
                text = value if _tail_punct(value) else value + tail
                out.append({"text": text, "start": span[0]["start"], "end": span[-1]["end"]})
                i += len(key)
                n += 1
                break
        else:
            out.append(dict(words[i]))
            i += 1
    return out, n


def merge_split(words):
    """«телеграм» + «-канал» → «телеграм-канал»."""
    out = []
    for w in words:
        if out and w["text"].startswith("-") and len(w["text"]) > 1:
            out[-1] = {"text": out[-1]["text"].rstrip(",.") + w["text"],
                       "start": out[-1]["start"], "end": w["end"]}
        else:
            out.append(dict(w))
    return out


def script_tokens(script):
    return [t for t in (norm(x) for x in re.split(r"\s+", script)) if t]


def trim_to_script(words, script):
    """Отрезать слова после конца сценария (галлюцинации Whisper в тишине)."""
    s, t = script_tokens(script), [norm(w["text"]) for w in words]
    blocks = [b for b in difflib.SequenceMatcher(None, s, t, autojunk=False).get_matching_blocks()
              if b.size]
    if not blocks:
        return words
    last = blocks[-1]
    end = last.b + last.size + (len(s) - last.a - last.size)
    return words[:min(len(words), end)]


def diff_script(words, script):
    """Расхождения расшифровки со сценарием: [«12.30 с: „было“ ≠ сценарий „стало“»]."""
    s_raw = [x for x in re.split(r"\s+", script) if norm(x)]
    s = [norm(x) for x in s_raw]
    t = [norm(w["text"]) for w in words]
    out = []
    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, s, t, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        at = words[min(b0, len(words) - 1)]["start"] if words else 0.0
        heard = " ".join(w["text"] for w in words[b0:b1]) or "—"
        want = " ".join(s_raw[a0:a1]) or "—"
        out.append(f"{at:6.2f} с: «{heard}» ≠ сценарий «{want}»")
    return out


def parse_replace(items):
    out = {}
    for it in items or []:
        if "=" in it:
            k, v = it.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words_json")
    ap.add_argument("audio")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--settings", default=None)
    ap.add_argument("--script", default=None, help="текст сценария (файл)")
    ap.add_argument("--replace", action="append", help="разовая замена «было=стало»")
    args = ap.parse_args()

    s = settings_mod.load(args.settings) or settings_mod.default()
    mapping = dict(s["dictionary"])
    mapping.update(parse_replace(args.replace))
    raw = json.loads(Path(args.words_json).read_text(encoding="utf-8"))
    words, n_dict = apply_dictionary(to_words(raw), mapping)
    words = merge_split(words)
    script = Path(args.script).read_text(encoding="utf-8") if args.script else None
    if script:
        before = len(words)
        words = trim_to_script(words, script)
        if len(words) < before:
            print(f"обрезано после конца сценария: {before - len(words)} слов")

    sys.path.insert(0, str(rough_cut_scripts()))
    import snap_words
    words, moved = snap_words.snap(words, snap_words.db_reader(args.audio))

    out = Path(args.out or Path(args.words_json).with_name("transcript.json"))
    text = " ".join(w["text"] for w in words)
    out.write_text(json.dumps({"text": text, "words": [
        {"text": w["text"], "start": round(w["start"], 3), "end": round(w["end"], 3)} for w in words]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"расшифровка: {len(words)} слов, замен по словарю {n_dict}, подтянуто к звуку {moved} → {out}")
    if script:
        diffs = diff_script(words, script)
        print("сверка со сценарием: " + ("совпадает" if not diffs else f"расхождений {len(diffs)}"))
        for d in diffs:
            print("  " + d)
    print(text)


if __name__ == "__main__":
    main()
