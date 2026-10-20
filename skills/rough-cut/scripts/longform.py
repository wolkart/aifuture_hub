#!/usr/bin/env python3
"""Длинная запись (20–60 мин): резка без таблицы на 500 строк. Только stdlib + ffmpeg.

Снято с ручного прогона 66-минутного скринкаста (2026-10-16: 64:08 → 46:09, 44 реза
по смыслу, автор: «неплохо»). Три шага:

  lines   — расшифровка → нумерованные фразы с паузами (рвём на паузе ≥ 0,45 с или
            на точке длинной фразы) + подсказка, какими кусками читать (~10 мин,
            нахлёст 1 мин). Агент читает файл кусками и пишет резы по номерам фраз.
  build   — тишина по звуку (не по расшифровке: Whisper растягивает слова на тишину)
            + явные запинки «э-э / м-м», если они есть в расшифровке (Scribe их пишет,
            Whisper обычно нет) + резы по смыслу из plan.json → один cut-list и
            короткий отчёт-шлюз: было → стало, смысловые резы с номерами, «решай сам».
  restore — «верни 3, 7»: номера из отчёта → keep в plan.json → build заново,
            без повторного анализа.

plan.json (пишет агент по правилам decide-rules.md, раздел «По смыслу»):
  {"cuts":   [{"phrases": [43, 46], "why": "блуждание по настройкам (~36 с)"},
              {"from": "a:59", "to": "b:62", "why": "…"}, {"from": "t:1669.5", "to": "t:1702", "why": "…"}],
   "decide": [{"phrases": [120, 141], "why": "отступление про карты"}],
   "keep":   [3, 7]}
Якоря: a:N — сразу после фразы N, b:N — перед фразой N, t:X — секунда видео,
w:N:K — начало K-го слова фразы N. phrases [N, M] = фразы N…M вместе с паузами вокруг.
Время везде — видео (звук минус sync.offset_s), как в cut-list.

usage:
  longform.py lines   <words.json> [--offset S] [-o lines.txt]
  longform.py build   <видео> --words W --plan plan.json [--audio A] [--offset S]
                      [--noise-db -38 --min-dur 0.7 --pad 0.2] [-o cutlist.json]
  longform.py restore <plan.json> N [N …]
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cutlist  # noqa: E402

PAUSE = 0.45      # пауза, на которой рвём фразу
EDGE = 0.12       # запас у соседней фразы, когда режем по границе фраз
CHUNK = 600.0     # кусок чтения, с
OVERLAP = 60.0
BIG = 10.0        # рез длиннее — в шлюз обязательно, даже если не по смыслу
FILLER = re.compile(r"^(э+(-э+)*|эм+|э-м+|м+(-м+)*|хм+|а(-а+)+|uh+|um+|erm+|hmm+)$", re.I)  # Scribe: «Э-э-э,», «м-м-м»
PRIORITY = {"semantic": 4, "retake": 3, "filler": 2, "silence": 1}


def load_words(path, offset=0.0):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return [{"text": (w.get("word") or w.get("text") or "").strip(),
             "start": round(float(w["start"]) - offset, 3), "end": round(float(w["end"]) - offset, 3)}
            for w in d["words"] if (w.get("word") or w.get("text") or "").strip()]


def phrases(words, pause=PAUSE):
    """Слова → фразы [{n, a, b, text, words}] (нумерация с 1)."""
    out, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] >= pause
                    or (cur[-1]["text"][-1:] in ".?!" and len(cur) >= 4)):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return [{"n": i + 1, "a": p[0]["start"], "b": p[-1]["end"], "text": " ".join(w["text"] for w in p),
             "words": p} for i, p in enumerate(out)]


def mmss(t):
    t = max(0.0, t)
    return f"{int(t // 60):d}:{t % 60:04.1f}"


def lines_text(phr):
    """Текст для чтения + разбивка на куски: [(строка файла от, до, время от, до)]."""
    out, prev, starts = [], 0.0, []
    for p in phr:
        gap = p["a"] - prev
        if gap >= 1.0:
            out.append(f"      … пауза {gap:.1f} с")
        starts.append((len(out) + 1, p["a"]))
        out.append(f"{p['n']:5d}  {mmss(p['a']):>7}–{mmss(p['b']):<7} {p['text']}")
        prev = p["b"]
    chunks, t0 = [], 0.0
    end = phr[-1]["b"] if phr else 0.0
    while t0 < end:
        rows = [ln for ln, t in starts if t0 <= t < t0 + CHUNK + OVERLAP]
        if rows:
            chunks.append((rows[0], rows[-1], t0, min(end, t0 + CHUNK + OVERLAP)))
        t0 += CHUNK
    return out, chunks


def anchor(spec, phr, dur):
    """Якорь → секунды видео."""
    kind, _, rest = str(spec).partition(":")
    if kind == "t":
        return max(0.0, min(dur, float(rest)))
    if kind == "w":
        n, k = (int(x) for x in rest.split(":"))
        return max(0.0, phr[n - 1]["words"][k - 1]["start"] - 0.03)
    n = int(rest)
    if kind == "a":
        if n >= len(phr):
            return dur
        return min(phr[n - 1]["b"] + EDGE, phr[n]["a"])
    if kind == "b":
        if n <= 1:
            return 0.0
        return max(phr[n - 1]["a"] - EDGE, phr[n - 2]["b"])
    raise ValueError(f"якорь «{spec}»: ожидается a:N, b:N, t:X или w:N:K")


def span(item, phr, dur):
    if "phrases" in item:
        n, m = item["phrases"]
        return anchor(f"a:{n - 1}", phr, dur) if n > 1 else 0.0, anchor(f"b:{m + 1}", phr, dur) if m < len(phr) else dur
    return anchor(item["from"], phr, dur), anchor(item["to"], phr, dur)


def quote(phr, a, b, limit=70):
    """Слова, которые целиком внутри [a, b] (по середине слова: Whisper тянет слова на тишину)."""
    text = " ".join(w["text"] for p in phr for w in p["words"] if a <= (w["start"] + w["end"]) / 2 <= b)
    return (text[:limit] + "…") if len(text) > limit else text


def filler_cuts(words):
    return [{"start": round(max(0.0, w["start"] - 0.03), 3), "end": round(w["end"] + 0.03, 3), "action": "cut",
             "source": "filler", "reason": f"запинка «{w['text']}»", "confidence": 0.9}
            for w in words if FILLER.match(w["text"].strip(".,!?…—-").lower())]


def merge(cuts):
    """Слить пересекающиеся резы; причина — от самого «смыслового» (semantic > retake > filler > silence)."""
    out = []
    for c in sorted(cuts, key=lambda c: c["start"]):
        if out and c["start"] <= out[-1]["end"] + cutlist.EPS:
            top = out[-1]
            if PRIORITY.get(c["source"], 0) > PRIORITY.get(top["source"], 0):
                top.update({k: c[k] for k in ("source", "reason", "confidence", "n", "quote") if k in c})
            top["end"] = max(top["end"], c["end"])
        else:
            out.append(dict(c))
    return out


def semantic_cuts(plan, phr, dur):
    """Резы по смыслу с номерами по порядку времени; keep — вернуть, decide — не резать."""
    items = sorted(((span(c, phr, dur), c) for c in plan.get("cuts", [])), key=lambda x: x[0][0])
    keep = set(plan.get("keep", []))
    out = []
    for n, ((a, b), c) in enumerate(items, 1):
        if n in keep or b - a < 0.05:
            continue
        out.append({"start": round(a, 3), "end": round(b, 3), "action": "cut", "source": "semantic",
                    "reason": c["why"], "confidence": 0.8, "n": n, "quote": quote(phr, a, b)})
    return out, [(n, span(c, phr, dur), c["why"]) for n, c in enumerate([c for _, c in items], 1) if n in keep]


def out_time(segments, t):
    """Секунда исходника → секунда готового ролика (сумма оставленного до неё)."""
    acc = 0.0
    for s in segments:
        if s["end"] <= t:
            if s["action"] != "cut":
                acc += (s["end"] - s["start"]) / (s.get("rate", 1) if s["action"] == "speedup" else 1)
        elif s["start"] < t:
            if s["action"] != "cut":
                acc += t - s["start"]
            break
    return acc


def report(d, phr, decide, returned):
    segs = d["segments"]
    before = d["duration_s"]
    after = out_time(segs, before + 1)
    cuts = [s for s in segs if s["action"] == "cut"]
    by = {}
    for s in cuts:
        k = s.get("source", "?")
        by.setdefault(k, [0, 0.0])
        by[k][0] += 1
        by[k][1] += s["end"] - s["start"]
    names = {"silence": "тишина", "filler": "запинки", "semantic": "по смыслу", "retake": "дубли", "gaze": "взгляд"}
    lines = [f"Было {mmss(before)} → стало {mmss(after)} (−{mmss(before - after)}): "
             + ", ".join(f"{names.get(k, k)} {n} ({mmss(t)})" for k, (n, t) in sorted(by.items(), key=lambda x: -x[1][1])),
             "", "## Резы по смыслу — номер, чтобы вернуть: «верни 3, 7»", ""]
    big = sorted([s for s in cuts if s.get("source") == "semantic"
                  or (s["end"] - s["start"] >= BIG and s.get("source") != "silence")], key=lambda s: s["start"])
    for s in big:
        tag = f"{s['n']:3d}." if s.get("n") else "   —"
        lines.append(f"{tag} {mmss(out_time(segs, s['start']))} стык · −{s['end'] - s['start']:.1f} с · "
                     f"«{s.get('quote') or quote(phr, s['start'], s['end'])}» — {s['reason']}")
    if returned:
        lines += ["", "## Возвращено по просьбе", ""]
        lines += [f"{n:3d}. {mmss(a)}–{mmss(b)} — {why}" for n, (a, b), why in returned]
    if decide:
        lines += ["", "## Не резал — решай сам", ""]
        for item in decide:
            a, b = span(item, phr, before)
            lines.append(f"  - {mmss(out_time(segs, a))}–{mmss(out_time(segs, b))} (было {mmss(a)}, {b - a:.0f} с) — {item['why']}")
    long_sil = [s for s in cuts if s.get("source") == "silence" and s["end"] - s["start"] >= BIG]
    if long_sil:
        lines += ["", f"Тишина ≥ {BIG:.0f} с вырезана {len(long_sil)} раз — на скринкасте проверь, не ожидание ли "
                  "результата на экране (тогда вернуть или ускорить)."]
    return "\n".join(lines)


def cmd_lines(args):
    phr = phrases(load_words(args.words, args.offset))
    text, chunks = lines_text(phr)
    out = Path(args.out or Path(args.words).with_name(Path(args.words).name.replace(".words.json", "") + ".lines.txt"))
    out.write_text("\n".join(text) + "\n", encoding="utf-8")
    print(f"фраз {len(phr)}, {mmss(phr[-1]['b']) if phr else '0:00'} → {out}")
    print("читай кусками (строки файла):")
    for a, b, t0, t1 in chunks:
        print(f"  строки {a}–{b}  ({mmss(t0)}–{mmss(t1)})")


def cmd_build(args):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import silence_cut
    words = load_words(args.words, args.offset if args.words_offset is None else args.words_offset)
    phr = phrases(words)
    base = silence_cut.build_silence_cutlist(args.video, args.audio, args.offset, 1.0, args.noise_db,
                                             args.min_dur, args.pad, args.min_cut)
    dur = base["duration_s"]
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8")) if args.plan else {}
    sem, returned = semantic_cuts(plan, phr, dur)
    cuts = merge([s for s in base["segments"] if s["action"] == "cut"] + filler_cuts(words) + sem)
    meta = {k: base[k] for k in base if k not in ("version", "segments")}
    d = cutlist.from_cuts(meta, cuts)
    out = Path(args.out or cutlist.export_dir(args.video) / (Path(args.video).stem + ".cutlist.json"))
    out.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    rep = report(d, phr, plan.get("decide", []), returned)
    rep_path = out.with_name(out.name.replace(".cutlist.json", "") + ".report.md")
    full = ["| исходник | длина | источник | причина |", "|---|---|---|---|"] + [
        f"| {mmss(s['start'])}–{mmss(s['end'])} | {s['end'] - s['start']:.1f} | {s.get('source', '')} | {s.get('reason', '')} |"
        for s in d["segments"] if s["action"] == "cut"]
    rep_path.write_text(rep + "\n\n## Все резы\n\n" + "\n".join(full) + "\n", encoding="utf-8")
    print(rep)
    print(f"\ncut-list → {out}\nполная таблица → {rep_path}")


def cmd_restore(args):
    p = Path(args.plan)
    plan = json.loads(p.read_text(encoding="utf-8"))
    plan["keep"] = sorted(set(plan.get("keep", [])) | set(args.numbers))
    p.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"вернуть: {plan['keep']} → пересобери: longform.py build … --plan {p}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("lines")
    a.add_argument("words")
    a.add_argument("--offset", type=float, default=0.0)
    a.add_argument("-o", "--out")
    b = sub.add_parser("build")
    b.add_argument("video")
    b.add_argument("--words", required=True)
    b.add_argument("--plan")
    b.add_argument("--audio")
    b.add_argument("--offset", type=float, default=0.0, help="sync.offset_s: звук = видео + offset")
    b.add_argument("--words-offset", type=float, default=None,
                   help="сдвиг слов, если расшифровка не по звуку (по умолчанию = --offset)")
    b.add_argument("--noise-db", type=float, default=-38.0)
    b.add_argument("--min-dur", type=float, default=0.7)
    b.add_argument("--pad", type=float, default=0.2)
    b.add_argument("--min-cut", type=float, default=0.4)
    b.add_argument("-o", "--out")
    r = sub.add_parser("restore")
    r.add_argument("plan")
    r.add_argument("numbers", type=int, nargs="+")
    args = ap.parse_args()
    {"lines": cmd_lines, "build": cmd_build, "restore": cmd_restore}[args.cmd](args)


if __name__ == "__main__":
    main()
