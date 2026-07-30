#!/usr/bin/env python3
"""Кладёт вариативные Oswald и Montserrat в папку темы. Только stdlib.

Оба под OFL, кириллица включена, вариативность закрывает все веса разом —
поэтому в теме вес задаётся числом, а не отдельным файлом на начертание.
"""
import argparse
import urllib.request
from pathlib import Path

FONT_URLS = {
    "Oswald": "https://github.com/google/fonts/raw/main/ofl/oswald/Oswald%5Bwght%5D.ttf",
    "Montserrat": "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf",
}


def missing_fonts(theme_dir):
    """Каких семейств нет в <тема>/fonts."""
    fonts_dir = Path(theme_dir) / "fonts"
    return [name for name in FONT_URLS
            if not list(fonts_dir.glob(f"{name}*.ttf"))]


def ensure_fonts(theme_dir, download=True):
    """Докачивает недостающие. Возвращает список тех, что были недостающими."""
    missing = missing_fonts(theme_dir)
    if not download:
        return missing
    fonts_dir = Path(theme_dir) / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    for name in missing:
        dest = fonts_dir / f"{name}.ttf"
        urllib.request.urlretrieve(FONT_URLS[name], dest)
    return missing


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("theme_dir")
    args = ap.parse_args()
    got = ensure_fonts(Path(args.theme_dir))
    print("скачано: " + ", ".join(got) if got else "все шрифты уже на месте")


if __name__ == "__main__":
    main()
