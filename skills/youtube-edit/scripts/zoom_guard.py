#!/usr/bin/env python3
"""На переходе зума ни реза: правит cut-list по переходам из scan.json. Только stdlib.

Правило автора (2026-10-17): наезд и отъезд идут по чистой речи — склейка посреди перехода
дёргает кадр, и потом это уже не исправить (в экспорте зум вшит). Поэтому граница реза не
может лежать в окне перехода (движение всего кадра + поля PAD_BEFORE/PAD_AFTER):
  • начало реза в окне → рез начинается после окна (рез ужимается — лишнего не режем);
  • конец реза в окне → рез кончается до окна;
  • рез целиком в окне или от него остаётся < MIN_CUT → рез снят (остаётся «э-м» или пауза —
    «блогер имеет право запинаться»);
  • рез, накрывший переход целиком, — оставлен: граница вне окна, на склейке просто другой
    масштаб, как обычная перебивка.
Повторный прогон ничего не меняет (можно гонять после каждого longform.py build).

  python3 zoom_guard.py <cutlist.json> --scan export/монтаж/scan.json
      → cut-list правится на месте, прежний — <стем>.prezoom.json (если правки были)
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "rough-cut" / "scripts"))
import cutlist  # noqa: E402

PAD_BEFORE, PAD_AFTER = 0.2, 0.3
MIN_CUT = 0.15


def windows(transitions, pad_before=PAD_BEFORE, pad_after=PAD_AFTER):
    return [(round(a - pad_before, 3), round(b + pad_after, 3)) for a, b in transitions]


def guard(segments, wins, min_cut=MIN_CUT):
    """segments cut-list → (новые cut/speedup-сегменты, журнал [(было, стало|None, окно)])."""
    out, log = [], []
    for s in segments:
        if s["action"] == "keep":
            continue
        a, b = s["start"], s["end"]
        for wa, wb in wins:
            if b <= wa or a >= wb or (a < wa and b > wb):
                continue                                     # не задевает или накрыл переход целиком
            na = wb if wa <= a < wb else a
            nb = wa if wa < b <= wb else b
            if nb - na < min_cut or (wa <= a and b <= wb):
                log.append(((a, b), None, (wa, wb)))
                a = b = None
                break
            log.append(((a, b), (na, nb), (wa, wb)))
            a, b = na, nb
        if a is not None:
            out.append({**s, "start": round(a, 3), "end": round(b, 3)})
    return out, log


def apply(d, transitions):
    cuts, log = guard(d["segments"], windows(transitions))
    if not log:
        return d, log
    meta = {k: d[k] for k in d if k not in ("version", "segments")}
    return cutlist.from_cuts(meta, cuts), log


def mmss(t):
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cutlist")
    ap.add_argument("--scan", required=True)
    a = ap.parse_args()
    p = Path(a.cutlist)
    d = cutlist.load(p)
    tr = json.loads(Path(a.scan).read_text(encoding="utf-8"))["transitions"]
    nd, log = apply(d, tr)
    moved = sum(1 for _, new, _ in log if new)
    print(f"переходов зума: {len(tr)} · резов задето: {len(log)} (ужато {moved}, снято {len(log) - moved})")
    for (a0, b0), new, (wa, wb) in log:
        what = f"→ {mmss(new[0])}–{mmss(new[1])}" if new else "→ снят"
        print(f"  рез {mmss(a0)}–{mmss(b0)} {what} (переход {mmss(wa)}–{mmss(wb)})")
    if log:
        shutil.copy(p, p.with_name(p.name.replace(".cutlist.json", "") + ".prezoom.json"))
        p.write_text(json.dumps(nd, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"cut-list поправлен → {p}")


if __name__ == "__main__":
    main()
