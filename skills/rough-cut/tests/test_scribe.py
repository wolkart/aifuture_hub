import json
import subprocess
import sys
from pathlib import Path

import scribe

SCRIPTS = Path(__file__).parent.parent / "scripts"

RESP = {"language_code": "ru", "text": "Ну э-э сейчас покажу (смех)", "audio_duration_secs": 7.2,
        "words": [{"text": "Ну", "start": 0.1, "end": 0.3, "type": "word", "logprob": -0.1},
                  {"text": " ", "start": 0.3, "end": 0.35, "type": "spacing", "logprob": 0},
                  {"text": "э-э", "start": 0.35, "end": 0.9, "type": "word", "logprob": -0.4},
                  {"text": "сейчас", "start": 1.0, "end": 1.4, "type": "word", "logprob": -0.05},
                  {"text": "покажу", "start": 1.45, "end": 1.9, "type": "word", "logprob": -0.05},
                  {"text": "(смех)", "start": 2.0, "end": 2.6, "type": "audio_event", "logprob": -0.2},
                  {"text": "x", "start": None, "end": None, "type": "word", "logprob": -1}]}


def test_normalize_keeps_fillers_drops_spacing_splits_events():
    out = scribe.normalize(RESP)
    assert [w["word"] for w in out["words"]] == ["Ну", "э-э", "сейчас", "покажу"]
    assert out["events"] == [{"word": "(смех)", "start": 2.0, "end": 2.6}]
    assert out["backend"] == "scribe"


def test_fields_keep_disfluencies():
    f = scribe.fields("ru")
    assert f["no_verbatim"] == "false" and f["model_id"] == "scribe_v2"
    assert f["timestamps_granularity"] == "word" and f["language_code"] == "ru"
    assert "language_code" not in scribe.fields()


def test_multipart_body():
    body, ctype = scribe.multipart({"model_id": "scribe_v2"}, "file", "a.ogg", b"OGG")
    boundary = ctype.split("boundary=")[1]
    assert body.startswith(f"--{boundary}".encode()) and body.endswith(f"--{boundary}--\r\n".encode())
    assert b'name="model_id"\r\n\r\nscribe_v2' in body and b'filename="a.ogg"' in body and b"OGG" in body


def test_api_key_env_wins_over_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("ELEVENLABS_API_KEY=from-file\n")
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert scribe.api_key(env) == "from-file"
    monkeypatch.setenv("ELEVENLABS_API_KEY", "from-env")
    assert scribe.api_key(env) == "from-env"
    monkeypatch.delenv("ELEVENLABS_API_KEY")
    assert scribe.api_key(tmp_path / "none.env") is None


def test_cost():
    assert scribe.cost(3600) == 0.22 and scribe.cost(120) == 0.0073


def test_cli_without_key_explains(tmp_path, monkeypatch):
    env = dict(__import__("os").environ, ELEVENLABS_API_KEY="", HOME=str(tmp_path))
    r = subprocess.run([sys.executable, str(SCRIPTS / "transcribe.py"), "x.wav", "--backend", "scribe"],
                       capture_output=True, text=True, env=env, cwd=tmp_path)
    if scribe.api_key():  # у разработчика ключ может лежать в .env скилла — тогда тест не о том
        return
    assert r.returncode != 0 and "ELEVENLABS_API_KEY" in r.stderr
