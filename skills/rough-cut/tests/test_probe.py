import probe


def test_probe_video(media_dir):
    info = probe.probe(media_dir / "clip.mp4")
    assert info["has_video"] and info["has_audio"]
    assert info["fps"] == {"num": 30, "den": 1}
    assert info["width"] == 320 and info["height"] == 240
    assert abs(info["duration_s"] - 6.0) < 0.5


def test_probe_audio_only(media_dir):
    info = probe.probe(media_dir / "tone_gap.wav")
    assert info["has_audio"] and not info["has_video"]
    assert abs(info["duration_s"] - 5.0) < 0.1
