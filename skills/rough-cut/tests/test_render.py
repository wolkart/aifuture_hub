import subprocess

import pytest

import cutlist
import probe
import render


def make_cutlist(media_dir, cuts):
    info = probe.probe(media_dir / "clip.mp4")
    meta = {"profile": "light", "scenario": "screencast",
            "inputs": {"video": str(media_dir / "clip.mp4"),
                       "audio": None, "video2": None},
            "sync": {"offset_s": 0.0, "confidence": 1.0},
            "fps": info["fps"], "width": info["width"],
            "height": info["height"],
            "duration_s": round(info["duration_s"], 3)}
    return cutlist.from_cuts(meta, cuts)


def test_render_cuts_duration(media_dir, tmp_path):
    d = make_cutlist(media_dir, [
        {"start": 2.0, "end": 4.0, "action": "cut", "source": "silence",
         "reason": "тишина", "confidence": 0.95}])
    out = tmp_path / "out.mp4"
    subprocess.run(render.build_cmd(d, out), check=True)
    assert abs(probe.probe(out)["duration_s"] - 4.0) < 0.3


def test_render_speedup_shrinks(media_dir, tmp_path):
    d = make_cutlist(media_dir, [
        {"start": 2.0, "end": 6.0, "action": "speedup", "rate": 4,
         "source": "screencast", "reason": "загрузка", "confidence": 0.8}])
    out = tmp_path / "out.mp4"
    subprocess.run(render.build_cmd(d, out), check=True)
    # 2с как есть + 4с/4 = 3с
    assert abs(probe.probe(out)["duration_s"] - 3.0) < 0.3


def test_render_refuses_overwrite_input(media_dir):
    d = make_cutlist(media_dir, [])
    with pytest.raises(ValueError):
        render.build_cmd(d, media_dir / "clip.mp4")
