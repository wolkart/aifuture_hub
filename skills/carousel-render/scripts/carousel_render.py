#!/usr/bin/env python3
"""Оркестратор: slides.json + тема → папка PNG + простыня + отчёт.

Единственная точка входа скилла. Всё остальное — библиотеки, которые он
складывает в конвейер: тема → подбор ступени → съёмка → ужатие → простыня.
"""
import argparse
import json
import os
import tempfile
from pathlib import Path

import contact_sheet
import fit
import render
import theme as theme_mod


def output_dir(slides_json, env_dir, name):
    """Куда складывать. OUTPUT_DIR из .env, иначе рядом со slides.json."""
    base = Path(env_dir) if env_dir else Path(slides_json).parent
    return base / name


def run(slides_json, theme_path, out_dir=None):
    """Полный прогон карусели. Возвращает структуру для отчёта."""
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

    slides, pngs = [], []
    with tempfile.TemporaryDirectory(prefix="carousel-render-") as tmp:
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
    return {"папка": target, "слайды": slides, "простыня": sheet, "проблемы": problems}


def format_report(result):
    """Короткий отчёт автору. Без рассуждений."""
    lines = [f"Снято карточек: {len(result['слайды'])} → {result['папка']}"]
    if result.get("простыня"):
        lines.append(f"Простыня: {result['простыня']}")

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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slides_json")
    ap.add_argument("--theme", default=os.environ.get("THEME_PATH"))
    ap.add_argument("--out")
    args = ap.parse_args()
    if not args.theme:
        raise SystemExit("THEME_PATH не задан — запусти scripts/check_env.py")
    print(format_report(run(args.slides_json, args.theme, args.out)))


if __name__ == "__main__":
    main()
