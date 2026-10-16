#!/usr/bin/env python3
"""Шортсы из длинного ролика: выбор кусков → таблица → резка выбранных. Только stdlib + ffmpeg.

Шортс — кусок 30–60 с, понятный без остального ролика: первая фраза работает как хук
(не «как я уже говорил», не «и вот»), конец законченный (точка, а не середина мысли).
Куски выбирает агент по фразам (`longform.py lines`) и пишет shorts.json; скрипт
проверяет каждый механически и печатает таблицу. Рендерить до выбора автора нельзя:
сборка шортса — минуты, выбор по таблице — секунды.

shorts.json:
  {"shorts": [{"phrases": [210, 236], "title": "почему бот, а не n8n"},
              {"from": "b:410", "to": "a:452", "title": "…"}]}
Якоря — как в longform.py (номера фраз; время — видео).

  check <words.json> --plan shorts.json [--offset S]
        → таблица # / где / длина / о чём / первая и последняя фраза / ⚠
  cut   <видео> --words W --plan shorts.json --pick 1 3 [--audio A] [--offset S]
        → export/shorts/<n>/_сборка/<стем>-<n>.cutlist.json: только кусок, внутри —
          тишина и явные запинки; дальше render.py и /reel по этой папке
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cutlist  # noqa: E402
import longform as lf  # noqa: E402

MIN_LEN, MAX_LEN = 30.0, 60.0
# начало, которое опирается на сказанное раньше: без него шортс непонятен
LEAN_START = re.compile(r"^(и|а|но|вот|так|поэтому|то есть|кстати|ну|тут|здесь|это|этот|эта|эти|он|она|они|"
                        r"как я|как уже|соответственно|следовательно|дальше|потом|теперь)\b", re.I)
BACKREF = re.compile(r"как я (уже )?говорил|как уже говорил|выше|ранее|в прошлый раз|как мы (уже )?видели|"
                     r"я уже показывал|помните", re.I)


def checks(phr, a, b):
    """⚠ к куску: длина, начало без контекста, отсылки назад, обрыв в конце."""
    ws = [w for p in phr for w in p["words"] if a <= (w["start"] + w["end"]) / 2 <= b]
    out = []
    if not ws:
        return ["в куске нет слов"], ws
    length = b - a
    if length < MIN_LEN or length > MAX_LEN:
        out.append(f"длина {length:.0f} с — вне {MIN_LEN:.0f}–{MAX_LEN:.0f}")
    text = " ".join(w["text"] for w in ws)
    first = re.sub(r"^[^\w]+", "", ws[0]["text"])
    m = LEAN_START.match(" ".join([first] + [w["text"] for w in ws[1:3]]))
    if m:
        out.append(f"начало опирается на прошлое: «{m.group(0)}…»")
    if BACKREF.search(text):
        out.append(f"отсылка назад: «{BACKREF.search(text).group(0)}»")
    if ws[-1]["text"][-1:] not in ".?!…":
        out.append("конец без точки — возможно, обрыв мысли")
    return out, ws


def table(phr, plan, dur):
    rows = ["| # | где | длина | о чём | первая фраза | последняя фраза | ⚠ |", "|---|---|---|---|---|---|---|"]
    for n, item in enumerate(plan["shorts"], 1):
        a, b = lf.span(item, phr, dur)
        warn, ws = checks(phr, a, b)
        first = next((p["text"] for p in phr if p["a"] >= a - 0.05), "")
        last = next((p["text"] for p in reversed(phr) if p["b"] <= b + 0.05), "")
        rows.append(f"| {n} | {lf.mmss(a)}–{lf.mmss(b)} | {b - a:.0f} с | {item.get('title', '')} | "
                    f"{first[:60]} | {last[:60]} | {'; '.join(warn) or '—'} |")
    return "\n".join(rows)


def short_cutlist(base, phr_words, a, b):
    """Cut-list на весь исходник, где оставлен только [a, b] минус тишина и запинки внутри."""
    dur = base["duration_s"]
    inner = [s for s in base["segments"] if s["action"] == "cut" and s["end"] > a and s["start"] < b]
    inner = [dict(s, start=max(s["start"], a), end=min(s["end"], b)) for s in inner]
    fill = [c for c in lf.filler_cuts(phr_words) if a <= c["start"] and c["end"] <= b]
    edges = []
    if a > cutlist.EPS:
        edges.append({"start": 0.0, "end": round(a, 3), "action": "cut", "source": "user",
                      "reason": "до шортса", "confidence": 1.0})
    if dur - b > cutlist.EPS:
        edges.append({"start": round(b, 3), "end": round(dur, 3), "action": "cut", "source": "user",
                      "reason": "после шортса", "confidence": 1.0})
    meta = {k: base[k] for k in base if k not in ("version", "segments")}
    return cutlist.from_cuts(meta, lf.merge(edges + inner + fill))


def cmd_check(args):
    phr = lf.phrases(lf.load_words(args.words, args.offset))
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    print(table(phr, plan, phr[-1]["b"] + 1 if phr else 0))
    print("\nкакие берём? (номера) — рендер только выбранных")


def cmd_cut(args):
    import silence_cut
    words = lf.load_words(args.words, args.offset if args.words_offset is None else args.words_offset)
    phr = lf.phrases(words)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    base = silence_cut.build_silence_cutlist(args.video, args.audio, args.offset, 1.0, args.noise_db,
                                             args.min_dur, args.pad, args.min_cut)
    stem = Path(args.video).stem
    root = cutlist.export_dir(args.video) / "shorts"
    for n in args.pick:
        item = plan["shorts"][n - 1]
        a, b = lf.span(item, phr, base["duration_s"])
        d = short_cutlist(base, words, a, b)
        build = root / str(n) / "_сборка"
        build.mkdir(parents=True, exist_ok=True)
        out = build / f"{stem}-{n}.cutlist.json"
        out.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        kept = lf.out_time(d["segments"], d["duration_s"] + 1)
        print(f"шортс {n} «{item.get('title', '')}»: {lf.mmss(a)}–{lf.mmss(b)} → {kept:.1f} с → {out}")
        print(f"  рендер: uv run scripts/render.py {out} --out {build / (stem + f'-{n}.roughcut.mp4')}")
        print(f"  дальше: /reel по {build / 'v1'} (стадии 2–7; горизонтальный кадр ставит build_main)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("words")
    c.add_argument("--plan", required=True)
    c.add_argument("--offset", type=float, default=0.0)
    k = sub.add_parser("cut")
    k.add_argument("video")
    k.add_argument("--words", required=True)
    k.add_argument("--plan", required=True)
    k.add_argument("--pick", type=int, nargs="+", required=True)
    k.add_argument("--audio")
    k.add_argument("--offset", type=float, default=0.0)
    k.add_argument("--words-offset", type=float, default=None)
    k.add_argument("--noise-db", type=float, default=-38.0)
    k.add_argument("--min-dur", type=float, default=0.7)
    k.add_argument("--pad", type=float, default=0.2)
    k.add_argument("--min-cut", type=float, default=0.4)
    args = ap.parse_args()
    {"check": cmd_check, "cut": cmd_cut}[args.cmd](args)


if __name__ == "__main__":
    main()
