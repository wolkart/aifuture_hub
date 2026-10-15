#!/usr/bin/env python3
"""Склейка слоёв и звука ffmpeg. Только stdlib + ffmpeg.

Две операции:
  base  — черновик → behind.webm (текст за головой) → вырезанный человек (кадры маски,
          только в окнах подложек) → <вариант>/base.mp4. Её потом масштабируют наезды,
          поэтому текст за головой «едет» вместе с видео.
  final — основа (main.mp4 / base.mp4 / черновик) → front.webm (субтитры, карточки) +
          звук: голос черновика → −14 LUFS, музыка −12 LU к голосу, пик ≤ −1,5 dBTP →
          export/<имя> — <метка>.mp4.
Альфа-слои — VP9 webm; декодер для них задаётся явно (-c:v libvpx-vp9), иначе ffmpeg
берёт встроенный и теряет прозрачность.

usage: composite.py base  <папка варианта>
       composite.py final <папка варианта> [--no-music] [--label "по слову, лайм"] [--settings …]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hf  # noqa: E402
import settings as settings_mod  # noqa: E402
from layout import Build  # noqa: E402


def enable_expr(windows):
    return "+".join(f"between(t,{a},{b})" for a, b in windows) or "0"


def base_cmd(video, behind_webm, matte_pattern, windows, out, fps=hf.FPS):
    fc = (f"[0:v][1:v]overlay=format=auto[a];[2:v]format=yuva420p[m];"
          f"[a][m]overlay=format=auto:enable='{enable_expr(windows)}'[v]")
    return ["ffmpeg", "-y", "-v", "error", "-stats", "-i", str(video), "-c:v", "libvpx-vp9",
            "-i", str(behind_webm), "-framerate", str(fps), "-i", str(matte_pattern),
            "-filter_complex", fc, "-map", "[v]", "-an", "-r", str(fps), "-c:v", "libx264", "-crf", "14",
            "-preset", "medium", "-pix_fmt", "yuv420p", str(out)]


def gains(voice_lufs, music_lufs, target=-14.0, rel=-12.0):
    """Усиление (dB) голоса до target и музыки до target+rel."""
    gv = target - voice_lufs
    gm = None if music_lufs is None else (target + rel) - music_lufs
    return round(gv, 2), (None if gm is None else round(gm, 2))


def level_expr(levels):
    """Огибающая музыки, dB к обычному уровню: [(t, db, ramp)] → выражение ffmpeg от t.
    До первого ключа — 0 dB; от ключа к ключу — линейно за ramp секунд, дальше держится."""
    parts, prev = [], 0.0
    for t, db, ramp in sorted(levels):
        ramp = max(0.01, float(ramp or 0.01))
        parts.append((t, prev, db, ramp))
        prev = db
    expr = f"{prev}"
    for t, d0, d1, r in reversed(parts):
        expr = (f"if(lt(t,{t:.3f}),{d0},if(lt(t,{t + r:.3f}),{d0}+({d1}-({d0}))*(t-{t:.3f})/{r:.3f},{expr}))")
    return expr


def tp_linear(db):
    return round(10 ** (db / 20), 4)


def level_at(levels, t):
    """Уровень огибающей в момент t — та же логика, что level_expr (для проверки и отчёта)."""
    prev, cur = 0.0, 0.0
    for kt, db, ramp in sorted(levels):
        ramp = max(0.01, float(ramp or 0.01))
        if t < kt:
            return cur
        cur = db if t >= kt + ramp else prev + (db - prev) * (t - kt) / ramp
        prev = db
    return cur


def auto_levels(words, dur, lift_db=6.0, min_gap=0.6, ramp=0.25, tail=0.15):
    """Музыка под голосом — на своём уровне (−12 LU к голосу), в паузах ≥ min_gap и
    до/после речи — громче на lift_db. Огибающая по словам расшифровки: уходит вниз
    за ramp до первого слова фразы, поднимается через tail после последнего.
    → ключи [(t, db, ramp)] для level_expr."""
    if lift_db <= 0 or not words:
        return []
    phrases = []
    for w in words:
        if phrases and w["start"] - phrases[-1][1] < min_gap:
            phrases[-1][1] = w["end"]
        else:
            phrases.append([w["start"], w["end"]])
    keys = []
    if phrases[0][0] > ramp + 0.05:
        keys += [(0.0, lift_db, 0.01), (round(phrases[0][0] - ramp, 3), 0.0, ramp)]
    for (_, pe), (ps, _) in zip(phrases, phrases[1:]):
        room = (ps - ramp) - (pe + tail)
        if room < 0.1:
            continue
        keys += [(round(pe + tail, 3), lift_db, round(min(0.4, room / 2), 3)), (round(ps - ramp, 3), 0.0, ramp)]
    last = phrases[-1][1]
    if dur - last > tail + 0.2:
        keys.append((round(last + tail, 3), lift_db, 0.4))
    return keys


def final_cmd(video, front_webm, voice_src, music, out, dur, gv, gm, true_peak=-1.5, fps=hf.FPS, levels=(),
              sfx=None):
    cmd = ["ffmpeg", "-y", "-v", "error", "-stats", "-i", str(video)]
    vf = "[0:v]null[bv]"
    if front_webm:
        cmd += ["-c:v", "libvpx-vp9", "-i", str(front_webm)]
        vf = "[0:v][1:v]overlay=format=auto[bv]"
    vi = 2 if front_webm else 1
    cmd += ["-i", str(voice_src)]
    af = f"[{vi}:a]volume={gv}dB[vo]"
    mix, k = ["[vo]"], vi + 1
    if music:
        cmd += ["-i", str(music)]
        env = f",volume='pow(10,({level_expr(levels)})/20)':eval=frame" if levels else ""
        af += f";[{k}:a]volume={gm}dB{env}[mu]"
        mix.append("[mu]")
        k += 1
    if sfx:   # звуки уже на нужном уровне (пики из плана), без нормализации
        cmd += ["-i", str(sfx)]
        af += f";[{k}:a]anull[sx]"
        mix.append("[sx]")
    mix_in = "[vo]"
    if len(mix) > 1:
        af += f";{''.join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0[mx]"
        mix_in = "[mx]"
    # лимитер ловит пики отсчётов, а true peak — между ними: 0,3 dB запаса; у звуков атаки
    # резкие (щелчок, удар), между отсчётами они вылезают выше — запас 0,9 dB и быстрая атака
    margin = 0.9 if sfx else 0.3
    af += f";{mix_in}alimiter=limit={tp_linear(true_peak - margin)}:attack=1:level=disabled[ao]"
    cmd += ["-filter_complex", f"{vf};{af}", "-map", "[bv]", "-map", "[ao]", "-r", str(fps),
            "-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", str(out)]
    return cmd


def parse_loudnorm(stderr):
    """JSON-блок loudnorm (print_format=json) из stderr → dict с числами."""
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr, re.S)
    if not m:
        raise ValueError("loudnorm: нет замера в выводе ffmpeg")
    out = {}
    for k, v in json.loads(m.group(0)).items():
        try:
            out[k] = float(v)
        except (TypeError, ValueError):
            pass
    return out


def measure(path):
    """Интегральная громкость (LUFS) и true peak (dBTP)."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af",
                        "loudnorm=print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    d = parse_loudnorm(p.stderr)
    return d["input_i"], d["input_tp"]


