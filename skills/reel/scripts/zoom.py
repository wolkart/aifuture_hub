"""План наездов камеры по кускам монтажа. Только stdlib.

Правила (говорящая голова):
  • на каждой склейке масштаб меняется ≥ 0,1 — прячет скачок кадра (jump cut);
  • кусок с ударным словом: быстрый наезд «вжух» (+0,12 за 0,16 с) на этом слове и удержание;
  • иначе длинный кусок (> 1,8 с) — медленный наезд или отъезд (±0,05), короткий — статика;
  • центр масштаба — лицо в этом куске (медиана), поэтому лицо не уезжает;
  • масштаб ≥ 1 вокруг точки внутри кадра — края кадра всегда закрыты;
  • в окнах «текст за головой» только мягкий наезд до 1,04: текст масштабируется вместе с
    видео и иначе вылезает за край.
Уровни, размер и скорость «вжуха» — из настроек (монтаж.наезды).
"""
import csv
import statistics

from words import norm

MIN_STEP = 0.1
LONG = 1.8
DRIFT = 0.05
PLATE_MAX = 1.04
DEFAULT_CENTER = (0.5, 0.45)


def load_faces(path):
    """faces.csv (t,cx,cy; пустые cx — лица нет) → [(t, cx, cy)]."""
    out = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("cx"):
                out.append((float(r["t"]), float(r["cx"]), float(r["cy"])))
    return out


def face_center(faces, a, b):
    pts = [(x, y) for t, x, y in faces if a <= t < b]
    if not pts:
        return DEFAULT_CENTER
    return statistics.median(x for x, _ in pts), statistics.median(y for _, y in pts)


def plan(spans, words, punch=(), faces=(), plates=(), levels=(1.0, 1.15), punch_add=0.12,
         punch_dur=0.16):
    """spans: [(a, b)] кусков на таймлайне ролика. → [{i, a, b, base, end, kind, origin, js: []}]"""
    lo, hi = levels[0], levels[-1]
    punch_set = {norm(p) for p in punch}
    rows, used, prev_end = [], set(), None
    for i, (a, b) in enumerate(spans):
        on_plate = any(pa - 0.05 <= a and b <= pb + 0.05 for pa, pb in plates)
        base = lo if (i % 2 == 0 or on_plate) else hi
        if not on_plate and prev_end is not None and abs(base - prev_end) < MIN_STEP:
            base = hi if prev_end < lo + 0.06 else lo
        cx, cy = face_center(faces, a, b)
        origin = f"{cx * 100:.1f}% {cy * 100:.1f}%"
        js = [f'tl.set("#cam", {{transformOrigin: "{origin}", scale: {base}}}, {a:.3f});']
        hit = next((w for w in words if a <= w["start"] < b - 0.15 and norm(w["text"]) in punch_set
                    and norm(w["text"]) not in used), None)
        if on_plate:
            js.append(f'tl.fromTo("#cam", {{scale: {lo}}}, {{scale: {PLATE_MAX}, duration: {b - a - 0.02:.3f}, '
                      f'ease: "sine.inOut", immediateRender: false}}, {a:.3f});')
            start, end, kind = lo, PLATE_MAX, f"текст позади: {lo:.2f}→{PLATE_MAX:.2f}"
        elif hit:
            used.add(norm(hit["text"]))
            top = round(base + punch_add, 3)
            js.append(f'tl.to("#cam", {{scale: {top}, duration: {punch_dur}, ease: "power3.out"}}, '
                      f'{hit["start"]:.3f});')
            start, end, kind = base, top, f"вжух «{hit['text'].strip(',.!?')}» {base:.2f}→{top:.2f}"
        elif b - a > LONG:
            push = (i // 2) % 2 == 0
            if prev_end is not None and not push and abs(base + DRIFT - prev_end) < MIN_STEP:
                push = True  # отъезд начался бы слишком близко к прошлому масштабу
            s0, s1 = (base, round(base + DRIFT, 3)) if push else (round(base + DRIFT, 3), base)
            js.append(f'tl.fromTo("#cam", {{scale: {s0}}}, {{scale: {s1}, duration: {b - a - 0.02:.3f}, '
                      f'ease: "sine.inOut", immediateRender: false}}, {a:.3f});')
            start, end, kind = s0, s1, f"{'наезд' if push else 'отъезд'} {s0:.2f}→{s1:.2f}"
        else:
            start, end, kind = base, base, f"статика {base:.2f}"
        rows.append({"i": i, "a": a, "b": b, "base": base, "start_scale": start, "end": end, "kind": kind,
                     "origin": origin, "js": js, "plate": on_plate})
        prev_end = end
    return rows


def jumps(rows):
    """Скачок масштаба на каждой склейке (для проверки правила ≥ 0,1)."""
    return [round(abs(r["start_scale"] - p["end"]), 3) for p, r in zip(rows, rows[1:])]
