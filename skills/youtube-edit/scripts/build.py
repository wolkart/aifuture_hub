#!/usr/bin/env python3
"""Сцены ролика (export/монтаж/scenes.py) → проекты HyperFrames → клипы графики + clips.json.

  python3 build.py <export/монтаж> [имя …] [--gaps] [--render] [--settings reel.settings.json]
    без ключей — только проекты (секунды): что где стоит, сдвиги начала (fitted), якоря на вырезанных словах;
    --gaps     — паузы внутри сцен > 1,8 с и что в них звучит: закрывай действиями на слова (mark/wave/shake/chip);
    --render   — клипы: Д, П и Э — mp4 (high, кадры видео PNG; под Э — кусок той же резки таймлайна),
                 А — .mov ProRes 4444 с альфой (лежат поверх зума); звуки сцены — внутри клипа. Долго: фоном.
    --alpha    — Э тоже прозрачными (.mov): под ними живая запись V1, но с вуалью на весь кадр это ~50 МБ/с
                 (11,7 с = 605 МБ на пробе 2026-10-20) — только когда на диске есть место.

Сцены — список функций SCENES в scenes.py; функция возвращает Ins(...).done(...) или Tpl/drawer(...).
Панели (wide_drawer) получают кусок таймлайна с лицом — нужен cut-list (ищется в export/ сам).
"""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[1]
for p in (HERE, SKILLS / "reel" / "scripts", SKILLS / "motion-assets" / "scripts", SKILLS / "motion-assets" / "templates"):
    sys.path.insert(0, str(p))
import hf         # noqa: E402  (reel)
import stage      # noqa: E402
import timeline   # noqa: E402

SFX = SKILLS / "reel" / "scripts" / "sfx.py"
LANE = {"zoom": 1, "Д": 2, "Э": 2, "П": 2, "А": 3}
KIND = {"Д": "сцена", "Э": "поверх экрана", "П": "панель", "А": "акцент", "З": "зум на голове"}


def find_cutlist(work):
    found = sorted(Path(work).resolve().parent.glob("*.cutlist.json"))
    return found[0] if len(found) == 1 else None


