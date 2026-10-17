"""План наездов камеры по кускам монтажа. Только stdlib.

Правила (говорящая голова):
  • статики нет: каждый кусок с лицом двигается, ходы по кругу — быстрый наезд с удержанием,
    медленный отъезд, медленный наезд, быстрый отъезд (короткий кусок — только быстрые);
  • на склейке масштаб прыгает ≥ 0,1 или кусок сразу начинается быстрым ходом — то и другое
    прячет скачок кадра (jump cut);
  • кусок с ударным словом: быстрый наезд «вжух» на этом слове и удержание (до верха + 0,08);
    у слова можно задать силу и возврат: {"word": "наезд", "add": 0.35, "back": 0.1} — влетел
    на +0,35 и сразу отъехал до +0,1 («вжух-вжух», наезд читается как наезд);
  • центр масштаба — лицо в этом куске (медиана), поэтому лицо не уезжает;
  • масштаб ≥ 1 вокруг точки внутри кадра — края кадра всегда закрыты;
  • в окнах «текст за головой» только мягкий наезд до 1,04: текст масштабируется вместе с
    видео и иначе вылезает за край; кусок перед таким окном плавно возвращается к нижнему
    уровню, иначе на склейке кадр рывком отпрыгивает назад.
Уровни, размер и скорость «вжуха» — из настроек (монтаж.наезды).
"""
import csv
import statistics

from words import norm

MIN_STEP = 0.1
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


FAST = 0.22        # быстрый наезд/отъезд в начале куска, с
SHORT = 0.8        # кусок короче — только быстрые ходы (медленный не заметен)
LEAD = 2.0         # ударное слово дальше от начала куска — сначала быстрый наезд


def rotation(lo, hi):
    """Четыре хода по кругу (автор, 2026-10-17): быстрый наезд с удержанием, медленный отъезд,
    медленный наезд, быстрый отъезд. Три ступени: низ, середина, верх — скачок на склейке 0,1."""
    mid = round((lo + hi) / 2, 3)
    return [("in", True, lo, hi), ("out", False, mid, lo), ("in", False, mid, hi), ("out", True, mid, lo)]


