#!/usr/bin/env python3
"""Один таймлайн с готовым роликом для Resolve: резка + графика + зум + звуки + музыка. Только stdlib.

  python3 assemble.py <cutlist> [--range С ПО] [--mp4] [--no-music]
    → export/<стем>.fcpxml (с --range — «<стем> — проба ММСС-ММСС.fcpxml»): File → Import → Timeline…
        V1 — резка записи (клипы ссылаются на исходник, без перекодирования; отдельный звук — под ним);
        V2 — зум на голове; V3 — сцены, вставки поверх экрана, панели; V4 — акценты у головы;
        звук графики — внутри её клипов; музыка — music/bed.wav отдельной дорожкой;
        маркер на каждой вставке: номер, вид, что.
    → export/<стем> — таймкоды.md — что на какой таймкод.
    --mp4 — запасной выход без Resolve: готовый mp4 (резка → графика поверх → звук с лимитером).

Графика — connected clips к тому клипу резки, внутри которого её начало: offset — во времени родителя
(его start + сдвиг). Вставка длиннее родителя «свисает» за склейку — FCPX это разрешает; как прочтёт
Resolve — проверка первым куском (--range), результат — в references/resolve.md.
"""
import argparse
import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "rough-cut" / "scripts"))
import timeline  # noqa: E402

KIND = {"Д": "сцена", "Э": "поверх экрана", "П": "панель", "А": "акцент", "З": "зум на голове"}
TRIM_WARN = 0.45
LIMIT = 0.84
# у alimiter по умолчанию level=1 — сам дотягивает выход до 0 dBFS; поэтому level=false и +1,5 dB до лимитера: пики на −1,5 dBFS
MASTER = f"volume={-20 * math.log10(LIMIT):.2f}dB,alimiter=limit={LIMIT}:level=false"


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    return float(j["format"]["duration"]), any(s["codec_type"] == "audio" for s in j["streams"])


def load_items(work):
    """Графика и зум из clips.json / zoom.json: [{name, type, start, dur, file, lane, what}] — только отрендеренное."""
    items, missing = [], []
    for f in ("zoom.json", "clips.json"):
        p = work / f
        for c in (json.loads(p.read_text(encoding="utf-8")) if p.exists() else []):
            path = work / c["file"] if c.get("file") else None
            if not path or not path.exists():
                missing.append(c["name"])
                continue
            dur, aud = probe(path)
            items.append({**c, "path": path, "media_dur": dur, "dur": round(min(dur, c.get("dur") or dur), 3), "audio": aud})
    return sorted(items, key=lambda c: (c["start"], c["lane"])), missing


def fit(items):
    """Нахлёсты на одной дорожке: хвост предыдущей (выход, запас) обрезается до начала следующей."""
    out, warn, last = [], [], {}
    for c in sorted(items, key=lambda c: c["start"]):
        p = last.get(c["lane"])
        if p is not None and p["start"] + p["dur"] > c["start"]:
            cut = p["start"] + p["dur"] - c["start"]
            if cut > TRIM_WARN:
                warn.append(f"{p['name']} → {c['name']}: нахлёст {cut:.2f} с — хвост обрезан")
            p["dur"] = round(c["start"] - p["start"], 3)
        out.append(c)
        last[c["lane"]] = c
    return [c for c in out if c["dur"] > 0.04], warn


def in_range(sp, items, rng):
    """Кусок таймлайна [a, b): куски резки обрезаются, графика — с началом внутри, время от a."""
    if not rng:
        return sp, items
    a, b = rng
    spans = []
    for ta, tb, sa, sb, r in sp:
        lo, hi = max(a, ta), min(b, tb)
        if hi - lo > 0.04:
            spans.append((round(lo - a, 4), round(hi - a, 4), sa + (lo - ta) * r, sa + (hi - ta) * r, r))
    its = [{**c, "start": round(c["start"] - a, 3), "dur": round(min(c["dur"], b - c["start"]), 3)}
           for c in items if a <= c["start"] < b]
    return spans, its


class Rt:
    """Секунды → рациональное время FCPXML по сетке кадров."""

    def __init__(self, num, den):
        self.num, self.den = num, den

    def __call__(self, s):
        return f"{round(s * self.num / self.den) * self.den}/{self.num}s"


