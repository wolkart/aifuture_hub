#!/usr/bin/env python3
"""cut-list → FCPXML 1.9 (импорт в DaVinci Resolve). Только stdlib.

Резы «мягкие»: клипы ссылаются на исходники, границы двигаются в Resolve.
speedup — обычный клип + маркер SPEEDUP ×N (ретайм руками: импорт timeMap
в Resolve ненадёжен). Отдельный звук — connected clip lane=-1 со сдвигом
sync.offset_s. Мультикам (inputs.video2) — connected clip lane=1.
"""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import cutlist


def rt(seconds, num, den):
    """Секунды → рациональное время FCPXML, выровненное по границе кадра."""
    frames = round(seconds * num / den)
    return f"{frames * den}/{num}s"


def _asset(res, rid, name, path, total, **attrs):
    """Asset с медиа-ссылкой через <media-rep> (требование FCPXML 1.9 / Resolve)."""
    a = ET.SubElement(res, "asset", id=rid, name=name,
                      start="0s", duration=total, **attrs)
    ET.SubElement(a, "media-rep", kind="original-media",
                  src=Path(path).resolve().as_uri())
    return a


def build(d):
    num, den = d["fps"]["num"], d["fps"]["den"]
    fx = ET.Element("fcpxml", version="1.9")
    res = ET.SubElement(fx, "resources")
    ET.SubElement(res, "format", id="r1", name=f"FFVideoFormat{d['height']}p",
                  frameDuration=f"{den}/{num}s",
                  width=str(d["width"]), height=str(d["height"]))
    total = rt(d["duration_s"], num, den)
    _asset(res, "r2", "camera", d["inputs"]["video"], total,
           hasVideo="1", hasAudio="1", audioSources="1", audioChannels="2",
           format="r1")
    audio = d["inputs"].get("audio")
    if audio:
        _asset(res, "r3", "obs-audio", audio, total,
               hasAudio="1", audioSources="1", audioChannels="2")
    video2 = d["inputs"].get("video2")
    if video2:
        _asset(res, "r4", "camera2", video2, total,
               hasVideo="1", format="r1")

    seq = ET.SubElement(
        ET.SubElement(
            ET.SubElement(
                ET.SubElement(ET.SubElement(fx, "library"), "event",
                              name="rough-cut"),
                "project", name="rough-cut"),
            "sequence", format="r1"),
        "spine")

    off_s = d.get("sync", {}).get("offset_s", 0.0)
    # Всё в целых кадрах: позиция и длина клипа — от кадров его краёв в исходнике.
    # Округлять секунды позиции и длины по отдельности нельзя: копится зазор или
    # нахлёст в кадр на склейке (на 66-минутном уроке — 109 стыков из 438).
    frame = lambda s: round(s * num / den)
    at = lambda f: f"{f * den}/{num}s"
    tl = 0
    for seg in cutlist.timeline(d):
        s, e = frame(seg["start"]), frame(seg["end"])
        if e <= s:
            continue
        clip = ET.SubElement(seq, "asset-clip", ref="r2", name="rough-cut",
                             offset=at(tl), start=at(s), duration=at(e - s))
        if seg["action"] == "speedup":
            ET.SubElement(clip, "marker", start=at(s),
                          duration=at(min(e - s, frame(1.0))),
                          value=f"SPEEDUP ×{seg['rate']} (rough-cut): "
                                f"{seg.get('reason', '')}")
        if audio:
            ET.SubElement(clip, "asset-clip", ref="r3", lane="-1",
                          offset=at(s), start=rt(seg["start"] + off_s, num, den),
                          duration=at(e - s))
        if video2:
            ET.SubElement(clip, "asset-clip", ref="r4", lane="1",
                          offset=at(s), start=at(s), duration=at(e - s))
        tl += e - s
    return fx


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cutlist_path")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    d = cutlist.load(args.cutlist_path)
    out = Path(args.out or Path(args.cutlist_path).with_suffix(".fcpxml"))
    tree = ET.ElementTree(build(d))
    ET.indent(tree)
    tree.write(out, encoding="utf-8", xml_declaration=True)
    doctype_body = out.read_text(encoding="utf-8").split("\n", 1)
    out.write_text(doctype_body[0] + "\n<!DOCTYPE fcpxml>\n" + doctype_body[1],
                   encoding="utf-8")
    print(f"FCPXML: {out}")


if __name__ == "__main__":
    main()
