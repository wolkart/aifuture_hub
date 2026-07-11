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


def build(d):
    num, den = d["fps"]["num"], d["fps"]["den"]
    fx = ET.Element("fcpxml", version="1.9")
    res = ET.SubElement(fx, "resources")
    ET.SubElement(res, "format", id="r1", frameDuration=f"{den}/{num}s",
                  width=str(d["width"]), height=str(d["height"]))
    total = rt(d["duration_s"], num, den)
    ET.SubElement(res, "asset", id="r2",
                  src=Path(d["inputs"]["video"]).resolve().as_uri(),
                  hasVideo="1", hasAudio="1", format="r1",
                  start="0s", duration=total)
    audio = d["inputs"].get("audio")
    if audio:
        ET.SubElement(res, "asset", id="r3",
                      src=Path(audio).resolve().as_uri(),
                      hasAudio="1", start="0s", duration=total)
    video2 = d["inputs"].get("video2")
    if video2:
        ET.SubElement(res, "asset", id="r4",
                      src=Path(video2).resolve().as_uri(),
                      hasVideo="1", format="r1", start="0s", duration=total)

    seq = ET.SubElement(
        ET.SubElement(
            ET.SubElement(
                ET.SubElement(ET.SubElement(fx, "library"), "event",
                              name="rough-cut"),
                "project", name="rough-cut"),
            "sequence", format="r1"),
        "spine")

    off_s = d.get("sync", {}).get("offset_s", 0.0)
    tl = 0.0
    for seg in cutlist.timeline(d):
        dur = seg["end"] - seg["start"]
        clip = ET.SubElement(seq, "asset-clip", ref="r2", name="rough-cut",
                             offset=rt(tl, num, den),
                             start=rt(seg["start"], num, den),
                             duration=rt(dur, num, den))
        if seg["action"] == "speedup":
            ET.SubElement(clip, "marker", start=rt(seg["start"], num, den),
                          duration=rt(min(dur, 1.0), num, den),
                          value=f"SPEEDUP ×{seg['rate']} (rough-cut): "
                                f"{seg.get('reason', '')}")
        if audio:
            ET.SubElement(clip, "asset-clip", ref="r3", lane="-1",
                          offset=rt(seg["start"], num, den),
                          start=rt(seg["start"] + off_s, num, den),
                          duration=rt(dur, num, den))
        if video2:
            ET.SubElement(clip, "asset-clip", ref="r4", lane="1",
                          offset=rt(seg["start"], num, den),
                          start=rt(seg["start"], num, den),
                          duration=rt(dur, num, den))
        tl += dur
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