def fcpxml(d, sp, items, music, title, music_from=0.0):
    num, den = d["fps"]["num"], d["fps"]["den"]
    rt = Rt(num, den)
    W, H = timeline.W, timeline.H
    fx = ET.Element("fcpxml", version="1.9")
    res = ET.SubElement(fx, "resources")
    ET.SubElement(res, "format", id="r1", name=f"FFVideoFormat{H}p", frameDuration=f"{den}/{num}s", width=str(W), height=str(H))
    ET.SubElement(res, "format", id="r0", name="source", frameDuration=f"{den}/{num}s", width=str(d["width"]), height=str(d["height"]))

    def asset(rid, name, path, dur, video=True, audio=True, fmt="r1"):
        attrs = {"hasAudio": "1", "audioSources": "1", "audioChannels": "2"} if audio else {}
        if video:
            attrs.update(hasVideo="1", format=fmt)
        a = ET.SubElement(res, "asset", id=rid, name=name, start="0s", duration=rt(dur), **attrs)
        ET.SubElement(a, "media-rep", kind="original-media", src=Path(path).resolve().as_uri())

    audio = d["inputs"].get("audio")
    # отдельная запись звука — звук монтажа: у видео звук не объявляем, иначе в Resolve голос пойдёт дважды
    asset("r2", Path(d["inputs"]["video"]).stem, d["inputs"]["video"], d["duration_s"], audio=not audio, fmt="r0")
    if audio:
        asset("r3", Path(audio).stem, audio, d["duration_s"], video=False)
    for i, c in enumerate(items):
        asset(f"g{i}", c["path"].stem, c["path"], c.get("media_dur", c["dur"]), audio=c["audio"])
    if music:
        asset("m1", "music-bed", music, probe(music)[0], video=False)
    seq = ET.SubElement(ET.SubElement(ET.SubElement(ET.SubElement(fx, "library"), "event", name=title), "project", name=title),
                        "sequence", format="r1", tcStart="0s")
    spine = ET.SubElement(seq, "spine")
    off = d.get("sync", {}).get("offset_s", 0.0)
    clips = []
    for ta, tb, sa, sb, r in sp:
        if r != 1:
            raise SystemExit("в cut-list есть speedup: FCPXML не передаёт скорость надёжно — замени его на cut или keep")
        c = ET.SubElement(spine, "asset-clip", ref="r2", name=Path(d["inputs"]["video"]).stem, offset=rt(ta), start=rt(sa),
                          duration=rt(tb - ta))
        if audio:
            ET.SubElement(c, "asset-clip", ref="r3", lane="-1", offset=rt(sa), start=rt(sa + off), duration=rt(tb - ta))
        clips.append((ta, tb, sa, c))
    n = 0
    for i, c in enumerate(items):
        ta, tb, sa, parent = next((x for x in clips if x[0] - 1e-6 <= c["start"] < x[1]), clips[-1])
        g = ET.SubElement(parent, "asset-clip", ref=f"g{i}", lane=str(c["lane"]), name=c["name"],
                          offset=rt(sa + (c["start"] - ta)), start="0s", duration=rt(c["dur"]))
        if c["type"] != "З":
            n += 1
            ET.SubElement(g, "marker", start="0s", duration=f"{den}/{num}s", value=f"{n:02d} {KIND[c['type']]}: {c.get('what') or c['name']}")
    if music and clips:
        ta, tb, sa, first = clips[0]
        ET.SubElement(first, "asset-clip", ref="m1", lane="-2", name="music-bed", offset=rt(sa), start=rt(music_from),
                      duration=rt(timeline.total(sp)))
    return fx


def write_xml(fx, path):
    tree = ET.ElementTree(fx)
    ET.indent(tree)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    head, body = Path(path).read_text(encoding="utf-8").split("\n", 1)
    Path(path).write_text(head + "\n<!DOCTYPE fcpxml>\n" + body, encoding="utf-8")


def tc(t, fps):
    f = round(t * fps)
    return f"{f // (3600 * fps):02d}:{f // (60 * fps) % 60:02d}:{f // fps % 60:02d}:{f % fps:02d}"


def timecodes(items, total, fps, title, xml_name, warn, music_note):
    gfx = [c for c in items if c["type"] != "З"]
    zooms = [c for c in items if c["type"] == "З"]
    cover = sum(c["dur"] for c in gfx)
    count = {k: sum(1 for c in gfx if c["type"] == k) for k in "ДЭПА"}
    md = [f"# {title} — графика по таймлайну", "",
          f"Таймлайн {timeline.mmss(total)}. Вставок {len(gfx)} (Д {count['Д']} · Э {count['Э']} · П {count['П']} · А {count['А']}), "
          f"графики {cover / 60:.1f} мин ({cover / max(total, 1):.0%}); зум на голове — {len(zooms)} кусков "
          f"({sum(c['dur'] for c in zooms) / 60:.1f} мин).", "",
          f"Импорт: **File → Import → Timeline…** → `{xml_name}`. Таймкод ниже — от нуля; таймлайн Resolve обычно "
          "начинается с 01:00:00:00 — тогда плюс час.", "",
          "| № | с | до | длина | вид | что |", "|---|---|---|---|---|---|"]
    md += [f"| {i:02d} | {tc(c['start'], fps)} | {tc(c['start'] + c['dur'], fps)} | {c['dur']:4.1f} с | {KIND[c['type']]} | "
           f"{c.get('what') or c['name']} |" for i, c in enumerate(gfx, 1)]
    if warn:
        md += ["", "Нахлёсты (хвосты обрезаны):", *[f"- {w}" for w in warn]]
    if music_note:
        md += ["", music_note]
    return "\n".join(md) + "\n"


