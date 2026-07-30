#!/usr/bin/env python3
"""Подбор ступени кегля под объём контента. Только stdlib.

Кегль ходит по конечному числу ступеней, а не подгоняется плавно. Причина
не техническая: плавная подгонка даёт сорок разных размеров за год и убивает
узнаваемость ленты. Не влезло на минимальной — говорим автору, на сколько
резать, и не ужимаем молча.
"""
import argparse
import json
import math
import os
from pathlib import Path

import build_html
import render
import theme as theme_mod

# Один источник истины: какие кегли нужны лейауту. Живёт в build_html, потому
# что там же проверка «кегль не передан» — здесь только псевдоним.
SIZE_KEYS = build_html.SIZE_KEYS

# Ключ ступеней в теме под каждое имя переменной кегля.
STEP_KEY = {
    "заголовок": "обложка_заголовок",
    "подзаголовок": "обложка_подзаголовок",
    "тело": "тело",
    "тело_список": "тело_список",
    "cta": "cta",
}

# Грубая оценка «сколько символов в строке» — для подсказки, не для вёрстки.
CHARS_PER_LINE = 34


def sizes_for(data, layout, index):
    """Кегли для лейаута на ступени index (0 — самая крупная)."""
    return {name: theme_mod.steps(data, STEP_KEY[name])[index]
            for name in SIZE_KEYS[layout]}


def shortfall_chars(overflow_px, line_height_px, chars_per_line=CHARS_PER_LINE):
    """На сколько примерно символов резать текст.

    Считаем в целых строках: сократить полстроки нельзя, а автору нужна
    понятная цифра, а не точная.
    """
    if overflow_px <= 0 or line_height_px <= 0:
        return 0
    lines = math.ceil(overflow_px / line_height_px)
    return lines * chars_per_line


def step_count(data, layout):
    """Сколько ступеней доступно лейауту."""
    return len(theme_mod.steps(data, STEP_KEY[SIZE_KEYS[layout][0]]))


def fit_slide(slide, data, platform, base_dir, tmp_dir):
    """Спускается по ступеням, пока не влезет. Возвращает финальный HTML и отчёт."""
    layout = slide["лейаут"]
    fmt = data["формат"]
    tmp_dir = Path(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    result = None
    for index in range(step_count(data, layout)):
        sizes = sizes_for(data, layout, index)
        html_path = tmp_dir / f"{slide['№']:02d}.html"
        html_path.write_text(build_html.build(slide, data, platform, sizes, base_dir),
                             encoding="utf-8")

        measured = render.measure(html_path, fmt["ширина"], fmt["высота"])
        result = {"html": html_path, "ступень": index,
                  "переполнение": measured["overflow_px"],
                  "недобор_символов": shortfall_chars(measured["overflow_px"],
                                                      measured["line_height_px"])}
        if measured["overflow_px"] <= 0:
            return result
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slides_json")
    ap.add_argument("--theme", default=os.environ.get("THEME_PATH"))
    ap.add_argument("--tmp", default="/tmp/carousel-render")
    args = ap.parse_args()

    spec = json.loads(Path(args.slides_json).read_text(encoding="utf-8"))
    data = theme_mod.load(args.theme)
    base = Path(args.slides_json).parent
    for slide in spec["слайды"]:
        got = fit_slide(slide, data, spec["meta"]["площадка"], base, args.tmp)
        print(f"{slide['№']:02d} ступень={got['ступень']} "
              f"переполнение={got['переполнение']}px "
              f"недобор={got['недобор_символов']}")


if __name__ == "__main__":
    main()
