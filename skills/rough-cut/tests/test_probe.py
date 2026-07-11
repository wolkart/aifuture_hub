import probe


def test_rotation_of_side_data():
    st = {"side_data_list": [{"side_data_type": "Display Matrix",
                              "rotation": 90}]}
    assert probe.rotation_of(st) == 90


def test_rotation_of_tags():
    assert probe.rotation_of({"tags": {"rotate": "270"}}) == 270


def test_rotation_of_none():
    assert probe.rotation_of({}) == 0


def test_oriented_dims_swaps_on_quarter_turn():
    assert probe.oriented_dims(1920, 1080, 90) == (1080, 1920)
    assert probe.oriented_dims(1920, 1080, -90) == (1080, 1920)
    assert probe.oriented_dims(1920, 1080, 270) == (1080, 1920)


def test_oriented_dims_keeps_on_flat():
    assert probe.oriented_dims(1920, 1080, 0) == (1920, 1080)
    assert probe.oriented_dims(1920, 1080, 180) == (1920, 1080)


def test_parse_streams_applies_rotation():
    data = {"format": {"duration": "10.0"},
            "streams": [{"codec_type": "video", "r_frame_rate": "50/1",
                         "width": 1920, "height": 1080,
                         "side_data_list": [{"rotation": 90}]},
                        {"codec_type": "audio"}]}
    info = probe.parse_streams(data)
    assert (info["width"], info["height"]) == (1080, 1920)
    assert info["has_audio"]


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
