#!/usr/bin/env python3
"""Проверка перед показом автору: контакт-листы кадров готового ролика. Только stdlib + ffmpeg.

Кадр на каждую вставку и карточку (середина окна), первая и последняя секунды, 30 кадров
на окна маски — подписанные, сеткой. Агент смотрит листы глазами по чек-листу
(references/editing-rules.md, «Проверка») и чинит найденное ДО показа автору.
Перемотка -ss после -i: медленнее, зато кадр тот, что в ролике.

usage: check_frames.py <папка варианта> [--video export/….mp4] [--cols 4]
Выход: <вариант>/check/лист-01.png … (удаляются tidy.py после заморозки).
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hf  # noqa: E402
import inserts as ins  # noqa: E402
import settings as settings_mod  # noqa: E402
import words as wmod  # noqa: E402
from layout import Build  # noqa: E402

MATTE_SAMPLES = 30
# Безопасная зона Reels на 1080×1920: по высоте 360–1420 px, по ширине до 960 px —
# сверху заголовок и камера интерфейса, справа кнопки, снизу подпись и ник.
# Рисуется рамкой на каждом кадре листа: что вылезло за неё, интерфейс закроет.
SAFE = (0, 360, 960, 1420)
SAFE_BOX = (f"drawbox=x=iw*{SAFE[0]}/1080:y=ih*{SAFE[1]}/1920:w=iw*{SAFE[2] - SAFE[0]}/1080:"
            f"h=ih*{SAFE[3] - SAFE[1]}/1920:color=red@0.6:t=1")


def sample_times(brolls, cards, windows, dur, matte_n=MATTE_SAMPLES):
    """→ [(t, подпись)] по возрастанию: вставки, карточки, края ролика, окна маски."""
    out = [(0.3, "первая секунда"), (max(0.0, dur - 0.5), "последняя секунда")]
    for r in brolls:
        out.append((round((r["a"] + r["b"]) / 2, 3), f"б-ролл #{r['n'] + 1} {r['layout']}"))
    for c in cards:
        out.append((round((c["a"] + c["b"]) / 2, 3), f"карточка {c['template']}"))
    total = sum(b - a for a, b in windows)
    for a, b in windows:
        k = max(1, round(matte_n * (b - a) / total)) if total else 0
        for i in range(k):
            out.append((round(a + (b - a) * (i + 0.5) / k, 3), "маска"))
    return sorted(out)


def has_drawtext():
    """drawtext есть не в каждой сборке ffmpeg (Homebrew без freetype) — тогда без подписей."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    return " drawtext " in out


def esc_drawtext(text):
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("variant")
    ap.add_argument("--video", default=None)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--settings", default=None)
    args = ap.parse_args()
    b = Build(args.variant)
    plan = b.load_plan() if b.plan.exists() else {}
    s = settings_mod.load(args.settings) or settings_mod.default()
    video = Path(args.video) if args.video else max(b.final.glob(f"{b.stem} — *.mp4"),
                                                    key=lambda p: p.stat().st_mtime)
    dur = hf.duration(video)
    words = wmod.load(b.transcript)
    brolls, cards, _, _ = ins.resolve(plan.get("items", []), lambda a: wmod.at(words, a), dur)
    times = sample_times(brolls, cards, b.read_json(b.windows, []) if plan.get("behind_text") else [], dur)
    font = s["theme"]["font_main"]
    labels = has_drawtext()
    tmp = Path(tempfile.mkdtemp())
    for i, (t, label) in enumerate(times):
        vf = "scale=270:-2," + SAFE_BOX
        if labels and font and Path(font).exists():
            vf += (f",drawtext=fontfile='{font}':text='{esc_drawtext(f'{t:.2f} {label}')}':x=8:y=8:"
                   f"fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-ss", f"{t:.3f}", "-frames:v", "1",
                        "-vf", vf, str(tmp / f"f_{i:03d}.png")], check=True)
    out_dir = b.var / "check"
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir()
    per = args.cols * 3
    sheets = []
    for k in range(0, len(times), per):
        n = min(per, len(times) - k)
        sheet = out_dir / f"лист-{k // per + 1:02d}.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-start_number", str(k), "-i", str(tmp / "f_%03d.png"),
                        "-frames:v", "1", "-vf",
                        f"tile={args.cols}x{(n + args.cols - 1) // args.cols}:padding=6:color=0x202020",
                        str(sheet)], check=True)
        sheets.append(sheet)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"проверка: {len(times)} кадров на {len(sheets)} листах → {out_dir}"
          + ("" if labels else " (ffmpeg без drawtext — подписи ниже, ячейки слева направо, сверху вниз)"))
    for n, sh in enumerate(sheets):
        print(f"  {sh}")
        if not labels:
            chunk = times[n * per:(n + 1) * per]
            print("    " + " · ".join(f"{i + 1}) {t:.2f} {lbl}" for i, (t, lbl) in enumerate(chunk)))
    print("красная рамка — безопасная зона Reels (360–1420 по высоте, до 960 по ширине): "
          "текст и главное — внутри")
    print("чек-лист: не на переходе · объект целиком · субтитры не на лице · карточка не на б-ролле · "
          "нет мебели/ореола в маске · ничего приватного · текст = сценарий · края чистые")
    print(json.dumps([{"t": t, "что": lbl} for t, lbl in times], ensure_ascii=False))


if __name__ == "__main__":
    main()
