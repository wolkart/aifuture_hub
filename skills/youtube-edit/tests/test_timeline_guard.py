"""Время через cut-list и «на переходе зума ни реза»."""
import json

from conftest import cutlist_doc

import timeline
import zoom_guard


def test_spans_and_mapping():
    d = cutlist_doc([(0, 10), (12, 20), (25, 30)], 30)
    sp = timeline.spans(d)
    assert [(a, b) for a, b, *_ in sp] == [(0, 10), (10, 18), (18, 23)]
    assert timeline.total(sp) == 23
    assert timeline.to_tl(sp, 13) == 11
    assert timeline.to_tl(sp, 11) is None                  # вырезано
    assert timeline.to_src(sp, 11) == 13
    assert timeline.cut_points(sp) == [10, 18]


def test_src_spans_to_tl_merges_across_splices():
    sp = timeline.spans(cutlist_doc([(0, 10), (12, 20)], 20))
    # голова 5–15 записи: 5–10 и 12–15 → на таймлайне подряд 5–13
    assert timeline.src_spans_to_tl(sp, [(5, 15)]) == [(5, 13)]
    assert timeline.src_spans_to_tl(sp, [(10.5, 11.5)]) == []


def test_word_alive_by_its_middle():
    sp = timeline.spans(cutlist_doc([(0, 10), (12, 20)], 20))
    assert timeline.word_tl(sp, 12.5, 13.0) == (10.5, 11.0)
    assert timeline.word_tl(sp, 9.9, 10.1)[0] == 9.9       # середина на краю куска — живо, конец по краю
    assert timeline.word_tl(sp, 10.5, 11.0) == (None, None)


def test_words_keep_longform_numbering(tmp_path):
    words = {"words": [{"word": "Раз", "start": 0.5, "end": 0.9}, {"word": "два.", "start": 1.0, "end": 1.4},
                       {"word": "Вырезано", "start": 11.0, "end": 11.5},
                       {"word": "Три", "start": 13.0, "end": 13.4}]}
    wp = tmp_path / "w.words.json"
    wp.write_text(json.dumps(words), encoding="utf-8")
    res = timeline.words(cutlist_doc([(0, 10), (12, 20)], 20), wp, 0.0)
    assert [p["n"] for p in res] == [1, 2, 3]
    assert res[1]["words"][0][1] is None and res[1]["a"] is None
    assert res[2]["words"][0][1] == 11.0


def test_piece_cmd_concats_timeline_spans():
    d = cutlist_doc([(0, 10), (12, 20)], 20)
    cmd = timeline.piece_cmd(d, 8, 4, "/tmp/x.mp4")
    assert cmd.count("-i") == 2                              # два куска записи: 8–10 и 12–14
    i = cmd.index("-ss")
    assert cmd[i + 1] == "8.000" and cmd[cmd.index("-ss", i + 1) + 1] == "12.000"
    assert "concat=n=2" in cmd[cmd.index("-filter_complex") + 1]


# ── zoom_guard ──

def seg(a, b, action="cut"):
    return {"start": a, "end": b, "action": action, "source": "silence"}


def test_guard_shrinks_cut_away_from_transition():
    wins = [(10.0, 11.0)]
    out, log = zoom_guard.guard([seg(9.0, 10.5)], wins)        # конец реза в окне → кончается до окна
    assert (out[0]["start"], out[0]["end"]) == (9.0, 10.0)
    out, log = zoom_guard.guard([seg(10.5, 12.0)], wins)       # начало в окне → начинается после
    assert (out[0]["start"], out[0]["end"]) == (11.0, 12.0)


def test_guard_drops_cut_inside_or_tiny_and_keeps_covering():
    wins = [(10.0, 11.0)]
    out, log = zoom_guard.guard([seg(10.2, 10.8)], wins)
    assert out == [] and log[0][1] is None
    out, _ = zoom_guard.guard([seg(9.95, 10.5)], wins)         # остаётся 0,05 с < MIN_CUT
    assert out == []
    out, log = zoom_guard.guard([seg(9.0, 12.0)], wins)        # накрыл переход целиком — граница вне окна
    assert (out[0]["start"], out[0]["end"]) == (9.0, 12.0) and log == []


def test_guard_apply_is_idempotent():
    d = cutlist_doc([(0, 10.5), (12, 20)], 20)                  # рез 10,5–12 начинается в окне перехода
    nd, log = zoom_guard.apply(d, [(10.3, 11.0)])
    assert log
    nd2, log2 = zoom_guard.apply(nd, [(10.3, 11.0)])
    assert log2 == [] and nd2 == nd