def mp4(d, sp, items, music, out, rng):
    """Запасной выход без Resolve: V1 резкой (rough-cut render.py) → графика поверх → звук. Два прохода кодирования."""
    import render
    import cutlist
    v1 = out.with_name(out.stem + ".v1.tmp.mp4")
    dd = d
    if rng:
        import music as mus
        dd = mus.chunk_cutlist(d, rng[0], rng[1] - rng[0])
    cutlist.validate(dd)
    subprocess.run(render.build_cmd(dd, v1), check=True)
    total = timeline.total(sp)
    items = sorted(items, key=lambda c: c["lane"])          # порядок входов = порядок наложения: зум ниже графики
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(v1)]
    for c in items:
        cmd += ["-i", str(c["path"])]
    if music:
        cmd += ["-i", str(music)]
    W, H = timeline.W, timeline.H
    fc, v, auds = [f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[b0]"], "[b0]", ["[0:a]"]
    for i, c in enumerate(items, 1):
        s, du = c["start"], c["dur"]
        fc.append(f"[{i}:v]trim=0:{du:.3f},setpts=PTS-STARTPTS+{s:.3f}/TB[g{i}]")
        fc.append(f"{v}[g{i}]overlay=enable='between(t,{s:.3f},{s + du - 0.034:.3f})':eof_action=pass[v{i}]")
        v = f"[v{i}]"
        if c["audio"]:
            ms = int(round(s * 1000))
            fc.append(f"[{i}:a]atrim=0:{du:.3f},adelay={ms}|{ms}[a{i}]")
            auds.append(f"[a{i}]")
    if music:
        k = len(items) + 1
        start = rng[0] if rng else 0.0
        fc.append(f"[{k}:a]atrim={start:.3f}:{start + total:.3f},asetpts=PTS-STARTPTS[m]")
        auds.append("[m]")
    fc.append(f"{''.join(auds)}amix=inputs={len(auds)}:normalize=0:duration=first,{MASTER}[a]")
    fps = f"{d['fps']['num']}/{d['fps']['den']}"
    cmd += ["-filter_complex", ";".join(fc), "-map", v, "-map", "[a]", "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium",
            "-crf", "16", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", fps, "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
            "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    v1.unlink()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cutlist")
    ap.add_argument("--range", type=float, nargs=2, metavar=("С", "ПО"))
    ap.add_argument("--mp4", action="store_true")
    ap.add_argument("--no-music", action="store_true")
    a = ap.parse_args()
    cut = Path(a.cutlist).resolve()
    d = timeline.load(cut)
    work = timeline.work_dir(cut)
    stem = cut.name.replace(".cutlist.json", "")
    items, missing = load_items(work)
    items, warn = fit(items)
    sp, its = in_range(timeline.spans(d), items, a.range)
    total = timeline.total(sp)
    music = None if a.no_music else (work / "music" / "bed.wav")
    music = music if music and music.exists() else None
    tag = f" — проба {timeline.mmss(a.range[0]).replace(':', '')[:4]}-{timeline.mmss(a.range[1]).replace(':', '')[:4]}" if a.range else ""
    title = stem + tag
    xml = cut.parent / f"{title}.fcpxml"
    write_xml(fcpxml(d, sp, its, music, title, a.range[0] if a.range else 0.0), xml)
    fps = round(d["fps"]["num"] / d["fps"]["den"])
    bed = json.loads((work / "music" / "bed.json").read_text(encoding="utf-8")) if music and (work / "music" / "bed.json").exists() else None
    note = (f"Музыка: {Path(bed['track']).stem} · {bed['rel_lu']:.0f} LU к голосу · подъём в паузах {bed['lift_db']:.0f} dB "
            f"(`монтаж/music/bed.wav`).") if bed else ("Музыки нет." if not music else "")
    (cut.parent / f"{title} — таймкоды.md").write_text(timecodes(its, total, fps, title, xml.name, warn, note), encoding="utf-8")
    gfx = [c for c in its if c["type"] != "З"]
    print(f"таймлайн {timeline.mmss(total)} · вставок {len(gfx)} · зум {len(its) - len(gfx)} · музыка: {'есть' if music else 'нет'} → {xml}")
    for w in warn:
        print("  ⚠", w)
    if missing:
        print(f"  ✗ не отрендерено (в таймлайн не вошло): {', '.join(missing)}")
    if a.mp4:
        out = cut.parent / f"{title} — готовый.mp4"
        mp4(d, sp, its, music, out, a.range)
        print(f"mp4: {out}")


if __name__ == "__main__":
    main()
