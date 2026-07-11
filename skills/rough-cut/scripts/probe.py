#!/usr/bin/env python3
"""ffprobe → компактный JSON о медиафайле. Только stdlib.

Учитывает поворот в метаданных (вертикальная съёмка камеры хранится как
1920×1080 + display-matrix rotation 90): в выдаче width/height — как кадр
реально показывается, а не как лежит в контейнере.
"""
import argparse
import json
import subprocess
from fractions import Fraction


def rotation_of(vstream):
    """Угол поворота видеопотока из ffprobe-словаря (side_data или tags.rotate)."""
    for sd in vstream.get("side_data_list", []):
        if sd.get("rotation") is not None:
            return int(sd["rotation"])
    tag = vstream.get("tags", {}).get("rotate")
    return int(tag) if tag is not None else 0


def oriented_dims(width, height, rotation):
    """Свап сторон при повороте на ±90/±270 (вертикаль ↔ горизонталь)."""
    return (height, width) if abs(rotation) % 180 == 90 else (width, height)


def parse_streams(data):
    info = {"duration_s": float(data["format"]["duration"]),
            "has_video": False, "has_audio": False}
    for st in data["streams"]:
        if st["codec_type"] == "video" and not info["has_video"]:
            fr = Fraction(st["r_frame_rate"])
            w, h = oriented_dims(st["width"], st["height"], rotation_of(st))
            info.update(has_video=True,
                        fps={"num": fr.numerator, "den": fr.denominator},
                        width=w, height=h)
        elif st["codec_type"] == "audio":
            info["has_audio"] = True
    return info


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, check=True).stdout
    info = {"path": str(path)}
    info.update(parse_streams(json.loads(out)))
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    print(json.dumps([probe(f) for f in args.files], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
