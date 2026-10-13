#!/usr/bin/env python3
"""plan.json → PLAN.md: таблица, которую автор смотрит перед рендером. Только stdlib.

Одна хронология без дыр: каждый момент ролика — либо вставка (б-ролл, ассет, карточка,
текст за головой), либо «спикер» с наездом этого куска. Колонки: время / слово / что
появляется / раскладка / наезд. Ниже — ошибки (рендер с ними не соберётся) и
предупреждения (ориентиры), затем строки «нет ассета → карточка или motion-assets».

Шлюз: PLAN.md показывается автору, рендер — только после его «ок».

usage: plan_md.py <папка варианта> [--settings reel.settings.json] [--library <папка>]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import behind as behind_mod  # noqa: E402
import captions  # noqa: E402
import hf  # noqa: E402
import inserts as ins  # noqa: E402
import settings as settings_mod  # noqa: E402
import words as wmod  # noqa: E402
import zoom  # noqa: E402
from layout import Build  # noqa: E402

TEMPLATE_NAMES = {"tiles": "плитки", "terminal": "терминал", "profile": "профиль", "chips": "чипы",
                  "rewrite": "было→стало", "rows": "строки-статусы", "compare": "сравнение",
                  "buttons": "кнопки", "cta": "CTA"}


def first_word(words, t):
    w = wmod.first_at_or_after(words, t, 0.3)
    return f"«{w['text'].strip(',.')}»" if w else "—"


def zoom_at(rows, t):
    r = next((r for r in rows if r["a"] - 1e-3 <= t < r["b"]), None)
    return r["kind"] if r else "—"


def what_broll(r):
    src = r.get("asset") or Path(str(r.get("file") or r.get("path") or "?")).name
    rate = f" ×{r['rate']:g}" if r["rate"] != 1 else ""
    note = f" — {r['note']}" if r.get("note") else ""
    return f"б-ролл {src} @{r['in']:.1f}{rate}{note}"


def what_card(c):
    slots = c.get("slots") or {}
    hint = slots.get("title") or slots.get("word") or slots.get("command") or ""
    name = TEMPLATE_NAMES.get(c["template"], c["template"])
    return f"карточка «{name}»" + (f": {hint}" if hint else "")


def gaps(covered, dur, min_len=0.3):
    """Участки, где на экране только спикер."""
    out, t = [], 0.0
    for a, b in sorted(covered):
        if a - t >= min_len:
            out.append((t, a))
        t = max(t, b)
    if dur - t >= min_len:
        out.append((t, dur))
    return out


def table(words, dur, brolls, cards, behind_res, zoom_rows):
    events = [(r["a"], r["b"], what_broll(r), r["layout"]) for r in brolls]
    events += [(c["a"], c["b"], what_card(c), "карточка") for c in cards]
    for w in behind_res:
        for ph in w["phrases"]:
            text = " / ".join(" ".join(x["text"] for x in ln["words"]) for ln in ph["lines"])
            events.append((ph["a"], ph["b"], f"текст за головой: {text}", "за головой"))
    for a, b in gaps([(a, b) for a, b, *_ in events], dur):
        events.append((a, b, "спикер", "—"))
    lines = ["| время | слово | что появляется | раскладка | наезд |", "|---|---|---|---|---|"]
    for a, b, what, layout in sorted(events, key=lambda e: (e[0], e[1])):
        lines.append(f"| {a:.2f}–{b:.2f} | {first_word(words, a)} | {what} | {layout} | {zoom_at(zoom_rows, a)} |")
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("variant")
    ap.add_argument("--settings", default=None)
    ap.add_argument("--library", default=None)
    args = ap.parse_args()

    b = Build(args.variant)
    plan = b.load_plan()
    s = (settings_mod.load(args.settings, plan.get("accent"), plan.get("captions"))
         or settings_mod.default())
    words = wmod.load(b.transcript)
    dur = round(hf.duration(b.roughcut) - 0.02, 2)
    at = lambda a: wmod.at(words, a)  # noqa: E731
    lib_dir = Path(args.library) if args.library else s["folders"]["library"]
    library = json.loads((lib_dir / "index.json").read_text(encoding="utf-8")) \
        if lib_dir and (lib_dir / "index.json").exists() else None
    search = [b.export.parent] + list(s["folders"]["brolls"])

    problems = []
    try:
        brolls, cards, missing, problems = ins.resolve(plan.get("items", []), at, dur, library, lib_dir,
                                                       search, s["edit"]["insert_len"])
        behind_res = behind_mod.resolve(plan.get("behind_text", []), at, dur)
    except KeyError as e:
        raise SystemExit(f"plan_md: якорь не найден в расшифровке — {e}")
    spans = ins.spans_from_cutlist(json.loads(b.cutlist.read_text())) if b.cutlist.exists() else [(0.0, dur)]
    rows = []
    if plan.get("zoom", True):
        faces = zoom.load_faces(b.faces) if b.faces.exists() else []
        plates = [[w["a"], w["b"]] for w in behind_res]
        rows = zoom.plan([(a, min(x, dur)) for a, x in spans if a < dur], words, plan.get("punch_words", []),
                         faces, plates, s["edit"]["zoom_levels"], s["edit"]["punch_add"], s["edit"]["punch_dur"])

    style = "по слову" if s["captions"]["style"] == "word" else "строки"
    flags = [f"субтитры: {style}", f"акцент: {s['theme']['accent']['name']}",
             f"наезды: {'да' if plan.get('zoom', True) else 'нет'}",
             f"музыка: {'да' if plan.get('music', True) else 'нет'}",
             f"текст за головой: {'да' if plan.get('behind_text') else 'нет'}"]
    out = [f"# План: {b.stem} — {b.name} ({plan.get('mode', 'full')})", "",
           f"Длина {dur:.1f} с · " + " · ".join(flags),
           f"Под вставками {ins.coverage(brolls, dur):.1f} с из {dur:.1f}; б-роллов {len(brolls)}, "
           f"карточек {len(cards)}", ""]
    if plan.get("accent_words"):
        out += ["Ударные слова субтитров: " + ", ".join(plan["accent_words"]), ""]
    if plan.get("punch_words"):
        out += ["«Вжух» на словах: " + ", ".join(plan["punch_words"]), ""]
    out += table(words, dur, brolls, cards, behind_res, rows)
    errors = [p for p in problems if p["level"] == "error"]
    warns = [p for p in problems if p["level"] == "warn"]
    if errors:
        out += ["", "## Ошибки — рендер не соберётся", ""] + [f"- ✗ {p['where']}: {p['text']}" for p in errors]
    if warns:
        out += ["", "## Предупреждения", ""] + [f"- ⚠ {p['where']}: {p['text']}" for p in warns]
    if missing:
        out += ["", "## Нет ассета", ""] + [
            f"- {m['t']:.2f} с {first_word(words, m['t'])}: {m['want']} → карточка или motion-assets"
            for m in missing]
    segs = captions.visible_segments(words, behind_mod.hidden_windows(behind_res))
    edges = behind_mod.edges(behind_res)
    units = (captions.word_beats(segs, dur, edges) if s["captions"]["style"] == "word"
             else captions.line_pages(segs, dur, edges))
    out += ["", f"## Субтитры ({len(units)})", "", "Текст на экране — проверь кодовое слово и термины:", ""]
    out += ["    " + line for line in captions.summary(units)]
    jumps = zoom.jumps(rows)
    small = [(i + 1, j) for i, j in enumerate(jumps) if j < 0.1 and not rows[i + 1]["plate"]]
    if small:
        out += ["", "⚠ склейки с перепадом масштаба < 0,1: " + ", ".join(f"#{i} ({j})" for i, j in small)]
    b.plan_md.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    print(f"\n→ {b.plan_md}\nок?")


if __name__ == "__main__":
    main()
