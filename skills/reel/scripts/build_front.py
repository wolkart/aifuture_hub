#!/usr/bin/env python3
"""Передний слой (субтитры + карточки) и задний («текст за головой») → проекты HyperFrames.

  <вариант>/front/index.html   — прозрачный слой ПЕРЕД человеком: карточки и субтитры;
  <вариант>/behind/index.html  — прозрачный слой ПОЗАДИ человека (только если в плане
                                 есть behind_text): подложка + крупный текст;
  <вариант>/windows.json       — окна подложек (маска человека нужна только в них).
Тайминги — из transcript.json (пословно, после подгонки к звуку), длительность — из файла.
Субтитры не дублируют текст за головой и поднимаются на стык на окнах half.

Без plan.json (режим subs) — только субтитры по настройкам.

usage: build_front.py <папка варианта> [--settings reel.settings.json]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import behind as behind_mod  # noqa: E402
import captions  # noqa: E402
import cards as cards_mod  # noqa: E402
import glyphs  # noqa: E402
import hf  # noqa: E402
import inserts as ins  # noqa: E402
import settings as settings_mod  # noqa: E402
import words as wmod  # noqa: E402
from layout import Build  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("variant")
    ap.add_argument("--settings", default=None)
    ap.add_argument("--allow-fallback", action="store_true",
                    help="собрать, даже если букв нет в шрифте темы (нарисуются чужим шрифтом)")
    args = ap.parse_args()

    b = Build(args.variant)
    plan = b.load_plan() if b.plan.exists() else {"mode": "subs"}
    s = (settings_mod.load(args.settings, plan.get("accent"), plan.get("captions"))
         or settings_mod.default())
    theme = s["theme"]
    words = wmod.load(b.transcript)
    dur = round(hf.duration(b.roughcut) - 0.02, 2)  # длина ролика = длина черновика
    at = lambda a: wmod.at(words, a)  # noqa: E731

    hidden, edges = [], []
    if plan.get("behind_text"):
        res = behind_mod.resolve(plan["behind_text"], at, dur)
        if b.cutlist.exists():   # окно текста не переживает склейку
            import json as _json
            behind_mod.clamp_to_spans(res, ins.spans_from_cutlist(_json.loads(b.cutlist.read_text())))
        css, body, js, windows = behind_mod.build(res, theme)
        fonts = hf.setup_project(b.behind, theme)
        (b.behind / "index.html").write_text(hf.page(css, "\n".join(body), "\n".join(js), dur, fonts),
                                            encoding="utf-8")
        b.write_json(b.windows, windows)
        hidden, edges = behind_mod.hidden_windows(res), behind_mod.edges(res)
        print(f"за головой: окна {windows}")

    brolls, card_items, _, problems = ins.resolve(plan.get("items", []), at, dur,
                                                 insert_len=s["edit"]["insert_len"])
    for p in problems:
        if "б-ролл" not in p["text"] and "ассет" not in p["text"]:
            print(f"{'✗' if p['level'] == 'error' else '⚠'} {p['where']}: {p['text']}")
    halves = ins.half_windows(brolls)
    c_files = []
    c_css, c_body, c_js = cards_mod.build(card_items, at, theme, files=c_files) if card_items else ("", [], [])
    c_hidden, c_keys = captions.plan_keys(plan, at, dur)
    shown = captions.insert_words(captions.replace_words(words, plan.get("captions_replace")),
                                  captions.plan_inserts(plan, at))
    s_css, s_body, s_js, units = captions.build(shown, dur, s["captions"], theme, hidden + c_hidden, edges, halves,
                                                plan.get("accent_words", []), c_keys)
    fonts = hf.setup_project(b.front, theme, extra=c_files)
    (b.front / "index.html").write_text(
        hf.page(c_css + s_css, "\n".join(c_body + s_body), "\n".join(c_js + s_js), dur, fonts),
        encoding="utf-8")

    style = {"word": "по слову", "caps": "капс"}.get(s["captions"]["style"], "строки")
    print(f"субтитры: {style}, акцент «{theme['accent']['name']}», единиц {len(units)}; карточек {len(card_items)}")
    for line in captions.summary_parts(shown, dur, s["captions"], hidden + c_hidden, edges, c_keys):
        print(line)
    if plan.get("behind_text"):
        print("рендер: " + " ".join(hf.render_cmd(b.behind, b.behind_webm, "webm")))
    bad = False
    for where, page in (("front", b.front / "index.html"), ("behind", b.behind / "index.html")):
        if where == "behind" and not plan.get("behind_text"):
            continue
        res = glyphs.check(page.read_text(encoding="utf-8"), theme["font_main"], theme["font_display"])
        for line in glyphs.report(res, where):
            print(line)
        bad = bad or bool(res["missing"])
    if bad and not args.allow_fallback:
        raise SystemExit("build_front: буквы не из шрифта темы — замени слово/символ или шрифт "
                         "(собрать как есть — --allow-fallback)")
    print("рендер: " + " ".join(hf.render_cmd(b.front, b.front_webm, "webm")))


if __name__ == "__main__":
    main()
