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


def test_confidence_low_when_target_is_pure_noise(media_dir):
    """Нет общего сигнала → пик не выделяется → низкая уверенность."""
    import numpy as np
    ref = sync_offset.extract_pcm(media_dir / "sync_ref.wav")
    rng = np.random.default_rng(1)
    unrelated = rng.standard_normal(len(ref)).astype(np.float32)
    _off, conf = sync_offset.find_offset(ref, unrelated)
    assert conf < 0.5
