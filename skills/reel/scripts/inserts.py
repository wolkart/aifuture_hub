"""Пункты плана → время ролика + проверки. Только stdlib.

Пункты plan.json["items"] (якоря — см. words.at):
  {"kind": "broll", "from": <якорь>, "to": <якорь>, "asset": "<id из библиотеки>" | "file": "<путь>",
   "in": 19.8, "rate": 1, "layout": "full"|"half", "pos": "50% 45%", "note": "что видно"}
  {"kind": "card", "template": "tiles", "from": <якорь>, "to": <якорь>, "slots": {...}}
  {"kind": "missing", "at": <якорь>, "want": "что хотелось показать"}
      → строка плана «нет ассета → карточка или motion-assets»; ассет на лету не изобретается.

Проверки (в PLAN.md видно каждую):
  • длина вставки вне ориентира 0,5–1,8 с — ⚠ (ориентир, не запрет);
  • б-роллы налезают друг на друга — ошибка;
  • окно источника задевает приватное окно из описи — ошибка (IP, ключи, токены);
  • окно источника задевает переход/наезд записи экрана — ⚠ кадр на размытом переходе;
  • окно выходит за длину источника — ошибка.
"""
from pathlib import Path


def overlaps(a0, a1, b0, b1, eps=1e-3):
    return a0 < b1 - eps and b0 < a1 - eps


def spans_from_cutlist(cl):
    """Куски черновика на таймлайне ролика: [(a, b)] — keep и speedup (с rate)."""
    out, t = [], 0.0
    for s in cl["segments"]:
        if s["action"] == "cut":
            continue
        d = (s["end"] - s["start"]) / (s.get("rate", 1) if s["action"] == "speedup" else 1)
        out.append((round(t, 3), round(t + d, 3)))
        t += d
    return out


def find_asset(library, asset_id):
    for e in (library or {}).get("assets", []):
        if e.get("id") == asset_id:
            return e
    return None


def source_path(item, library, library_dir, search_dirs=()):
    """Файл б-ролла: из библиотеки (files.mp4) или путь (абсолютный / в папках б-роллов)."""
    if item.get("asset"):
        e = find_asset(library, item["asset"])
        if not e:
            return None, None
        rel = (e.get("files") or {}).get("mp4")
        return (Path(library_dir) / rel if rel and library_dir else None), e
    if item.get("file"):
        p = Path(item["file"]).expanduser()
        if p.is_absolute():
            return p, None
        for d in search_dirs:
            if d and (Path(d) / p).exists():
                return Path(d) / p, None
        return p, None
    return None, None


def resolve(items, at, dur, library=None, library_dir=None, search_dirs=(), insert_len=(0.5, 1.8)):
    """→ (brolls, cards, missing, problems). problems: [{"level": "error"|"warn", "where", "text"}]"""
    brolls, cards, missing, problems = [], [], [], []
    for n, it in enumerate(items):
        kind = it.get("kind", "broll")
        if kind == "missing":
            missing.append({"t": at(it.get("at", 0.0)), "want": it.get("want", ""), "anchor": it.get("at")})
            continue
        t0 = round(max(0.0, at(it["from"])), 3)
        t1 = round(min(dur, at(it["to"])), 3)
        where = f"#{n + 1} {t0:.2f}–{t1:.2f}"
        if t1 - t0 < 0.05:
            problems.append({"level": "error", "where": where, "text": "пустое окно: «до» раньше «от»"})
            continue
        if kind == "card":
            cards.append({**it, "a": t0, "b": t1, "n": n})
            continue
        rate = float(it.get("rate", 1))
        m0 = float(it.get("in", 0.0))
        m1 = m0 + (t1 - t0) * rate
        src, entry = source_path(it, library, library_dir, search_dirs)
        r = {**it, "a": t0, "b": t1, "rate": rate, "in": m0, "src_window": (round(m0, 3), round(m1, 3)),
             "path": src, "entry": entry, "layout": it.get("layout", "full"), "pos": it.get("pos", "50% 50%"),
             "n": n}
        brolls.append(r)
        lo, hi = insert_len
        if rate == 1 and not lo <= t1 - t0 <= hi:
            problems.append({"level": "warn", "where": where,
                             "text": f"вставка {t1 - t0:.2f} с — вне ориентира {lo}–{hi} с"})
        if it.get("asset") and entry is None:
            problems.append({"level": "error", "where": where, "text": f"нет ассета «{it['asset']}» в index.json"})
        if entry:
            for p in entry.get("private", []):
                if overlaps(m0, m1, float(p["from"]), float(p["to"])):
                    problems.append({"level": "error", "where": where,
                                     "text": f"приватное окно {p['from']}–{p['to']} с: {p.get('what', '')}"})
            for ta, tb in entry.get("transitions", []):
                if overlaps(m0, m1, float(ta), float(tb)):
                    problems.append({"level": "warn", "where": where,
                                     "text": f"кадр на переходе {ta}–{tb} с источника"})
            if entry.get("duration") and m1 > float(entry["duration"]) + 0.05:
                problems.append({"level": "error", "where": where,
                                 "text": f"окно источника до {m1:.2f} с, а ассет {entry['duration']} с"})
    brolls.sort(key=lambda r: r["a"])
    for x, y in zip(brolls, brolls[1:]):
        if overlaps(x["a"], x["b"], y["a"], y["b"]):
            problems.append({"level": "error", "where": f"{y['a']:.2f}",
                             "text": f"б-роллы #{x['n'] + 1} и #{y['n'] + 1} налезают друг на друга"})
    return brolls, cards, missing, problems


def half_windows(brolls, gap=0.05):
    """Окна раскладки half, соседние склеены: [[a, b]]."""
    merged = []
    for r in sorted((r for r in brolls if r["layout"] == "half"), key=lambda r: r["a"]):
        if merged and r["a"] - merged[-1][1] < gap:
            merged[-1][1] = r["b"]
        else:
            merged.append([r["a"], r["b"]])
    return merged


def coverage(brolls, dur):
    return sum(min(dur, r["b"]) - max(0.0, r["a"]) for r in brolls)
