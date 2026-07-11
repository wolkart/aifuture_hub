import transcribe


def test_pick_backend():
    assert transcribe.pick_backend("darwin", "arm64") == "mlx"
    assert transcribe.pick_backend("darwin", "x86_64") == "faster"
    assert transcribe.pick_backend("linux", "x86_64") == "faster"
    assert transcribe.pick_backend("linux", "x86_64", override="mlx") == "mlx"


def test_normalize_mlx():
    raw = {"text": " привет мир",
           "segments": [{"words": [
               {"word": " привет", "start": 0.1, "end": 0.5},
               {"word": " мир", "start": 0.6, "end": 0.9}]}]}
    out = transcribe.normalize_mlx(raw)
    assert out["words"] == [{"word": "привет", "start": 0.1, "end": 0.5},
                            {"word": "мир", "start": 0.6, "end": 0.9}]


def test_normalize_faster():
    class W:
        def __init__(self, word, start, end):
            self.word, self.start, self.end = word, start, end

    class S:
        def __init__(self, text, words):
            self.text, self.words = text, words

    segs = [S(" привет мир", [W(" привет", 0.1, 0.5), W(" мир", 0.6, 0.9)])]
    out = transcribe.normalize_faster(segs)
    assert out["text"] == "привет мир"
    assert out["words"][1] == {"word": "мир", "start": 0.6, "end": 0.9}
