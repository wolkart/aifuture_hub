from pathlib import Path

import extract_frames


def test_frame_times_three_for_long():
    assert extract_frames.frame_times(1.0, 5.0) == [1.2, 3.0, 4.8]


def test_frame_times_one_for_short():
    assert extract_frames.frame_times(1.0, 1.3) == [1.15]


def test_extract_writes_frames(media_dir, tmp_path):
    res = extract_frames.extract(media_dir / "clip.mp4",
                                 [{"start": 1.0, "end": 5.0}], tmp_path)
    assert len(res) == 1
    assert len(res[0]["frames"]) == 3
    for p in res[0]["frames"]:
        assert Path(p).stat().st_size > 0
