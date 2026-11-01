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


def _fake(name, key, result=None, fail=None):
    import types
    m = types.ModuleType(name)
    m.api_key = lambda: key

    def run(audio, language):
        if fail:
            raise SystemExit(fail)
        return result
    m.run = run
    return m


def test_cloud_chain_falls_back_to_deepgram(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "scribe", _fake("scribe", "k", fail="scribe: HTTP 401 — quota_exceeded"))
    monkeypatch.setitem(sys.modules, "deepgram", _fake("deepgram", "k", result={"backend": "deepgram"}))
    res, errors = transcribe.run_cloud("a.wav", "ru", transcribe.CLOUD_CHAIN["scribe"])
    assert res == {"backend": "deepgram"} and "quota_exceeded" in errors[0]


def test_cloud_chain_empty_when_all_fail(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "scribe", _fake("scribe", None))
    monkeypatch.setitem(sys.modules, "deepgram", _fake("deepgram", "k", fail="deepgram: HTTP 402"))
    res, errors = transcribe.run_cloud("a.wav", "ru", transcribe.CLOUD_CHAIN["scribe"])
    assert res is None and errors == ["scribe: нет ключа", "deepgram: HTTP 402"]
