import sync_offset


def test_offset_found(media_dir):
    ref = sync_offset.extract_pcm(media_dir / "sync_ref.wav")
    target = sync_offset.extract_pcm(media_dir / "sync_shifted.wav")
    off, conf = sync_offset.find_offset(ref, target)
    assert abs(off - 1.5) < 0.05
    assert conf > 0.5


def test_offset_zero_for_identical(media_dir):
    ref = sync_offset.extract_pcm(media_dir / "sync_ref.wav")
    off, conf = sync_offset.find_offset(ref, ref)
    assert abs(off) < 0.01
    assert conf > 0.9
