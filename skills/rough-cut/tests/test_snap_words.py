import json
import subprocess
import sys
from pathlib import Path

import snap_words

SCRIPTS = Path(__file__).parent.parent / "scripts"


def test_word_starting_in_silence_moves_to_voice():
    db_at = lambda t: -20.0 if t >= 1.0 else -90.0  # голос с 1.0 с
    words, moved = snap_words.snap([{"word": "Привет", "start": 0.6, "end": 1.4}], db_at)
    assert moved == 1
    assert abs(words[0]["start"] - 0.98) < 0.02


def test_word_inside_speech_untouched():
    db_at = lambda t: -20.0
    w = [{"word": "раз", "start": 1.0, "end": 1.3}, {"word": "два", "start": 1.3, "end": 1.6}]
    words, moved = snap_words.snap(w, db_at)
    assert moved == 0 and words == w


def test_tail_in_silence_trimmed():
    db_at = lambda t: -20.0 if t < 1.5 else -90.0  # голос кончился на 1.5
    words, _ = snap_words.snap([{"word": "конец", "start": 1.0, "end": 2.3}], db_at)
    assert words[0]["end"] < 1.6


def test_cli_on_wav(media_dir, tmp_path):
    # tone_gap.wav: тон 0–1, тишина 1–4, тон 4–5; «слово» Whisper поставил на 3.6
    src = tmp_path / "w.json"
    src.write_text(json.dumps({"text": "x", "words": [{"word": "x", "start": 3.6, "end": 4.6}]}))
    subprocess.run([sys.executable, str(SCRIPTS / "snap_words.py"), str(src),
                    str(media_dir / "tone_gap.wav")], check=True)
    w = json.loads(src.read_text())["words"][0]
    assert abs(w["start"] - 3.98) < 0.03
