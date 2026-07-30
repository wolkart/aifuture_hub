#!/usr/bin/env python3
"""Доктор окружения carousel-render. Только stdlib.

Проверяет то, без чего рендер молча выдаст брак: Chrome, sips, читаемую тему
и наличие файлов шрифтов. Отсутствие шрифтов — самый коварный случай: Chrome
не падает, а рисует засечным фолбэком.
"""
import argparse
import os
import shutil
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
REQUIRED_FONTS = ("Oswald", "Montserrat")


def check_chrome():
    """Chrome на штатном месте?"""
    if Path(CHROME).exists():
        return True, CHROME
    return False, f"не найден по пути {CHROME}"


def check_sips():
    """sips есть в PATH? Нужен для ужатия 2× → 1×."""
    path = shutil.which("sips")
    return (True, path) if path else (False, "не найден в PATH (нужен macOS)")


def check_theme(theme_path):
    """THEME_PATH задан и файл существует?"""
    if not theme_path:
        return False, "THEME_PATH не задан в .env — скилл не знает, где твоя тема"
    p = Path(theme_path)
    if not p.exists():
        return False, f"файл темы не найден: {p}"
    return True, str(p)


def check_fonts(theme_dir):
    """Файлы шрифтов лежат в папке темы?

    В системе автора Oswald и Montserrat не установлены — они живут только
    в Figma. Поэтому единственный надёжный источник это файлы рядом с темой.
    """
    fonts_dir = Path(theme_dir) / "fonts"
    missing = [n for n in REQUIRED_FONTS
               if not list(fonts_dir.glob(f"{n}*.ttf")) + list(fonts_dir.glob(f"{n}*.otf"))]
    if missing:
        return False, ("нет файлов: " + ", ".join(missing)
                       + " — запусти scripts/fonts.py, он скачает их с Google Fonts")
    return True, str(fonts_dir)


def report(checks):
    """checks: [(название, ок, сообщение)] → человекочитаемый отчёт."""
    lines = []
    for name, ok, msg in checks:
        lines.append(f"{'✓' if ok else '✗'} {name}: {msg}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--theme", default=os.environ.get("THEME_PATH"))
    args = ap.parse_args()

    theme_ok, theme_msg = check_theme(args.theme)
    checks = [("Chrome", *check_chrome()), ("sips", *check_sips()),
              ("Тема", theme_ok, theme_msg)]
    if theme_ok:
        checks.append(("Шрифты", *check_fonts(Path(args.theme).parent)))

    print(report(checks))
    raise SystemExit(0 if all(ok for _, ok, _ in checks) else 1)


if __name__ == "__main__":
    main()
