#!/usr/bin/env python3
"""Опись б-ролла, автоматическая часть: переходы + контакт-листы + заготовка записи. Только stdlib.

Опись — события, не темы: что появилось, что выделено, где клик, где объект виден
целиком (шаг 0,5 с) и где приватное (IP, ключи, токены, почты). События агент пишет
сам, глядя на листы; скрипт даёт ему глаза и то, что считается без глаз:

  • переходы — ffmpeg отдаёт серые кадры 10 к/с 108×192, средняя абсолютная разница
    соседних кадров > 4 → переход/наезд. Записи экрана с авто-зумом дают их пачками,
    поэтому окна ближе merge_gap сливаются. Вставки /reel ставит только между ними;
  • контакт-листы — кадры 2 к/с сеткой 5×4 (10 с на лист), таймкод в секундах на
    каждом кадре и диапазон в имени файла. Таймкод рисуется встроенным пиксельным
    шрифтом, не drawtext: у ffmpeg без freetype (Homebrew) drawtext нет вовсе;
  • точечный кадр — frame_at: перемотка -ss ПОСЛЕ -i (до -i кадр неточен).

  scan_broll.py <видео> --out <папка> [--id <id>] [--library <папка>]
  scan_broll.py <видео> --out <папка> --at 3.5 4.0      — только точечные кадры
"""
import argparse
import json
import operator
import struct
import subprocess
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

FPS, DW, DH, THR, MERGE_GAP = 10, 108, 192, 4.0, 0.2
SHEET_FPS, COLS, ROWS, GAP = 2, 5, 4, 4
CELL_PORTRAIT, CELL_LANDSCAPE = (216, 384), (384, 216)

# Пиксельный шрифт 5×7 для таймкодов: хватает цифр и точки.
GLYPHS = {
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
}


# ── ffprobe ──────────────────────────────────────────────────────────────────

def probe(video):
    """{"duration", "width", "height"} — стороны как кадр показывается (с учётом поворота)."""
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
                          "-show_format", str(video)], capture_output=True, text=True,
                         check=True).stdout
    data = json.loads(out)
    v = next(s for s in data["streams"] if s["codec_type"] == "video")
    rot = 0
    for sd in v.get("side_data_list", []):
        if sd.get("rotation") is not None:
            rot = int(sd["rotation"])
    w, h = v["width"], v["height"]
    if abs(rot) % 180 == 90:
        w, h = h, w
    return {"duration": float(data["format"]["duration"]), "width": w, "height": h}


# ── переходы ─────────────────────────────────────────────────────────────────

def raw_frames(video, vf, frame_bytes, pix_fmt="gray"):
    """Сырые кадры ffmpeg по одному (bytes) через фильтр vf. Поток, без записи на диск."""
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video),
                             "-vf", "setpts=PTS-STARTPTS," + vf,
                             "-f", "rawvideo", "-pix_fmt", pix_fmt, "-"],
                            stdout=subprocess.PIPE)
    try:
        while True:
            buf = proc.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break
            yield buf
    finally:
        proc.stdout.close()
        proc.wait()


def mean_abs_diff(a, b):
    return sum(map(abs, map(operator.sub, a, b))) / len(a)


def frame_diffs(frames):
    """diffs[i] — разница кадров i и i+1."""
    out, prev = [], None
    for f in frames:
        if prev is not None:
            out.append(mean_abs_diff(prev, f))
        prev = f
    return out


def transitions(diffs, fps=FPS, thr=THR, merge_gap=MERGE_GAP):
    """Окна движения [[a, b]] по разнице соседних кадров. diffs[i] > thr → движение между
    кадрами i и i+1, то есть [i/fps, (i+1)/fps]; окна с паузой ≤ merge_gap сливаются."""
    wins = []
    for i, d in enumerate(diffs):
        if d <= thr:
            continue
        a, b = i / fps, (i + 1) / fps
        if wins and a - wins[-1][1] <= merge_gap + 1e-9:
            wins[-1][1] = b
        else:
            wins.append([a, b])
    return [[round(a, 2), round(b, 2)] for a, b in wins]


def scan_transitions(video, thr=THR, merge_gap=MERGE_GAP):
    frames = raw_frames(video, f"fps={FPS},scale={DW}:{DH}", DW * DH)
    return transitions(frame_diffs(frames), FPS, thr, merge_gap)


# ── PNG и таймкоды без зависимостей ──────────────────────────────────────────

def write_png(path, w, h, rgb):
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    stride = w * 3
    raw = b"".join(b"\x00" + bytes(rgb[y * stride:(y + 1) * stride]) for y in range(h))
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n"
                           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def fill(buf, bw, x, y, w, h, color):
    row = bytes(color) * w
    for yy in range(y, y + h):
        i = (yy * bw + x) * 3
        buf[i:i + w * 3] = row


def draw_label(buf, bw, x, y, text, scale=4, pad=6):
    """Таймкод белым по чёрной плашке в точке (x, y) листа шириной bw."""
    adv = 6 * scale
    fill(buf, bw, x, y, len(text) * adv - scale + 2 * pad, 7 * scale + 2 * pad, (0, 0, 0))
    for k, ch in enumerate(text):
        for r, bits in enumerate(GLYPHS.get(ch, GLYPHS["-"])):
            for c, bit in enumerate(bits):
                if bit == "1":
                    fill(buf, bw, x + pad + k * adv + c * scale, y + pad + r * scale,
                         scale, scale, (255, 255, 255))


