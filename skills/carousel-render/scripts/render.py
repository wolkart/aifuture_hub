#!/usr/bin/env python3
"""HTML → PNG через headless Chrome, плюс замер переполнения. Только stdlib.

Два прохода. Замер (`--dump-dom`) идёт в 1× и читает то, что страница сама
записала в data-атрибуты body. Съёмка (`--screenshot`) идёт в 2× ради
чистоты текста, затем `sips` ужимает до 1080×1350.
"""
import argparse
import re
import struct
import subprocess
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
VIRTUAL_TIME_MS = 2000

OVERFLOW_RE = re.compile(r'data-overflow="(\d+)"')
OVERFLOW_X_RE = re.compile(r'data-overflow-x="(\d+)"')
LINE_HEIGHT_RE = re.compile(r'data-line-height="(\d+)"')


def chrome_cmd(html_path, mode, width, height, scale, out):
    """Команда Chrome. mode: 'screenshot' | 'dom'.

    Профиль — общий, по умолчанию. Свой `--user-data-dir` на запуск выглядит
    правильнее для параллельной съёмки, но на Chrome 150 headless свежий
    профиль вешает процесс наглухо (проверено: >40 с без вывода, с
    `--no-first-run` тоже). Общий профиль параллель переносит: шесть запусков
    рядом — 4.4 с против 13 с по очереди.
    """
    cmd = [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
           f"--window-size={width},{height}",
           f"--force-device-scale-factor={scale if mode == 'screenshot' else 1}",
           f"--virtual-time-budget={VIRTUAL_TIME_MS}"]
    if mode == "screenshot":
        cmd.append(f"--screenshot={out}")
    else:
        cmd.append("--dump-dom")
    cmd.append(Path(html_path).resolve().as_uri())
    return cmd


def parse_overflow(dom):
    """Достаёт замеры, которые страница положила в data-атрибуты."""
    over = OVERFLOW_RE.search(dom)
    over_x = OVERFLOW_X_RE.search(dom)
    line = LINE_HEIGHT_RE.search(dom)
    return {"overflow_px": int(over.group(1)) if over else 0,
            "overflow_x_px": int(over_x.group(1)) if over_x else 0,
            "line_height_px": int(line.group(1)) if line else 0}


def measure(html_path, width, height):
    """Прогоняет страницу и возвращает переполнение в пикселях."""
    out = subprocess.run(chrome_cmd(html_path, "dom", width, height, 1, None),
                         capture_output=True, text=True, check=True).stdout
    return parse_overflow(out)


def screenshot(html_path, out_png, width, height, scale):
    """Снимает карточку в scale×. Возвращает путь к PNG."""
    subprocess.run(chrome_cmd(html_path, "screenshot", width, height, scale, out_png),
                   capture_output=True, check=True)
    return Path(out_png)


def downscale(png, width, height):
    """Ужимает до целевого размера. sips принимает высоту, потом ширину."""
    subprocess.run(["sips", "-z", str(height), str(width), str(png)],
                   capture_output=True, check=True)
    return Path(png)


def png_size(png):
    """Ширина и высота PNG из заголовка IHDR. Без сторонних библиотек."""
    data = Path(png).read_bytes()[16:24]
    return struct.unpack(">II", data)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html")
    ap.add_argument("--out")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1350)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--measure", action="store_true")
    args = ap.parse_args()

    if args.measure:
        print(measure(args.html, args.width, args.height))
        return
    png = screenshot(args.html, args.out, args.width, args.height, args.scale)
    downscale(png, args.width, args.height)
    print(f"{png} {png_size(png)}")


if __name__ == "__main__":
    main()
