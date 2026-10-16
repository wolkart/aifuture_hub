import json
import subprocess
import sys
from pathlib import Path

import pytest

import longform as lf

SCRIPTS = Path(__file__).parent.parent / "scripts"


def W(spec):
    """'слово@start-end ...' → слова."""
    out = []
    for tok in spec.split():
        text, _, t = tok.partition("@")
        a, b = (float(x) for x in t.split("-"))
        out.append({"text": text, "start": a, "end": b})
    return out


WORDS = W("Привет,@0.5-0.9 сегодня@1.0-1.4 ставим@1.5-1.9 бота.@2.0-2.4 "
          "Вот.@4.0-4.3 "
          "Где@6.0-6.3 тут@6.4-6.6 настройки,@6.7-7.3 что-то@7.4-7.8 поменялось.@7.9-8.5 "
          "э-э@9.5-9.9 Открываем@10.5-11.0 терминал.@11.1-11.5")


def test_phrases_break_on_pause_and_sentence():
    phr = lf.phrases(WORDS)
    assert [p["text"] for p in phr] == ["Привет, сегодня ставим бота.", "Вот.",
                                         "Где тут настройки, что-то поменялось.", "э-э", "Открываем терминал."]
    assert phr[0]["n"] == 1 and phr[0]["a"] == 0.5 and phr[0]["b"] == 2.4


def test_anchors_and_phrase_spans():
    phr = lf.phrases(WORDS)
    assert lf.anchor("a:1", phr, 20) == pytest.approx(2.52)
    assert lf.anchor("b:3", phr, 20) == pytest.approx(5.88)
    assert lf.anchor("t:3.5", phr, 20) == 3.5
    assert lf.anchor("w:3:2", phr, 20) == pytest.approx(6.37)
    a, b = lf.span({"phrases": [2, 3]}, phr, 20)   # «Вот.» + блуждание
    assert a == pytest.approx(2.52) and b == pytest.approx(9.38)
    assert lf.span({"phrases": [5, 5]}, phr, 20)[1] == 20   # последняя фраза — до конца записи
    with pytest.raises(ValueError):
        lf.anchor("z:1", phr, 20)


def test_filler_cuts_only_clear_fillers():
    cuts = lf.filler_cuts(W("ну@0-0.2 э-э@0.3-0.7 Ммм...@0.8-1.2 вот@1.3-1.5 эм,@1.6-1.8"))
    assert [c["reason"] for c in cuts] == ["запинка «э-э»", "запинка «Ммм...»", "запинка «эм,»"]


def test_merge_keeps_semantic_reason():
    cuts = lf.merge([
        {"start": 1.0, "end": 3.0, "action": "cut", "source": "silence", "reason": "тишина", "confidence": 0.9},
        {"start": 2.5, "end": 6.0, "action": "cut", "source": "semantic", "reason": "блуждание",
         "confidence": 0.8, "n": 1, "quote": "Где тут"},
        {"start": 8.0, "end": 9.0, "action": "cut", "source": "filler", "reason": "э-э", "confidence": 0.9}])
    assert len(cuts) == 2
    assert cuts[0]["start"] == 1.0 and cuts[0]["end"] == 6.0 and cuts[0]["source"] == "semantic"
    assert cuts[0]["n"] == 1 and cuts[0]["quote"] == "Где тут"


def test_semantic_numbering_keep_and_returned():
    phr = lf.phrases(WORDS)
    plan = {"cuts": [{"phrases": [3, 3], "why": "блуждание"}, {"phrases": [2, 2], "why": "Вот."}], "keep": [2]}
    sem, returned = lf.semantic_cuts(plan, phr, 20)
    assert [c["n"] for c in sem] == [1] and sem[0]["reason"] == "Вот."        # номера — по времени
    assert sem[0]["quote"] == "Вот."
    assert [(n, why) for n, _, why in returned] == [(2, "блуждание")]


def test_out_time():
    segs = [{"start": 0, "end": 2, "action": "keep"}, {"start": 2, "end": 5, "action": "cut"},
            {"start": 5, "end": 9, "action": "speedup", "rate": 4}, {"start": 9, "end": 10, "action": "keep"}]
    assert lf.out_time(segs, 1.5) == 1.5 and lf.out_time(segs, 4) == 2.0
    assert lf.out_time(segs, 9.5) == pytest.approx(3.5) and lf.out_time(segs, 99) == pytest.approx(4.0)


def test_lines_text_marks_pauses_and_chunks():
    text, chunks = lf.lines_text(lf.phrases(WORDS))
    assert any("пауза 1.6 с" in t for t in text)
    assert chunks[0][0] == 1 and chunks[0][2] == 0.0


def test_build_and_restore_cli(tmp_path):
    clip = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=12:size=320x240:rate=30",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=12", "-c:v", "libx264", "-preset",
                    "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(clip)], check=True)
    words = tmp_path / "w.words.json"
    words.write_text(json.dumps({"text": "", "words": [
        {"word": w["text"], "start": w["start"], "end": w["end"]} for w in WORDS]}, ensure_ascii=False))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"cuts": [{"phrases": [3, 3], "why": "блуждание по настройкам"}],
                                "decide": [{"phrases": [5, 5], "why": "анонс клуба"}]}, ensure_ascii=False))
    out = tmp_path / "clip.cutlist.json"
    r = subprocess.run([sys.executable, str(SCRIPTS / "longform.py"), "build", str(clip),
                        "--words", str(words), "--plan", str(plan), "-o", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("Было 0:12.0 → стало")
    assert "1." in r.stdout and "блуждание по настройкам" in r.stdout and "Не резал — решай сам" in r.stdout
    d = json.loads(out.read_text())
    assert any(s.get("source") == "semantic" for s in d["segments"])
    assert any(s.get("source") == "filler" for s in d["segments"])          # «э-э» из расшифровки
    assert (tmp_path / "clip.report.md").exists()
    subprocess.run([sys.executable, str(SCRIPTS / "longform.py"), "restore", str(plan), "1"], check=True,
                   capture_output=True)
    assert json.loads(plan.read_text())["keep"] == [1]
    r = subprocess.run([sys.executable, str(SCRIPTS / "longform.py"), "build", str(clip),
                        "--words", str(words), "--plan", str(plan), "-o", str(out)],
                       capture_output=True, text=True)
    assert "Возвращено по просьбе" in r.stdout
    assert not any(s.get("source") == "semantic" for s in json.loads(out.read_text())["segments"])