def cmd_base(b):
    windows = b.read_json(b.windows, [])
    if not windows:
        raise SystemExit("base: windows.json пуст — текста за головой в плане нет, основа = черновик")
    if not b.behind_webm.exists() or not (b.matte / "f_00001.png").exists():
        raise SystemExit("base: нужен behind.webm (рендер behind/) и кадры маски (matte.py)")
    subprocess.run(base_cmd(b.roughcut, b.behind_webm, b.matte / "f_%05d.png", windows, b.base), check=True)
    print(f"основа: {b.base} (текст за головой + маска в окнах {windows})")


def cmd_final(b, args):
    plan = b.load_plan() if b.plan.exists() else {}
    s = settings_mod.load(args.settings) or settings_mod.default()
    video = next(p for p in (b.main_mp4, b.base, b.roughcut) if p.exists())
    front = b.front_webm if b.front_webm.exists() else None
    dur = round(hf.duration(b.roughcut) - 0.02, 3)
    music = b.music if (plan.get("music", True) and not args.no_music and b.music.exists()) else None
    v_i, _ = measure(b.roughcut)
    m_i = measure(music)[0] if music else None
    gv, gm = gains(v_i, m_i, s["audio"]["voice_lufs"], s["music"]["rel_lu"])
    label = args.label or plan.get("label") or b.name
    b.final.mkdir(parents=True, exist_ok=True)
    out = b.final / f"{b.stem} — {label}.mp4"
    levels = []
    lift = float(plan.get("music_lift_db", s["music"].get("pause_lift_db", 6)))
    if music and not plan.get("music_levels") and lift > 0 and b.transcript.exists():
        import words as wmod
        levels = auto_levels(wmod.load(b.transcript), dur, lift)
        pauses = sum(1 for _, db, _ in levels if db > 0)
        print(f"музыка: под голосом {s['music']['rel_lu']:.0f} LU к голосу, в паузах +{lift:.0f} dB "
              f"(окон {pauses}; выключить — \"music_lift_db\": 0 в плане)")
    if music and plan.get("music_levels"):
        import words as wmod
        words = wmod.load(b.transcript)
        for k in plan["music_levels"]:
            levels.append((round(wmod.at(words, k["at"]), 3), float(k["db"]), float(k.get("ramp", 0.3))))
        print("музыка по словам: " + ", ".join(f"{t:.2f} с → {db:+.0f} dB за {r:.2f} с" for t, db, r in levels))
    sfx = b.var / "sfx.wav"
    sfx = sfx if (plan.get("sfx") and sfx.exists()) else None
    if plan.get("sfx") and not sfx:
        print("⚠ в плане есть звуки, а sfx.wav нет — собери: uv run sfx.py bed <вариант>")
    subprocess.run(final_cmd(video, front, b.roughcut, music, out, dur, gv, gm, s["audio"]["true_peak"],
                             levels=levels, sfx=sfx), check=True)
    f_i, f_tp = measure(out)
    rec = json.loads(b.cutlist.read_text())["inputs"].get("audio") if b.cutlist.exists() else None
    print(f"Звук: {Path(rec).name if rec else 'звук черновика'} (голос из {b.roughcut.name})")
    print(f"видео: {video.name}" + (" + front.webm" if front else "") + (f" | музыка {music.name}" if music else " | без музыки")
          + (" | звуки sfx.wav" if sfx else ""))
    print(f"громкость: голос {v_i:.1f} → {s['audio']['voice_lufs']:.0f} LUFS"
          + (f", музыка {m_i:.1f} → {s['audio']['voice_lufs'] + s['music']['rel_lu']:.0f} LUFS" if music else ""))
    tp_ok = f_tp <= s["audio"]["true_peak"] + 0.3
    print(f"итог: {f_i:.1f} LUFS, пик {f_tp:.1f} dBTP{'' if tp_ok else ' ⚠ выше нормы'} → {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("op", choices=["base", "final"])
    ap.add_argument("variant")
    ap.add_argument("--no-music", action="store_true")
    ap.add_argument("--label", default=None)
    ap.add_argument("--settings", default=None)
    args = ap.parse_args()
    b = Build(args.variant)
    if args.op == "base":
        cmd_base(b)
    else:
        cmd_final(b, args)


if __name__ == "__main__":
    main()
