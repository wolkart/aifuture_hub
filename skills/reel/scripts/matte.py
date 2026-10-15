#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["torch", "torchvision", "pillow", "numpy"]
# ///
"""Маска человека для «текста за головой» — RobustVideoMatting, только в окнах подложек.

Почему RVM: u2net (из HyperFrames) захватывает кресло и кусок торшера, Apple Vision —
почти без мебели, но только macOS; RVM — без мебели, стабильна во времени (рекуррентная
память), CPU/MPS, любая ОС. ~3 мин на 10 с на Apple Silicon.

Выход — сплошная последовательность <вариант>/matte/f_00001.png … на всю длину ролика:
вне окон — ссылки на один прозрачный кадр (ffmpeg не умеет дыры в последовательности).
Первый кадр окна — ceil(t·fps)+1, а не round: иначе берётся хвост прошлого куска.
Перед окном 0,5 с «разогрева» памяти модели. Кадры удаляются после вшивания (tidy.py).

usage: uv run matte.py <папка варианта>
"""
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

FPS = 30
WARM = 15   # кадров разогрева памяти модели
TAIL = 3


def frame_ranges(windows, fps=FPS, warm=WARM, tail=TAIL):
    """Окна [[a, b]] с → [(первый кадр с разогревом, первый кадр окна, последний)] (нумерация с 1)."""
    out = []
    for a, b in windows:
        first = math.ceil(a * fps) + 1
        out.append((max(1, first - warm), first, int(b * fps) + tail))
    return out


def extract_cmd(src, f0, f1, out_pattern, fps=FPS):
    """Кадры f0…f1 на сетке fps ролика. Черновик бывает 50 к/с (камера), а маска и слои — 30:
    без fps-фильтра подряд идущие кадры 50 к/с нумеруются как 30 к/с, и вырезанный человек
    плывёт медленнее звука (за 4 с окна отстаёт на 1,5 с). -ss после -i: кадр точный."""
    return ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ss", f"{(f0 - 1) / fps:.4f}",
            "-vf", f"fps={fps}", "-frames:v", str(f1 - f0 + 1), "-start_number", str(f0), str(out_pattern)]


def gaps(produced, total):
    """Номера кадров 1..total, которых нет среди готовых — их заполнят ссылки на пустой кадр."""
    have = set(produced)
    return [n for n in range(1, total + 1) if n not in have]


def main():
    import numpy as np
    import torch
    from PIL import Image
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import hf
    from layout import Build

    b = Build(sys.argv[1])
    windows = json.loads(b.windows.read_text())
    total = int(hf.duration(b.roughcut) * FPS)
    b.matte.mkdir(exist_ok=True)
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    model = torch.hub.load("PeterL1n/RobustVideoMatting", "mobilenetv3", trust_repo=True).eval().to(dev)
    produced, w, h = [], None, None
    with torch.no_grad():
        for f0, _first, f1 in frame_ranges(windows):
            tmp = Path(tempfile.mkdtemp())
            subprocess.run(extract_cmd(b.roughcut, f0, f1, tmp / "f_%05d.png"), check=True)
            rec = [None] * 4
            for n in range(f0, f1 + 1):
                p = tmp / f"f_{n:05d}.png"
                if not p.exists():
                    break
                img = np.asarray(Image.open(p).convert("RGB"))
                h, w = img.shape[:2]
                src = torch.from_numpy(img).permute(2, 0, 1)[None].float().div(255).to(dev)
                _fgr, pha, *rec = model(src, *rec, downsample_ratio=0.25)
                alpha = (pha[0, 0].clamp(0, 1).cpu().numpy() * 255).astype(np.uint8)
                Image.fromarray(np.dstack([img, alpha])).save(b.matte / p.name)
                produced.append(n)
    blank = b.matte / "blank.png"
    Image.new("RGBA", (w or 1080, h or 1920), (0, 0, 0, 0)).save(blank)
    for n in gaps(produced, total):
        link = b.matte / f"f_{n:05d}.png"
        if not link.exists():
            link.symlink_to(blank.name)
    print(f"маска: {len(produced)} кадров RVM ({dev}), всего в последовательности {total} → {b.matte}")


if __name__ == "__main__":
    main()
