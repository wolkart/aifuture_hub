#!/usr/bin/env python3
"""Режим thumbs: превью → текст → срез признаков. Только stdlib.

Превью НЕ хранятся: качаются во временную папку, после OCR удаляются.
В базу идёт распознанный текст и thumbnail_url, не файл.

OCR — Apple Vision через ocr-cards.sh, только macOS. Нет условий —
режим честно отказывается, остальные режимы скилла работают.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import thumb_text

WORKERS = 8
OCR_SCRIPT = Path(__file__).parent / "ocr-cards.sh"


def ocr_available(platform=None, which=None):
    platform = platform if platform is not None else sys.platform
    which = which or shutil.which
    return platform == "darwin" and bool(which("swiftc"))


def _default_fetcher(url, path):
    urllib.request.urlretrieve(url, path)


def download_all(videos, out_dir, fetcher=None):
    """Качает превью параллельно. Упавшие пропускаются, остальные собираются."""
    fetcher = fetcher or _default_fetcher
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = [v for v in videos if v.get("thumbnail_url")]

    def one(v):
        path = out_dir / (v["id"] + ".jpg")
        try:
            fetcher(v["thumbnail_url"], str(path))
            return v["id"]
        except Exception:
            return None

    done = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for got in pool.map(one, targets):
            if got:
                done.append(got)
    return done


def _default_ocr(paths):
    result = subprocess.run(["bash", str(OCR_SCRIPT)] + [str(p) for p in paths],
                            capture_output=True, text=True, check=False)
    return result.stdout


def build(data, ocr_runner=None, fetcher=None, work_dir=None):
    videos = data["videos"]
    total = len(videos)
    if ocr_runner is None and not ocr_available():
        return {"slices": {}, "texts": {}, "covered": 0, "total": total,
                "skipped": "OCR недоступен: нужен macOS и swiftc "
                           "(xcode-select --install)"}

    ocr_runner = ocr_runner or _default_ocr
    tmp = Path(work_dir) if work_dir else Path(tempfile.mkdtemp())
    ids = download_all(videos, tmp, fetcher)
    paths = [tmp / (i + ".jpg") for i in ids]

    raw = ocr_runner(paths) if paths else ""
    blocks = thumb_text.parse_ocr_output(raw)

    for p in paths:
        try:
            p.unlink()
        except OSError:
            pass

    records = {v["id"]: v for v in videos}
    return {
        "slices": thumb_text.slice_by_feature(records, blocks),
        "texts": {k: " ".join(v) for k, v in blocks.items() if v},
        "covered": sum(1 for v in blocks.values() if v),
        "total": total,
        "skipped": "",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="текст на превью канала")
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    data = json.loads(Path(args.src).read_text(encoding="utf-8"))
    result = build(data)
    Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"covered": result["covered"], "total": result["total"],
                      "skipped": result["skipped"], "out": args.out},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
