#!/usr/bin/env python3
"""Простыня из всех слайдов одной картинкой. Только stdlib.

Сетку рисует тот же Chrome, что и карточки: PNG встраиваются как data: URI,
поэтому сторонняя графическая библиотека не нужна.
"""
import argparse
from pathlib import Path

import build_html
import render

CELL_W = 360
GAP = 20
CAPTION_H = 46


def build_sheet_html(pngs, cols=3):
    """HTML-сетка со встроенными PNG."""
    cells = []
    for png in pngs:
        cells.append(
            f'<figure><img src="{build_html.data_uri(png)}" alt="">'
            f"<figcaption>{Path(png).stem}</figcaption></figure>"
        )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        "*{margin:0;padding:0;box-sizing:border-box}"
        f"body{{background:#f2f2f4;padding:{GAP}px;"
        "font:14px -apple-system,Helvetica,sans-serif}"
        f".сетка{{display:grid;grid-template-columns:repeat({cols},{CELL_W}px);gap:{GAP}px}}"
        "figure{background:#fff;padding:8px;border-radius:6px}"
        "img{width:100%;display:block;border-radius:3px}"
        "figcaption{text-align:center;padding-top:6px;color:#666}"
        "</style></head><body><div class='сетка'>"
        + "".join(cells)
        + "</div></body></html>"
    )


def sheet_size(count, cols, card_w, card_h):
    """Размер полотна под count карточек в cols колонок."""
    rows = (count + cols - 1) // cols
    width = cols * CELL_W + (cols + 1) * GAP + 8
    cell_h = round(CELL_W * card_h / card_w) + CAPTION_H
    height = rows * cell_h + (rows + 1) * GAP + 8
    return width, height


def build_sheet(pngs, out, cols=3, card_w=1080, card_h=1350):
    """Снимает простыню в PNG. Высота считается по числу рядов."""
    out = Path(out)
    html_path = out.with_suffix(".html")
    html_path.write_text(build_sheet_html(pngs, cols), encoding="utf-8")

    width, height = sheet_size(len(pngs), cols, card_w, card_h)
    render.screenshot(html_path, out, width, height, 1)
    html_path.unlink()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pngs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=3)
    args = ap.parse_args()
    print(build_sheet([Path(p) for p in args.pngs], args.out, args.cols))


if __name__ == "__main__":
    main()