def load_scenes(work):
    p = Path(work) / "scenes.py"
    if not p.exists():
        raise SystemExit(f"нет {p}: сцены ролика пишутся туда (образец — assets/scenes.example.py)")
    spec = importlib.util.spec_from_file_location("scenes", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["scenes"] = mod
    spec.loader.exec_module(mod)
    return list(mod.SCENES)


def type_of(sc):
    if sc["kind"] == "full":
        return "Д"
    if sc["kind"] == "over":
        return "Э"
    return {"wide_drawer": "П", "wide_follow": "Д"}.get(sc["template"], "А")


def collect(work, names=None):
    """→ [(spec, сдвиг начала)] по порядку на таймлайне."""
    out = []
    for fn in load_scenes(work):
        sc, shift = stage.fitted(fn)
        if names and sc["name"] not in names:
            continue
        sc["type"] = type_of(sc)
        out.append((sc, shift))
    return sorted(out, key=lambda x: x[0]["s0"])


def tpl_project(sc, d, cut, render=False):
    """Шаблон motion-assets → проект в d (без index.json библиотеки и без «зелёного» mp4)."""
    import _common
    import scene as ma
    tpl = ma.load_template(sc["template"])
    slots = dict(sc["slots"])
    if sc.get("face"):
        face = d / "face-q10.mp4"
        need = float(slots.get("close_at", slots.get("duration", 10))) + 1.5
        if render and not face.exists():
            if cut is None:
                raise SystemExit(f"{sc['name']}: панели нужен кусок таймлайна с лицом — укажи --cutlist")
            d.mkdir(parents=True, exist_ok=True)
            timeline.piece(timeline.load(cut), sc["s0"], need, face)
        slots["face"] = str(face) if face.exists() else ""
    merged = _common.merge_slots(tpl.SLOTS, slots)
    return ma.write_project(tpl, merged, stage.theme(), d, None, sc["layout"])


def mux_sfx(video, cues, total):
    """Звуки сцены по событиям → дорожка внутри клипа (mov — PCM, mp4 — AAC)."""
    if not cues:
        return
    cj, wav = video.with_name(video.stem + "-sfx.json"), video.with_name(video.stem + "-sfx.wav")
    cj.write_text(json.dumps([list(q) for q in cues]), encoding="utf-8")
    cmd = ["uv", "run", "-q", str(SFX), "cues", str(cj), "--out", str(wav), "--total", f"{total:.3f}"]
    if stage.settings_path():
        cmd += ["--settings", str(stage.settings_path())]
    subprocess.run(cmd, check=True, capture_output=True)
    tmp = video.with_name(video.stem + ".tmp" + video.suffix)
    acodec = ["-c:a", "pcm_s16le"] if video.suffix == ".mov" else ["-c:a", "aac", "-b:a", "192k"]
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", *acodec, "-shortest", str(tmp)], check=True)
    tmp.replace(video)
    cj.unlink()


def render_clip(d, name, alpha):
    """HyperFrames → mp4 (high) или .mov ProRes 4444 с альфой (если движок отдал без альфы — через webm)."""
    import scene as ma
    if not alpha:
        out = d / f"{name}.mp4"
        hf.render(d, out, "mp4", "high")
        return out
    out = d / f"{name}.mov"
    hf.render(d, out, "mov", "high")
    if not ma.has_alpha(ma.pix_fmt(out)):
        webm = d / f"{name}.webm"
        hf.render(d, webm, "webm", "high")
        subprocess.run(ma.prores_cmd(webm, out, "libvpx-vp9"), check=True)
        webm.unlink()
    return out


def entry(sc, work, clip):
    rel = clip.relative_to(work) if clip else None
    dur = hf.duration(clip) if clip and clip.exists() else sc.get("dur")
    return {"name": sc["name"], "type": sc["type"], "kind": sc["kind"], "template": sc.get("template"),
            "layout": sc.get("layout", "full" if sc["kind"] == "full" else "overlay"),
            "start": sc["s0"], "dur": round(dur, 3) if dur else None, "file": str(rel) if rel else None,
            "what": sc.get("what", ""), "lane": LANE[sc["type"]]}


def clip_path(work, sc, alpha_over=False):
    d = Path(work) / "clips" / sc["name"]
    alpha = (sc["kind"] == "over" and alpha_over) or sc.get("layout") == "overlay"
    return d, d / f"{sc['name']}.{'mov' if alpha else 'mp4'}", alpha


def over_bg(d, sc, cut):
    """Кусок таймлайна под вставкой поверх экрана (тот же кадр, что на V1): crf 10, кешируется по времени."""
    name = f"bg-{sc['s0']:.2f}-{sc['dur']:.2f}-q10.mp4"
    if not (d / name).exists():
        if cut is None:
            raise SystemExit(f"{sc['name']}: под вставкой нужен кусок таймлайна — укажи --cutlist")
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("bg-*.mp4"):
            old.unlink()
        timeline.piece(timeline.load(cut), sc["s0"], sc["dur"] + 0.1, d / name)
    return name


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work")
    ap.add_argument("names", nargs="*")
    ap.add_argument("--gaps", action="store_true")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--alpha", action="store_true", help="вставки поверх экрана — прозрачными .mov")
    ap.add_argument("--settings")
    ap.add_argument("--cutlist")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    stage.init(work, a.settings)
    cut = Path(a.cutlist) if a.cutlist else find_cutlist(work)
    items = collect(work, a.names)
    if a.gaps:
        total = 0.0
        for sc, _ in items:
            if sc["kind"] == "tpl":
                continue
            for g0, g1 in stage.idle_gaps(sc):
                total += g1 - g0
                print(f"{sc['name']:14s} {g0:5.1f}–{g1:5.1f} ({g1 - g0:3.1f} с) «{stage.WORDS.said(sc['s0'] + g0, sc['s0'] + g1)}»")
        print(f"пауз всего: {total:.0f} с")
        return
    entries = []
    for sc, shift in items:
        d, clip, alpha = clip_path(work, sc, a.alpha)
        if sc["kind"] == "tpl":
            built = tpl_project(sc, d, cut, a.render)
            sc["dur"], cues = built["duration"], built.get("sfx") or []
        else:
            bgv = over_bg(d, sc, cut) if sc["kind"] == "over" and not alpha else None
            stage.project(sc, d, bgv)
            cues = sc["sfx"]
            sc["layout"] = "overlay" if alpha else "full"
        note = f" (начало позже на {shift:.2f} с — было пусто)" if shift else ""
        print(f"{sc['type']} {sc['name']}: {timeline.mmss(sc['s0'])} · {sc['dur']:.1f} с{note}")
        if a.render:
            clip = render_clip(d, sc["name"], alpha)
            mux_sfx(clip, cues, sc["dur"])
            print(f"  рендер: {clip.relative_to(work)} ({clip.stat().st_size / 2 ** 20:.0f} МБ)")
        entries.append(entry(sc, work, clip))
    misses = sorted(set(stage.WORDS.misses))
    for n, k, w, how in misses:
        print(f"  ⚠ якорь ({n}, {k}) «{w}» вырезан → {how}")
    cj = work / "clips.json"
    old = json.loads(cj.read_text(encoding="utf-8")) if cj.exists() and a.names else []
    keep = [e for e in old if e["name"] not in {x["name"] for x in entries}]
    allc = sorted(keep + entries, key=lambda e: e["start"])
    cj.write_text(json.dumps(allc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"сцен: {len(entries)} · якорей заменено: {len(misses)} → {cj}")


if __name__ == "__main__":
    main()
