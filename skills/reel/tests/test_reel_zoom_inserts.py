import pytest

import inserts as ins
import words as wmod
import zoom


def spans(n, length=2.0):
    return [(round(i * length, 3), round((i + 1) * length, 3)) for i in range(n)]


@pytest.mark.parametrize("length", [0.9, 1.5, 2.0, 3.0])
def test_every_cut_changes_scale_by_at_least_step(words, length):
    rows = zoom.plan(spans(14, length), words, punch=["бесплатно", "сам"])
    assert all(j >= 0.1 - 1e-9 for j in zoom.jumps(rows)), zoom.jumps(rows)


def test_punch_word_once_and_on_word(words):
    sp = [(0.0, 30.0)]
    rows = zoom.plan(sp + [(30.0, 31.0)], words, punch=["бесплатно"])
    t = wmod.find(words, "бесплатно.")["start"]
    assert f"{t:.3f}" in rows[0]["js"][1] and "вжух" in rows[0]["kind"]
    assert rows[0]["end"] == pytest.approx(1.12)


def test_plate_window_keeps_zoom_small(words):
    rows = zoom.plan(spans(4), words, plates=[(1.9, 4.1)])
    assert rows[1]["plate"] and rows[1]["end"] <= zoom.PLATE_MAX
    assert rows[1]["base"] == 1.0


def test_face_center_median_and_default():
    faces = [(0.1, 0.4, 0.5), (0.2, 0.6, 0.5), (0.3, 0.5, 0.4), (5.0, 0.9, 0.9)]
    assert zoom.face_center(faces, 0.0, 1.0) == (0.5, 0.5)
    assert zoom.face_center(faces, 2.0, 3.0) == zoom.DEFAULT_CENTER


def test_load_faces_skips_empty(tmp_path):
    p = tmp_path / "faces.csv"
    p.write_text("t,cx,cy\n0.0,0.5,0.4\n0.1,,\n")
    assert zoom.load_faces(p) == [(0.0, 0.5, 0.4)]


def test_spans_from_cutlist_with_speedup():
    cl = {"segments": [{"start": 0, "end": 2, "action": "keep"}, {"start": 2, "end": 5, "action": "cut"},
                       {"start": 5, "end": 9, "action": "speedup", "rate": 4}, {"start": 9, "end": 10, "action": "keep"}]}
    assert ins.spans_from_cutlist(cl) == [(0.0, 2.0), (2.0, 3.0), (3.0, 4.0)]


def AT(words):
    return lambda a: wmod.at(words, a)


def test_resolve_kinds_and_length_warning(words):
    items = [{"kind": "broll", "from": "одну", "to": {"word": "кода,"}, "file": "/x/a.mp4", "in": 3.0, "layout": "half"},
             {"kind": "card", "template": "cta", "from": "Напиши", "to": 999},
             {"kind": "missing", "at": "Сервер", "want": "сервер в стойке"}]
    brolls, cards, missing, problems = ins.resolve(items, AT(words), 30.0)
    assert len(brolls) == 1 and len(cards) == 1 and len(missing) == 1
    assert cards[0]["b"] == 30.0
    assert brolls[0]["src_window"][0] == 3.0
    assert any(p["level"] == "warn" and "ориентира" in p["text"] for p in problems)


def test_overlap_is_error(words):
    items = [{"kind": "broll", "from": 1.0, "to": 2.0, "file": "/a.mp4"},
             {"kind": "broll", "from": 1.5, "to": 2.5, "file": "/b.mp4"}]
    _, _, _, problems = ins.resolve(items, AT(words), 30.0)
    assert any(p["level"] == "error" and "налезают" in p["text"] for p in problems)


def test_private_window_from_library_is_error_transition_is_warn(words, tmp_path):
    lib = {"assets": [{"id": "term", "kind": "broll", "duration": 30.0, "files": {"mp4": "term.mp4"},
                       "private": [{"from": 12.6, "to": 21.6, "what": "IP в заголовке"}],
                       "transitions": [[5.0, 5.4]]}]}
    items = [{"kind": "broll", "from": 1.0, "to": 2.0, "asset": "term", "in": 12.0},
             {"kind": "broll", "from": 3.0, "to": 4.0, "asset": "term", "in": 4.8},
             {"kind": "broll", "from": 5.0, "to": 6.0, "asset": "term", "in": 29.5}]
    brolls, _, _, problems = ins.resolve(items, AT(words), 30.0, lib, tmp_path)
    assert brolls[0]["path"] == tmp_path / "term.mp4"
    texts = [(p["level"], p["text"]) for p in problems]
    assert any(lv == "error" and "приватное" in t for lv, t in texts)
    assert any(lv == "warn" and "переходе" in t for lv, t in texts)
    assert any(lv == "error" and "ассет 30.0" in t for lv, t in texts)


def test_unknown_asset_is_error(words):
    _, _, _, problems = ins.resolve([{"kind": "broll", "from": 1.0, "to": 2.0, "asset": "nope"}],
                                    AT(words), 30.0, {"assets": []}, "/lib")
    assert any("нет ассета" in p["text"] for p in problems)


def test_half_windows_merge_and_coverage(words):
    items = [{"kind": "broll", "from": 1.0, "to": 2.0, "file": "/a", "layout": "half"},
             {"kind": "broll", "from": 2.0, "to": 3.0, "file": "/b", "layout": "half"},
             {"kind": "broll", "from": 5.0, "to": 6.0, "file": "/c"}]
    brolls, *_ = ins.resolve(items, AT(words), 30.0)
    assert ins.half_windows(brolls) == [[1.0, 3.0]]
    assert ins.coverage(brolls, 30.0) == pytest.approx(3.0)


def test_relative_file_found_in_search_dirs(words, tmp_path):
    (tmp_path / "b.mp4").write_bytes(b"x")
    brolls, *_ = ins.resolve([{"kind": "broll", "from": 1.0, "to": 2.0, "file": "b.mp4"}], AT(words), 30.0,
                             search_dirs=[tmp_path / "none", tmp_path])
    assert brolls[0]["path"] == tmp_path / "b.mp4"
