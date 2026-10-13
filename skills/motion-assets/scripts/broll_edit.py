#!/usr/bin/env python3
"""Обработка своего б-ролла ffmpeg-ом в НОВЫЙ файл библиотеки; оригинал не трогается. Только stdlib.

Операции (одна команда ffmpeg, один проход кодирования):
  1. размытие приватного — прямоугольники на окнах времени: split → crop → boxblur →
     overlay с enable='between(t,a,b)'. Делается первым, по кадру оригинала;
  2. кадрирование в 9:16 с фокусом по x (доля ширины) → 1080×1920;
  3. наезд на точку на отрезке — scale с eval=frame + crop. Не zoompan: тот округляет
     позицию до пикселя на каждом кадре и дрожит. Точка остаётся на своём месте экрана,
     вокруг всё растёт; вход и выход плавные (smoothstep за ramp секунд);
  4. ускорение пустых участков [a, b, скорость] — trim/setpts/concat, fps выравнивается.

Все координаты и времена — в кадре и времени ОРИГИНАЛА (как на контакт-листах
scan_broll.py): x, y, w, h — доли кадра 0…1, времена — секунды. Пересчёт в кадр после
кадрирования — здесь. Звук отбрасывается (б-ролл немой). После ускорения таймкоды
съезжают: опись (scan_broll.py) делается по готовому файлу из библиотеки.

  broll_edit.py <видео> --out <файл.mp4> | --id <id> [--library <папка>]
      [--focus-x 0.5] [--zoom t0,t1,cx,cy,масштаб[,ramp]]… [--blur x,y,w,h,from,to]…
      [--speed a,b,скорость]… [--print] [--force]
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT_W, OUT_H, OUT_FPS = 1080, 1920, 30


def _even(x):
    return max(2, int(round(x / 2.0)) * 2)


def crop_rect(src_w, src_h, focus_x=0.5, focus_y=0.5, out_w=OUT_W, out_h=OUT_H):
    """Самый большой прямоугольник с пропорцией out_w:out_h внутри кадра, центр — в фокусе
    (доли кадра), прижатый к краям. → (w, h, x, y) в пикселях оригинала, чётные."""
    aspect = out_w / out_h
    if src_w / src_h > aspect:      # шире цели: режем бока
        h = src_h - src_h % 2
        w = min(_even(h * aspect), src_w - src_w % 2)
    else:                           # уже или ровно: режем верх/низ
        w = src_w - src_w % 2
        h = min(_even(w / aspect), src_h - src_h % 2)
    x = int(round(min(max(focus_x * src_w - w / 2, 0), src_w - w)))
    y = int(round(min(max(focus_y * src_h - h / 2, 0), src_h - h)))
    return w, h, x, y


def crop_chain(rect, out_w=OUT_W, out_h=OUT_H):
    w, h, x, y = rect
    return f"crop={w}:{h}:{x}:{y},scale={out_w}:{out_h}:flags=lanczos,setsar=1"


def ease_expr(t0, t1, ramp):
    """Выражение ffmpeg 0→1→0: плавный вход за ramp с t0, плавный выход к t1 (smoothstep)."""
    a = f"clip((t-{t0:.3f})/{ramp:.3f},0,1)"
    b = f"clip((t-{t1 - ramp:.3f})/{ramp:.3f},0,1)"
    return f"({a}*{a}*(3-2*{a})-{b}*{b}*(3-2*{b}))"


def zoom_chain(t0, t1, cx, cy, scale, ramp=0.4, w=OUT_W, h=OUT_H):
    """Наезд в scale раз на точку (cx, cy — доли кадра) на [t0, t1]. Кадр растёт по времени
    (scale с eval=frame), crop постоянного размера держит точку на месте: x = (iw-w)·cx."""
    ramp = max(0.05, min(ramp, (t1 - t0) / 2))
    z = f"(1+{scale - 1:.4f}*{ease_expr(t0, t1, ramp)})"
    return (f"scale=w='trunc({w}*{z}/2)*2':h='trunc({h}*{z}/2)*2':eval=frame:flags=bicubic,"
            f"crop={w}:{h}:'(iw-{w})*{cx:.4f}':'(ih-{h})*{cy:.4f}'")


def blur_graph(boxes, src_w, src_h, src="0:v", out="vb"):
    """Размытие прямоугольников на окнах времени. boxes: [{x, y, w, h, from, to}] — доли
    кадра и секунды. Кусок вырезается из копии потока, размывается и кладётся сверху
    только между from и to."""
    n = len(boxes)
    parts = [f"[{src}]split={n + 1}[bb0]" + "".join(f"[bs{i}]" for i in range(n))]
    for i, b in enumerate(boxes):
        bw, bh = _even(b["w"] * src_w), _even(b["h"] * src_h)
        bx, by = int(b["x"] * src_w), int(b["y"] * src_h)
        # радиус < половины стороны; у хромы плоскость вдвое меньше — < четверти
        side = min(bw, bh)
        lr, cr = max(0, min(30, side // 2 - 1)), max(0, min(15, side // 4 - 1))
        parts.append(f"[bs{i}]crop={bw}:{bh}:{bx}:{by},"
                     f"boxblur=lr={lr}:lp=3:cr={cr}:cp=3[bl{i}]")
    cur = "bb0"
    for i, b in enumerate(boxes):
        nxt = out if i == n - 1 else f"bb{i + 1}"
        bx, by = int(b["x"] * src_w), int(b["y"] * src_h)
        parts.append(f"[{cur}][bl{i}]overlay={bx}:{by}:"
                     f"enable='between(t,{b['from']:.3f},{b['to']:.3f})'[{nxt}]")
        cur = nxt
    return ";".join(parts)


def speed_pieces(segments, duration):
    """[[a, b, скорость]] → сплошная раскладка [(a, b, скорость)] на 0…duration."""
    pieces, pos = [], 0.0
    for a, b, rate in sorted(segments):
        a, b = max(a, pos), min(b, duration)
        if b <= a:
            continue
        if a > pos:
            pieces.append((pos, a, 1.0))
        pieces.append((a, b, float(rate)))
        pos = b
    if pos < duration:
        pieces.append((pos, duration, 1.0))
    return pieces


def speed_graph(segments, duration, src="vc", out="vout", fps=OUT_FPS):
    pieces = speed_pieces(segments, duration)
    n = len(pieces)
    parts = [f"[{src}]split={n}" + "".join(f"[sp{i}]" for i in range(n))]
    for i, (a, b, rate) in enumerate(pieces):
        pts = "PTS-STARTPTS" if rate == 1.0 else f"(PTS-STARTPTS)/{rate:g}"
        parts.append(f"[sp{i}]trim=start={a:.3f}:end={b:.3f},setpts={pts}[sq{i}]")
    parts.append("".join(f"[sq{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,fps={fps}[{out}]")
    return ";".join(parts)


def map_point(cx, cy, rect, src_w, src_h):
    """Точка в долях оригинала → доли кадра после кадрирования (прижата к 0…1)."""
    w, h, x, y = rect
    return (min(max((cx * src_w - x) / w, 0.0), 1.0), min(max((cy * src_h - y) / h, 0.0), 1.0))


def filter_complex(info, focus_x=0.5, focus_y=0.5, zooms=(), blurs=(), speeds=()):
    """Граф целиком: [0:v] → размытие → кадрирование → наезды → ускорение → [vout]."""
    sw, sh = info["width"], info["height"]
    rect = crop_rect(sw, sh, focus_x, focus_y)
    parts, cur = [], "0:v"
    if blurs:
        parts.append(blur_graph(blurs, sw, sh, cur, "vb"))
        cur = "vb"
    chain = [crop_chain(rect)]
    for z in zooms:
        cx, cy = map_point(z["cx"], z["cy"], rect, sw, sh)
        chain.append(zoom_chain(z["t0"], z["t1"], cx, cy, z["scale"], z.get("ramp", 0.4)))
    if speeds:
        parts.append(f"[{cur}]{','.join(chain)}[vc]")
        parts.append(speed_graph(speeds, info["duration"], "vc", "vout"))
    else:
        parts.append(f"[{cur}]{','.join(chain)},fps={OUT_FPS}[vout]")
    return ";".join(parts)


def build_cmd(video, out, fc):
    if Path(out).resolve() == Path(video).resolve():
        raise ValueError("broll_edit: выход совпадает со входом — оригинал не перезаписывается")
    return ["ffmpeg", "-y", "-v", "error", "-i", str(video), "-filter_complex", fc,
            "-map", "[vout]", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]


# ── CLI ──────────────────────────────────────────────────────────────────────

def _floats(s, n_min, n_max, what):
    vals = [float(v) for v in s.split(",")]
    if not n_min <= len(vals) <= n_max:
        raise argparse.ArgumentTypeError(f"{what}: ожидается {n_min}–{n_max} чисел через запятую")
    return vals


def parse_zoom(s):
    v = _floats(s, 5, 6, "--zoom t0,t1,cx,cy,масштаб[,ramp]")
    z = dict(zip(("t0", "t1", "cx", "cy", "scale"), v))
    if len(v) == 6:
        z["ramp"] = v[5]
    return z


def parse_blur(s):
    return dict(zip(("x", "y", "w", "h", "from", "to"), _floats(s, 6, 6, "--blur x,y,w,h,from,to")))


def parse_speed(s):
    return _floats(s, 3, 3, "--speed a,b,скорость")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out", help="новый файл (иначе <библиотека>/<id>/<id>.mp4)")
    ap.add_argument("--id")
    ap.add_argument("--library")
    ap.add_argument("--settings")
    ap.add_argument("--focus-x", type=float, default=0.5)
    ap.add_argument("--focus-y", type=float, default=0.5)
    ap.add_argument("--zoom", type=parse_zoom, action="append", default=[])
    ap.add_argument("--blur", type=parse_blur, action="append", default=[])
    ap.add_argument("--speed", type=parse_speed, action="append", default=[])
    ap.add_argument("--print", action="store_true", help="только показать команду")
    ap.add_argument("--force", action="store_true", help="перезаписать существующий выход")
    args = ap.parse_args(argv)

    if args.out:
        out = Path(args.out)
    elif args.id:
        import library
        out = library.resolve_library(args.library, args.settings) / args.id / f"{args.id}.mp4"
    else:
        raise SystemExit("нужен --out <файл> или --id <id> (+ библиотека)")
    import scan_broll
    info = scan_broll.probe(args.video)
    fc = filter_complex(info, args.focus_x, args.focus_y, args.zoom, args.blur, args.speed)
    cmd = build_cmd(args.video, out, fc)
    if args.print:
        print(" ".join(f"'{c}'" if " " in c or ";" in c else c for c in cmd))
        return 0
    if out.exists() and not args.force:
        raise SystemExit(f"broll_edit: {out} уже существует (перезапись — --force)")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(cmd, check=True)
    print(f"Готово: {out}")
    print(f"  дальше опись по готовому файлу: scan_broll.py '{out}' --out <папка> --id {out.stem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
