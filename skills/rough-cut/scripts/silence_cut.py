# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "scipy"]
# ///
"""Автономный режим «только тишина»: детект тишины → cut-list. Без whisper, без LLM.

Для чистой начитки/скринкаста, когда дубли и филлеры не нужны — режем только
паузы. Если задан отдельный звук (OBS), синхрон считается тут же (детерминированно).
Таймкоды cut-list — в координатах основного видео.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cutlist
import detect_silence
import probe


def build_silence_cutlist(video, audio=None, offset=0.0, sync_conf=1.0,
                          noise_db=-35.0, min_dur=0.8, pad=0.15, min_cut=0.4):
    vinfo = probe.probe(video)
    dur = vinfo["duration_s"]
    src_audio = audio or video
    raw = detect_silence.to_cuts(
        detect_silence.detect(src_audio, noise_db, min_dur), pad, min_cut)
    cuts = []
    for c in raw:  # координаты звука → координаты видео (video = audio − offset)
        s = max(0.0, c["start"] - offset)
        e = min(dur, c["end"] - offset)
        if e - s >= min_cut:
            cuts.append({"start": round(s, 3), "end": round(e, 3),
                         "action": "cut", "source": "silence",
                         "reason": f"тишина {e - s:.1f}с", "confidence": 0.9})
    meta = {
        "profile": "light",
        "scenario": "camera_plus_audio" if audio else "screencast",
        "inputs": {"video": str(video),
                   "audio": str(audio) if audio else None, "video2": None},
        "sync": {"offset_s": round(offset, 4), "confidence": round(sync_conf, 3)},
        "fps": vinfo["fps"], "width": vinfo["width"], "height": vinfo["height"],
        "duration_s": round(dur, 3),
    }
    return cutlist.from_cuts(meta, cuts)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video")
    ap.add_argument("--audio", default=None, help="отдельный звук OBS")
    ap.add_argument("--offset", type=float, default=None,
                    help="смещение звука, с; если не задано и есть --audio — считается")
    ap.add_argument("--noise-db", type=float, default=-35.0)
    ap.add_argument("--min-dur", type=float, default=0.8)
    ap.add_argument("--pad", type=float, default=0.15)
    ap.add_argument("--min-cut", type=float, default=0.4)
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    offset, conf = args.offset or 0.0, 1.0
    if args.audio and args.offset is None:
        import sync_offset
        offset, conf = sync_offset.find_offset(
            sync_offset.extract_pcm(args.video),
            sync_offset.extract_pcm(args.audio))
    d = build_silence_cutlist(args.video, args.audio, offset, conf,
                              args.noise_db, args.min_dur, args.pad, args.min_cut)
    out = Path(args.out or Path(args.video).with_suffix(".cutlist.json"))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    cut_n = sum(1 for s in d["segments"] if s["action"] == "cut")
    kept = sum(s["end"] - s["start"] for s in d["segments"] if s["action"] == "keep")
    print(f"cut-list: {out}")
    print(f"вырезано пауз: {cut_n}, останется ≈ {kept:.1f}с "
          f"(синхрон {offset:+.2f}с, уверенность {conf:.2f})")


if __name__ == "__main__":
    main()
