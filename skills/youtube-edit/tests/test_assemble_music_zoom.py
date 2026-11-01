"""Таймлайн FCPXML, подложка музыки, зум на голове — без рендера."""
from fractions import Fraction
from pathlib import Path

import pytest
from conftest import cutlist_doc

import assemble
import head_zoom
import music
import timeline


def secs(rt):
    return float(Fraction(rt[:-1]))


def item(name, start, dur, typ="Д", lane=2):
    return {"name": name, "type": typ, "start": start, "dur": dur, "lane": lane, "path": Path(f"/tmp/{name}.mp4"),
            "audio": typ != "З", "what": name}


@pytest.fixture
def no_probe(monkeypatch):
    monkeypatch.setattr(assemble, "probe", lambda p: (100.0, True))


def test_connected_clip_offset_in_parent_time(no_probe):
    d = cutlist_doc([(0, 10), (12, 20)], 20)
    sp = timeline.spans(d)
    fx = assemble.fcpxml(d, sp, [item("a", 11.0, 2.0)], None, "t")
    spine = fx.find(".//spine")
    parents = spine.findall("asset-clip")
    assert len(parents) == 2
    second = parents[1]
    assert secs(second.get("offset")) == pytest.approx(10.0) and secs(second.get("start")) == pytest.approx(12.0)
    g = second.find("asset-clip")
    assert g.get("lane") == "2"                                # lane 1 — зум (V2), 2 — графика (V3), 3 — акценты (V4)
    assert secs(g.get("offset")) == pytest.approx(13.0)        # 12 + (11 − 10): время родителя
    assert g.find("marker").get("value").startswith("01 сцена")


def test_times_on_frame_grid(no_probe):
    d = cutlist_doc([(0, 10.013), (12, 20)], 20)
    fx = assemble.fcpxml(d, timeline.spans(d), [], None, "t")
    for c in fx.iter("asset-clip"):
        for k in ("offset", "start", "duration"):
            num, den = Fraction(c.get(k)[:-1]).limit_denominator(100000).as_integer_ratio()
            assert (Fraction(num, den) * 30).denominator == 1


def test_separate_audio_and_music_lanes(no_probe):
    d = cutlist_doc([(0, 10), (12, 20)], 20, audio="/tmp/obs.wav", offset=0.5)
    fx = assemble.fcpxml(d, timeline.spans(d), [], Path("/tmp/bed.wav"), "t")
    first = fx.find(".//spine/asset-clip")
    src = next(a for a in fx.iter("asset") if a.get("id") == "r2")
    assert src.get("hasAudio") is None                        # звук монтажа — отдельная запись, не камера
    lanes = {c.get("lane"): c for c in first.findall("asset-clip")}
    assert secs(lanes["-1"].get("start")) == pytest.approx(0.5)
    assert secs(lanes["-2"].get("duration")) == pytest.approx(18.0)


def test_speedup_refused(no_probe):
    d = cutlist_doc([(0, 20)], 20)
    sp = [(0, 5, 0, 10, 2.0)]
    with pytest.raises(SystemExit):
        assemble.fcpxml(d, sp, [], None, "t")


def test_fit_trims_tail_on_same_lane_only():
    its, warn = assemble.fit([item("a", 0, 5), item("b", 4, 3), item("z", 1, 10, "З", 1)])
    by = {c["name"]: c for c in its}
    assert by["a"]["dur"] == 4 and by["z"]["dur"] == 10 and warn


def test_range_shifts_spans_and_items():
    d = cutlist_doc([(0, 10), (12, 20)], 20)
    sp, its = assemble.in_range(timeline.spans(d), [item("a", 11.0, 9.0), item("b", 2.0, 1.0)], (9.0, 15.0))
    assert [(a, b) for a, b, *_ in sp] == [(0, 1.0), (1.0, 6.0)]
    assert sp[1][2] == 12.0
    assert [(c["name"], c["start"], c["dur"]) for c in its] == [("a", 2.0, 4.0)]


# ── музыка ──

def test_loop_count_covers_total():
    a, b, x = 24.75, 76.75, 4.0
    for total in (10, 60, 2400):
        n = music.loop_count(total, a, b, x)
        assert b + (n - 1) * (b - a - x) >= total


def test_recipe_precedence():
    sec = {"музыка": {"скринкаст": {"трек": "/m/a.mp3", "цикл": [1, 9], "уровень_LU_к_голосу": -30}}}
    r = music.recipe(sec, "скринкаст")
    assert r["трек"] == "/m/a.mp3" and r["цикл"] == [1, 9] and r["уровень_LU_к_голосу"] == -30 and r["подъём_в_паузах_dB"] == 0
    r = music.recipe(sec, "скринкаст", track="/m/b.mp3", rel=-25)
    assert "цикл" not in r and r["уровень_LU_к_голосу"] == -25           # чужой цикл к другому треку не относится
    assert music.recipe({}, "голова")["уровень_LU_к_голосу"] == -20


def test_chunk_cutlist_keeps_only_probe_piece():
    d = cutlist_doc([(0, 10), (12, 20)], 20)
    c = music.chunk_cutlist(d, 8.0, 4.0)
    assert [(s["start"], s["end"]) for s in c["segments"] if s["action"] == "keep"] == [(8.0, 10.0), (12.0, 14.0)]


# ── зум на голове ──

def test_regions_skip_opaque_graphics_only():
    clips = [{"type": "Д", "start": 20, "dur": 5, "layout": "full"}, {"type": "А", "start": 40, "dur": 5, "layout": "overlay"},
             {"type": "П", "start": 50, "dur": 10, "template": "wide_drawer", "layout": "full"}]
    regs = head_zoom.regions([(10, 70)], head_zoom.covers(clips))
    assert regs == [(10, 20, "cut", "full"), (25, 50, "full", "face"), (60, 70, "face", "cut")]


def test_plan_moves_every_piece_and_glides_to_panel():
    js, rows = head_zoom.plan(25.0, 50.0, "full", "face", cuts=[30.0, 40.0])
    assert len(rows) == 3
    levels = [float(r[2].split()[-1].split("→")[1]) for r in rows]
    assert all(abs(x - y) >= head_zoom.MIN_STEP - 1e-9 or "быстро" in r[2] for x, y, r in zip(levels, levels[1:], rows[1:]))
    assert "scale: 1.0" in js[-1]                              # к панели — к 1,00
