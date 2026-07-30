#!/usr/bin/env python3
"""Оркестратор: slides.json + тема → папка PNG + простыня + отчёт.

Единственная точка входа скилла. Всё остальное — библиотеки, которые он
складывает в конвейер: тема → подбор ступени → съёмка → ужатие → простыня.
"""
import argparse
import json
import os
import tempfile
from contextlib import nullcontext
from pathlib import Path

import contact_sheet
import envfile
import fit
import render
import theme as theme_mod


def output_dir(slides_json, env_dir, name):
    """Куда складывать. OUTPUT_DIR из .env, иначе рядом со slides.json."""
    base = Path(env_dir) if env_dir else Path(slides_json).parent
    return base / name


PREVIEW_CELL = 460


def preview_page(html_names, card_w, card_h, cols=3):
    """Страница со всеми карточками живьём, через iframe.

    Карточки уже самодостаточны, поэтому показывать их можно как есть —
    в масштабе. Это не картинка: можно открыть девтулзы и потрогать вёрстку,
    прежде чем менять значение в теме.
    """
    scale = PREVIEW_CELL / card_w
    cells = []
    for name in html_names:
        cells.append(
            f'<figure><div class="рамка">'
            f'<iframe src="_html/{name}" scrolling="no"></iframe>'
            f'</div><figcaption><a href="_html/{name}">{Path(name).stem}</a>'
            "</figcaption></figure>"
        )
    return (
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'>"
        "<title>Превью карусели</title><style>"
        "*{margin:0;padding:0;box-sizing:border-box}"
        "body{background:#17171b;color:#aaa;padding:24px;"
        "font:14px -apple-system,sans-serif}"
        "h1{font-size:16px;padding-bottom:16px}"
        f".сетка{{display:grid;grid-template-columns:repeat({cols},{PREVIEW_CELL}px);gap:20px}}"
        "figure{background:#222228;padding:8px;border-radius:8px}"
        f".рамка{{width:{PREVIEW_CELL}px;height:{round(card_h * scale)}px;"
        "overflow:hidden;border-radius:4px}"
        f"iframe{{width:{card_w}px;height:{card_h}px;border:0;"
        f"transform:scale({scale:.6f});transform-origin:0 0}}"
        "figcaption{text-align:center;padding-top:8px}"
        "figcaption a{color:#8ab;text-decoration:none}"
        "</style></head><body>"
        "<h1>Превью — живой HTML. Клик по номеру открывает карточку "
        "в полном размере; девтулзами можно пощупать вёрстку.</h1>"
        "<div class='сетка'>" + "".join(cells) + "</div></body></html>"
    )


def run(slides_json, theme_path, out_dir=None, preview=False):
    """Полный прогон карусели. Возвращает структуру для отчёта.

    preview=True сохраняет промежуточный HTML рядом с PNG и собирает
    страницу превью — обычно этот HTML живёт во временной папке и удаляется.
    """
    slides_json = Path(slides_json)
    spec = json.loads(slides_json.read_text(encoding="utf-8"))
    data = theme_mod.load(theme_path)

    problems = theme_mod.validate(data)
    name = spec["meta"]["название"]
    platform = spec["meta"]["площадка"]
    fmt = data["формат"]

    target = Path(out_dir) if out_dir else output_dir(
        slides_json, os.environ.get("OUTPUT_DIR"), name)
    target.mkdir(parents=True, exist_ok=True)

    html_dir = target / "_html"
    if preview:
        html_dir.mkdir(parents=True, exist_ok=True)

    slides, pngs = [], []
    keeper = (nullcontext(str(html_dir)) if preview
              else tempfile.TemporaryDirectory(prefix="carousel-render-"))
    with keeper as tmp:
        for slide in spec["слайды"]:
            fitted = fit.fit_slide(slide, data, platform, slides_json.parent, tmp)
            png = target / f"{slide['№']:02d}.png"
            render.screenshot(fitted["html"], png, fmt["ширина"], fmt["высота"],
                              fmt["масштаб_рендера"])
            render.downscale(png, fmt["ширина"], fmt["высота"])
            pngs.append(png)
            slides.append({"№": slide["№"], "png": png, "ступень": fitted["ступень"],
                           "переполнение": fitted["переполнение"],
                           "недобор_символов": fitted["недобор_символов"]})

    sheet = (contact_sheet.build_sheet(pngs, target / "contact-sheet.png",
                                       card_w=fmt["ширина"], card_h=fmt["высота"])
             if pngs else None)

    page = None
    if preview and slides:
        page = target / "превью.html"
        names = sorted(f.name for f in html_dir.glob("*.html"))
        page.write_text(preview_page(names, fmt["ширина"], fmt["высота"]),
                        encoding="utf-8")

    return {"папка": target, "слайды": slides, "простыня": sheet,
            "превью": page, "проблемы": problems}


def format_report(result):
    """Короткий отчёт автору. Без рассуждений."""
    lines = [f"Снято карточек: {len(result['слайды'])} → {result['папка']}"]
    if result.get("простыня"):
        lines.append(f"Простыня: {result['простыня']}")
    if result.get("превью"):
        lines.append(f"Превью (живой HTML): {result['превью']}")

    for s in result["слайды"]:
        if s["ступень"] > 0 and not s["переполнение"]:
            lines.append(f"слайд {s['№']}: кегль опущен на ступень {s['ступень']}")

    for s in result["слайды"]:
        if s["переполнение"] > 0:
            lines.append(f"слайд {s['№']}: не влезает даже на минимальной ступени — "
                         f"сократи примерно на {s['недобор_символов']} символов")

    for p in result.get("проблемы", []):
        lines.append(f"проблема темы: {p}")
    return "\n".join(lines)


def main():
    envfile.load()  # до разбора аргументов: дефолты берутся из окружения
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slides_json")
    ap.add_argument("--theme", default=os.environ.get("THEME_PATH"))
    ap.add_argument("--out")
    # Два имени: кириллица под стиль скилла, латиница чтобы набирать в терминале.
    ap.add_argument("--превью", "--preview", dest="preview", action="store_true",
                    help="сохранить HTML карточек и собрать страницу превью")
    args = ap.parse_args()
    if not args.theme:
        raise SystemExit("THEME_PATH не задан — запусти scripts/check_env.py")
    print(format_report(run(args.slides_json, args.theme, args.out, args.preview)))


if __name__ == "__main__":
    main()
