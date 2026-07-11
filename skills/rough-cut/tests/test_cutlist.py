import pytest

import cutlist


def make_meta():
    return {"profile": "light", "scenario": "camera_plus_audio",
            "inputs": {"video": "cam.mp4", "audio": "obs.wav", "video2": None},
            "sync": {"offset_s": 1.5, "confidence": 0.9},
            "fps": {"num": 30, "den": 1}, "width": 1920, "height": 1080,
            "duration_s": 10.0}


def test_from_cuts_tiles_full_duration():
    d = cutlist.from_cuts(make_meta(), [
        {"start": 2.0, "end": 4.0, "action": "cut", "source": "silence",
         "reason": "тишина", "confidence": 0.95}])
    acts = [(s["start"], s["end"], s["action"]) for s in d["segments"]]
    assert acts == [(0.0, 2.0, "keep"), (2.0, 4.0, "cut"), (4.0, 10.0, "keep")]
    cutlist.validate(d)  # не бросает


def test_validate_rejects_overlap():
    d = cutlist.from_cuts(make_meta(), [])
    d["segments"] = [{"start": 0.0, "end": 6.0, "action": "keep"},
                     {"start": 5.0, "end": 10.0, "action": "keep"}]
    with pytest.raises(ValueError):
        cutlist.validate(d)


def test_validate_rejects_gap():
    d = cutlist.from_cuts(make_meta(), [])
    d["segments"] = [{"start": 0.0, "end": 4.0, "action": "keep"},
                     {"start": 6.0, "end": 10.0, "action": "keep"}]
    with pytest.raises(ValueError):
        cutlist.validate(d)


def test_validate_requires_rate_for_speedup():
    d = cutlist.from_cuts(make_meta(), [])
    d["segments"] = [{"start": 0.0, "end": 10.0, "action": "speedup",
                      "source": "screencast", "reason": "x", "confidence": 1}]
    with pytest.raises(ValueError):
        cutlist.validate(d)


def test_timeline_skips_cuts():
    d = cutlist.from_cuts(make_meta(), [
        {"start": 2.0, "end": 4.0, "action": "cut", "source": "silence",
         "reason": "тишина", "confidence": 0.95}])
    assert [s["start"] for s in cutlist.timeline(d)] == [0.0, 4.0]