def plan(spans, words, punch=(), faces=(), plates=(), levels=(1.15, 1.35), punch_add=0.12,
         punch_dur=0.16):
    """spans: [(a, b)] кусков на таймлайне ролика. → [{i, a, b, base, end, kind, origin, js: []}]

    Статики нет: каждый кусок с лицом двигается. На склейке масштаб прыгает ≥ MIN_STEP или кусок
    сразу начинается быстрым ходом (за FAST с) — и то и другое прячет скачок кадра."""
    lo, hi = levels[0], levels[-1]
    cap = round(hi + 0.08, 3)
    spec = {}
    for p in punch:
        if isinstance(p, dict):
            spec[norm(p["word"])] = (float(p.get("add", punch_add)), p.get("back"), "add" in p)
        else:
            spec[norm(p)] = (punch_add, None, False)
    punch_set = set(spec)
    moves, r = rotation(lo, hi), 0
    rows, used, prev_end = [], set(), None
    for i, (a, b) in enumerate(spans):
        on_plate = any(pa - 0.05 <= a and b <= pb + 0.05 for pa, pb in plates)
        cx, cy = face_center(faces, a, b)
        origin = f"{cx * 100:.1f}% {cy * 100:.1f}%"
        hit = next((w for w in words if a <= w["start"] < b - 0.15 and norm(w["text"]) in punch_set
                    and norm(w["text"]) not in used), None)
        fast_start = False
        if on_plate:
            base = lo
            js = [f'tl.set("#cam", {{transformOrigin: "{origin}", scale: {base}}}, {a:.3f});',
                  f'tl.fromTo("#cam", {{scale: {lo}}}, {{scale: {PLATE_MAX}, duration: {b - a - 0.02:.3f}, '
                  f'ease: "sine.inOut", immediateRender: false}}, {a:.3f});']
            start, end, kind = lo, PLATE_MAX, f"текст позади: {lo:.2f}→{PLATE_MAX:.2f}"
        else:
            short = b - a < SHORT
            # первый ход по кругу, который на этой склейке даёт скачок ≥ шага или начинается быстро
            for k in range(len(moves)):
                d, fast, s0, s1 = moves[(r + k) % len(moves)]
                fast = fast or short
                if prev_end is None or abs(s0 - prev_end) >= MIN_STEP - 1e-9 or (fast and not hit):
                    r = (r + k + 1) % len(moves)
                    break
            else:   # ни один ход не дал скачка — ход с самым большим скачком
                k = max(range(len(moves)), key=lambda j: abs(moves[j][2] - prev_end))
                d, fast, s0, s1 = moves[k]
                fast, r = fast or short, (k + 1) % len(moves)
            base = s0
            js = [f'tl.set("#cam", {{transformOrigin: "{origin}", scale: {s0}}}, {a:.3f});']
            if hit:
                used.add(norm(hit["text"]))
                add, back, explicit = spec[norm(hit["text"])]
                hold, lead = s0, ""
                if hit["start"] - a > LEAD and s0 < hi:
                    # длинный кусок до ударного слова — сначала быстрый наезд и держим крупно (автор, 2026-10-17)
                    fast_start, hold, lead = True, hi, f"быстрый наезд {s0:.2f}→{hi:.2f}, "
                    js.append(f'tl.to("#cam", {{scale: {hi}, duration: {FAST}, ease: "power3.out"}}, {a + 0.02:.3f});')
                top = round(hold + add if explicit else min(cap, max(hold + add, hi)), 3)
                js.append(f'tl.to("#cam", {{scale: {top}, duration: {punch_dur}, ease: "power3.out"}}, '
                          f'{hit["start"]:.3f});')
                start, end, kind = s0, top, f"{lead}вжух «{hit['text'].strip(',.!?')}» {hold:.2f}→{top:.2f}"
                if back is not None:
                    settle = round(hold + float(back), 3)
                    js.append(f'tl.to("#cam", {{scale: {settle}, duration: 0.32, ease: "power2.inOut"}}, '
                              f'{hit["start"] + punch_dur + 0.04:.3f});')
                    end, kind = settle, kind + f"→{settle:.2f}"
            elif fast:
                fast_start = True
                js.append(f'tl.to("#cam", {{scale: {s1}, duration: {min(FAST, b - a - 0.04):.3f}, '
                          f'ease: "power3.out"}}, {a + 0.02:.3f});')
                start, end = s0, s1
                kind = f"{'быстрый наезд' if d == 'in' else 'быстрый отъезд'} {s0:.2f}→{s1:.2f}"
            else:
                js.append(f'tl.fromTo("#cam", {{scale: {s0}}}, {{scale: {s1}, duration: {b - a - 0.02:.3f}, '
                          f'ease: "sine.inOut", immediateRender: false}}, {a:.3f});')
                start, end = s0, s1
                kind = f"{'медленный наезд' if d == 'in' else 'медленный отъезд'} {s0:.2f}→{s1:.2f}"
        rows.append({"i": i, "a": a, "b": b, "base": base, "start_scale": start, "end": end, "kind": kind,
                     "origin": origin, "js": js, "plate": on_plate, "fast_start": fast_start,
                     "hit_end": (hit["start"] + punch_dur) if hit else a})
        prev_end = end
    glide_before_plates(rows, lo)
    return rows


def glide_before_plates(rows, lo, glide=1.2):
    """Кусок перед «текстом за головой» не обрывается рывком: окно текста держит масштаб ≤ 1,04,
    и на склейке с 1,12 на 1,00 кадр «отпрыгивает» назад. Поэтому за последние ~1,2 с куска
    масштаб плавно возвращается к нижнему уровню, пока за спиной растворяется фон."""
    for r, nxt in zip(rows, rows[1:]):
        if not nxt["plate"] or r["plate"] or r["end"] <= PLATE_MAX:
            continue
        t0 = max(r["hit_end"] + 0.15, r["b"] - glide)
        if r["b"] - 0.02 - t0 < 0.3:
            continue
        r["js"].append(f'tl.fromTo("#cam", {{scale: {r["end"]}}}, {{scale: {lo}, duration: {r["b"] - 0.02 - t0:.3f}, '
                       f'ease: "sine.inOut", immediateRender: false}}, {t0:.3f});')
        r["kind"] += f" → плавно к {lo:.2f} перед текстом позади"
        r["end"] = lo


def jumps(rows):
    """Скачок масштаба на каждой склейке (для проверки правила ≥ 0,1)."""
    return [round(abs(r["start_scale"] - p["end"]), 3) for p, r in zip(rows, rows[1:])]
