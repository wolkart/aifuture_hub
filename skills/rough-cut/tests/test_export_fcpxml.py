import xml.etree.ElementTree as ET

import cutlist
import export_fcpxml


def make_cutlist():
    meta = {"profile": "full", "scenario": "camera_plus_audio",
            "inputs": {"video": "cam.mp4", "audio": "obs.wav", "video2": None},
            "sync": {"offset_s": 1.5, "confidence": 0.9},
            "fps": {"num": 30, "den": 1}, "width": 1920, "height": 1080,
            "duration_s": 10.0}
    return cutlist.from_cuts(meta, [
        {"start": 2.0, "end": 4.0, "action": "cut", "source": "silence",
         "reason": "тишина", "confidence": 0.95},
        {"start": 6.0, "end": 8.0, "action": "speedup", "rate": 8,
         "source": "screencast", "reason": "загрузка", "confidence": 0.7}])


def test_rt_frame_aligned():
    assert export_fcpxml.rt(1.0, 30, 1) == "30/30s"
    assert export_fcpxml.rt(0.5, 30000, 1001) == "15015/30000s"  # 15 кадров NTSC


def test_build_valid_xml():
    root = export_fcpxml.build(make_cutlist())
    assert root.tag == "fcpxml" and root.get("version") == "1.9"
    ET.fromstring(ET.tostring(root))


def test_spine_clips_match_timeline():
    root = export_fcpxml.build(make_cutlist())
    spine = root.find(".//spine")
    clips = spine.findall("asset-clip")
    # тайлинг: keep 0–2, cut 2–4, keep 4–6, speedup 6–8, keep 8–10 → 4 клипа
    assert len(clips) == 4


def test_speedup_gets_marker():
    root = export_fcpxml.build(make_cutlist())
    markers = root.findall(".//asset-clip/marker")
    assert len(markers) == 1
    assert "SPEEDUP ×8" in markers[0].get("value")


def test_audio_connected_with_offset():
    root = export_fcpxml.build(make_cutlist())
    laned = [c for c in root.findall(".//asset-clip/asset-clip")
             if c.get("lane") == "-1"]
    assert len(laned) == 4  # звук приклеен к каждому клипу таймлайна
