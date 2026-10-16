import pytest

import longform as lf
import shorts


def W(spec):
    out, t = [], 0.0
    for sent in spec.split("|"):
        for tok in sent.split():
            out.append({"text": tok, "start": round(t, 2), "end": round(t + 0.4, 2)})
            t += 0.5
        t += 1.0          # пауза между предложениями — новая фраза
    return out


WORDS = W("Почему бот, а не n8n? | Потому что бот работает сам. | И вот как я уже говорил, "
          "это просто | Конец мысли.")


def test_checks_flag_lean_start_backref_and_cut_off_end():
    phr = lf.phrases(WORDS)
    warn, _ = shorts.checks(phr, phr[0]["a"], phr[1]["b"])
    assert any("длина" in w for w in warn) and not any("начало" in w for w in warn)
    warn, _ = shorts.checks(phr, phr[2]["a"], phr[2]["b"])
    assert any("начало опирается" in w for w in warn)
    assert any("отсылка назад" in w for w in warn)
    assert any("конец без точки" in w for w in warn)


def test_table_lists_first_and_last_phrase():
    phr = lf.phrases(WORDS)
    t = shorts.table(phr, {"shorts": [{"phrases": [1, 2], "title": "почему бот"}]}, 30.0)
    assert "| 1 |" in t and "почему бот" in t and "Почему бот, а не n8n?" in t and "Потому что бот работает сам." in t


def test_short_cutlist_keeps_only_span_minus_inner_cuts():
    base = {"version": 1, "profile": "light", "scenario": "screencast",
            "inputs": {"video": "/v.mp4", "audio": None, "video2": None}, "sync": {"offset_s": 0, "confidence": 1},
            "fps": 30, "width": 1920, "height": 1080, "duration_s": 100.0,
            "segments": [{"start": 0, "end": 40, "action": "keep"},
                         {"start": 40, "end": 45, "action": "cut", "source": "silence", "reason": "т", "confidence": 0.9},
                         {"start": 45, "end": 100, "action": "keep"}]}
    words = [{"text": "э-э", "start": 50.0, "end": 50.4}]
    d = shorts.short_cutlist(base, words, 30.0, 70.0)
    keeps = [(s["start"], s["end"]) for s in d["segments"] if s["action"] == "keep"]
    assert keeps[0][0] == pytest.approx(30.0) and keeps[-1][1] == pytest.approx(70.0)
    assert lf.out_time(d["segments"], 101) == pytest.approx(40 - 5 - 0.46, abs=0.01)
