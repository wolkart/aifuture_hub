#!/usr/bin/env python3
"""ffprobe → компактный JSON о медиафайле. Только stdlib."""
import argparse
import json
import subprocess
from fractions import Fraction


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    info = {"path": str(path),
            "duration_s": float(data["format"]["duration"]),
            "has_video": False, "has_audio": False}
    for st in data["streams"]:
        if st["codec_type"] == "video" and not info["has_video"]:
            fr = Fraction(st["r_frame_rate"])
            info.update(has_video=True,
                        fps={"num": fr.numerator, "den": fr.denominator},
                        width=st["width"], height=st["height"])
        elif st["codec_type"] == "audio":
            info["has_audio"] = True
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    print(json.dumps([probe(f) for f in args.files], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
