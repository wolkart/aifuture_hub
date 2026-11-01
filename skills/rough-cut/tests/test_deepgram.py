import deepgram

RESP = {"metadata": {"duration": 7.2},
        "results": {"channels": [{"alternatives": [{
            "transcript": "ну сейчас покажу",
            "words": [{"word": "ну", "punctuated_word": "Ну", "start": 0.1, "end": 0.3},
                      {"word": "сейчас", "punctuated_word": "сейчас", "start": 1.0, "end": 1.4},
                      {"word": "покажу", "punctuated_word": "покажу.", "start": 1.45, "end": 1.9},
                      {"word": "", "start": 2.0, "end": 2.1}]}]}]}}


def test_normalize_takes_punctuated_words_and_drops_empty():
    out = deepgram.normalize(RESP)
    assert [w["word"] for w in out["words"]] == ["Ну", "сейчас", "покажу."]
    assert out["words"][0] == {"word": "Ну", "start": 0.1, "end": 0.3}
    assert out["backend"] == "deepgram" and out["events"] == []


def test_params_default_russian_with_fillers():
    q = deepgram.params()
    assert q["model"] == "nova-3" and q["language"] == "ru" and q["filler_words"] == "true"
    assert deepgram.params("en")["language"] == "en"


def test_api_key_env_wins_over_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("DEEPGRAM_API_KEY=from-file\n")
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    assert deepgram.api_key(env) == "from-file"
    monkeypatch.setenv("DEEPGRAM_API_KEY", "from-env")
    assert deepgram.api_key(env) == "from-env"
    monkeypatch.delenv("DEEPGRAM_API_KEY")
    assert deepgram.api_key(tmp_path / "none.env") is None


def test_cost():
    assert deepgram.cost(3600) == 0.26
