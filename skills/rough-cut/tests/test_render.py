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


def test_fades_on_every_kept_piece():
    assert render.fades(1.0) == ",afade=t=in:d=0.008,afade=t=out:st=0.9920:d=0.008"
    assert render.fades(0.01) == ""  # кусок короче двух затуханий — без них


def test_cmd_has_fade_per_keep_segment(media_dir, tmp_path):
    import cutlist
    d = cutlist.from_cuts({"version": 1, "profile": "light", "scenario": "camera_plus_audio",
                           "inputs": {"video": str(media_dir / "clip.mp4"), "audio": None, "video2": None},
                           "fps": 30, "width": 320, "height": 240, "duration_s": 6.0},
                          [{"start": 2.0, "end": 3.0, "action": "cut", "source": "silence",
                            "reason": "тишина", "confidence": 0.9}])
    fc = render.build_cmd(d, tmp_path / "o.mp4")
    graph = fc[fc.index("-filter_complex") + 1]
    assert graph.count("afade=t=in") == 2 and graph.count("afade=t=out") == 2
