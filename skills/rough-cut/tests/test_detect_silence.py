import detect_silence


def test_detect_finds_gap(media_dir):
    ivs = detect_silence.detect(media_dir / "tone_gap.wav")
    assert len(ivs) == 1
    assert abs(ivs[0]["start"] - 1.0) < 0.3
    assert abs(ivs[0]["end"] - 4.0) < 0.3


def test_to_cuts_pads_inward():
    cuts = detect_silence.to_cuts([{"start": 1.0, "end": 4.0}], pad=0.15)
    assert cuts == [{"start": 1.15, "end": 3.85}]


def test_to_cuts_drops_short():
    assert detect_silence.to_cuts([{"start": 1.0, "end": 1.5}], pad=0.15,
                                  min_cut=0.4) == []