def cell_size(width, height):
    return CELL_PORTRAIT if height >= width else CELL_LANDSCAPE


def sheet_name(prefix, k, a, b):
    return f"{prefix}_sheet{k:02d}_{a:06.1f}-{b:06.1f}.png"


def compose_sheet(frames, times, cw, ch, cols=COLS, rows=ROWS, gap=GAP):
    """Кадры rgb24 cw×ch → лист сеткой cols×rows с таймкодом на каждом. → (w, h, bytes)."""
    sw, sh = cols * cw + (cols + 1) * gap, rows * ch + (rows + 1) * gap
    buf = bytearray(bytes((32, 32, 32)) * (sw * sh))
    for n, (fr, t) in enumerate(zip(frames, times)):
        x0 = gap + (n % cols) * (cw + gap)
        y0 = gap + (n // cols) * (ch + gap)
        for y in range(ch):
            i = ((y0 + y) * sw + x0) * 3
            buf[i:i + cw * 3] = fr[y * cw * 3:(y + 1) * cw * 3]
        draw_label(buf, sw, x0 + 4, y0 + 4, f"{t:.1f}")
    return sw, sh, buf


def contact_sheets(video, out_dir, prefix, width, height, fps=SHEET_FPS, cols=COLS, rows=ROWS):
    """Листы PNG по cols×rows кадров с шагом 1/fps. Возвращает пути."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cw, ch = cell_size(width, height)
    vf = (f"fps={fps},scale={cw}:{ch}:force_original_aspect_ratio=decrease,"
          f"pad={cw}:{ch}:(ow-iw)/2:(oh-ih)/2:color=0x202020")
    per = cols * rows
    paths, batch, n = [], [], 0

    def flush():
        times = [(n - len(batch) + j) / fps for j in range(len(batch))]
        sw, sh, buf = compose_sheet(batch, times, cw, ch, cols, rows)
        p = out_dir / sheet_name(prefix, len(paths) + 1, times[0], times[-1])
        write_png(p, sw, sh, buf)
        paths.append(p)

    for fr in raw_frames(video, vf, cw * ch * 3, "rgb24"):
        batch.append(fr)
        n += 1
        if len(batch) == per:
            flush()
            batch = []
    if batch:
        flush()
    return paths


def frame_at(video, t, out):
    """Точный кадр в момент t: -ss после -i (декодирует до места, а не прыгает по ключевым)."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-ss", f"{t:.3f}",
                    "-frames:v", "1", str(out)], check=True)
    return out


# ── заготовка записи ─────────────────────────────────────────────────────────

def draft_entry(id_, duration, trans, mp4_rel):
    """Запись index.json для б-ролла: события, приватное, теги и тему заполняет агент."""
    return {"id": id_, "kind": "broll", "layout": "full", "duration": round(duration, 2),
            "theme": "dark", "tags": [], "describes": "", "events": [],
            "transitions": trans, "private": [], "files": {"mp4": mp4_rel}}


def rel_to_library(video, id_, library):
    """Путь файла для files.mp4: относительно библиотеки, если файл уже в ней."""
    v = Path(video).resolve()
    if library:
        try:
            return str(v.relative_to(Path(library).resolve()))
        except ValueError:
            pass
    return f"{id_}/{v.name}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out", required=True, help="папка для листов, кадров и заготовки")
    ap.add_argument("--id", help="id ассета (по умолчанию — имя файла)")
    ap.add_argument("--library", help="папка библиотеки (для относительного пути в files)")
    ap.add_argument("--at", type=float, nargs="+", help="только точечные кадры в эти моменты")
    ap.add_argument("--thr", type=float, default=THR)
    ap.add_argument("--merge-gap", type=float, default=MERGE_GAP)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    video, out = Path(args.video), Path(args.out)
    id_ = args.id or video.stem
    if args.at:
        paths = [frame_at(video, t, out / f"{id_}_t{t:07.2f}.png") for t in args.at]
        print("\n".join(str(p) for p in paths))
        return 0

    import library
    info = probe(video)
    trans = scan_transitions(video, args.thr, args.merge_gap)
    sheets = contact_sheets(video, out, id_, info["width"], info["height"])
    entry = draft_entry(id_, info["duration"], trans, rel_to_library(video, id_, args.library))
    draft = out / f"{id_}.entry.json"
    draft.write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    windows = library.usable_windows(entry, min_len=0.5)
    if args.json:
        print(json.dumps({"transitions": trans, "usable": windows,
                          "sheets": [str(p) for p in sheets], "draft": str(draft),
                          "entry": entry}, ensure_ascii=False, indent=2))
        return 0
    print(f"Видео: {video} — {info['width']}×{info['height']}, {info['duration']:.2f} с")
    print(f"Переходы ({len(trans)}): " + (", ".join(f"{a}–{b}" for a, b in trans) or "нет"))
    print("Стоячие окна ≥ 0,5 с: " + (", ".join(f"{a}–{b}" for a, b in windows) or "нет"))
    print(f"Контакт-листы ({len(sheets)}, 2 к/с, 10 с на лист):")
    for p in sheets:
        print(f"  {p}")
    print(f"Заготовка записи: {draft}")
    print("  дальше: events с шагом 0,5 с (появилось / выделено / клик / виден целиком),\n"
          "  private — IP, ключи, токены, почты; theme — тёмный/светлый интерфейс; tags.\n"
          "  точный кадр: scan_broll.py <видео> --out <папка> --at <t>\n"
          "  в индекс: library.py add <заготовка>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
