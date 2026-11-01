"""Каркас сцен: якоря, разбор JS, out() без вспышки, fitted, шаблоны, образец сцен."""
import importlib.util
import json
from pathlib import Path

import pytest

import stage

ASSETS = Path(__file__).resolve().parents[1] / "assets"


@pytest.fixture
def words(example_words, tmp_path):
    (tmp_path / "words.json").write_text(json.dumps(example_words, ensure_ascii=False), encoding="utf-8")
    stage.init(tmp_path, settings_path=str(tmp_path / "нет.json"))
    stage.LEAD.clear()
    return stage.WORDS


def test_anchor_by_number_prefix_and_inside(words):
    assert words.k(15, "одной") == 2
    assert words.k(15, 99) == 3                                # за концом — последнее
    assert words.k(17, "автоматиз") == 9
    assert stage.at(15, "одной") == 50.86
    with pytest.raises(KeyError):
        words.k(15, "нет-такого")


def test_cut_word_falls_back_to_nearest_and_is_reported():
    w = stage.Words([{"n": 1, "words": [["раз", 1.0, 1.4], ["два", None, None], ["три", 3.0, 3.3]]}])
    assert w.t(1, 1) == 1.4                                    # ближе предыдущее — его конец
    assert w.misses and w.misses[0][2] == "два"


def test_out_goes_from_current_opacity():
    assert 'const out = (sel, at, d = 0.2) => tl.to(sel, { opacity: 0' in stage.JS_BASE
    assert "fromTo(sel, { opacity: 1" not in stage.JS_BASE


def test_first_content_skips_cursor_veil_and_base():
    js = [stage.JS_BASE, 'tl.set("#cur", { x: 1, y: 2 }, 0);', 'fade("#cur", 0.200, 0.15);', 'popIn("#win", 0.100, 0.3);',
          'popIn("#a", 2.400, 0.26);', 'fade("#veil", 0.0, 0.3);']
    assert stage.first_content(js) == 2.4


def test_idle_gaps_and_beats_close_them(words):
    s = stage.Ins("x", 10.0, "full")
    s.add('<div id="a"></div>', "a").pop("#a", 0.5)
    sc = s.done(8.0)
    assert stage.idle_gaps(sc) == [(0.76, 8.0)]
    s = stage.Ins("x", 10.0, "full")
    s.add('<div id="a"></div>', "a").pop("#a", 0.5)
    for t in (2.2, 3.9, 5.6, 7.2):
        s.mark("#a", t)
    assert stage.idle_gaps(s.done(8.0)) == []


def test_fitted_moves_start_to_first_element(words):
    def scene():
        s = stage.Ins("late", stage.at(15, 0), "full")
        s.add('<div id="a"></div>', "a").pop("#a", s.t(16, "копируете"))
        return s.done(s.t(17, 0))
    sc, shift = stage.fitted(scene)
    assert shift == pytest.approx(54.0 - 49.72 - 0.35, abs=0.01)
    assert stage.first_content(sc["js"]) == pytest.approx(0.35, abs=0.01)


def test_rel_times_and_drawer(words):
    t = stage.Tpl("c", "wide_chips", 10.0, {"items": [{"label": "a", "at": 11.5}], "duration": 3.0})
    assert t.slots["items"][0]["at"] == 1.5 and t.slots["duration"] == 3.0 and t.layout == "overlay"
    d = stage.drawer("p", 10.0, 30.0, [{"at": 10.5, "type": "list", "items": [{"title": "x", "at": 12.0}]},
                                       {"at": 20.0, "type": "message", "reply_at": 25.0}])
    assert d.layout == "full" and d.face
    assert d.slots["open_at"] == 0.25 and d.slots["close_at"] == 19.5
    assert d.slots["groups"][1]["reply_at"] == 15.0


def test_project_over_baked_or_transparent(words, tmp_path):
    s = stage.Ins("o", 1.0, "over", veil="light")
    s.add('<div id="a"></div>', "a").pop("#a", 0.5)
    sc = s.done(3.0)
    stage.project(sc, tmp_path / "o")
    html = (tmp_path / "o" / "index.html").read_text(encoding="utf-8")
    assert 'id="veil"' in html and "background: transparent" in html and 'class="bg"' not in html
    stage.project(sc, tmp_path / "b", "bg-1.00-3.30-q10.mp4")
    html = (tmp_path / "b" / "index.html").read_text(encoding="utf-8")
    assert 'id="bgv" src="bg-1.00-3.30-q10.mp4"' in html and html.index('id="bgv"') < html.index('id="veil"')
    assert json.loads((tmp_path / "b" / "scene.json").read_text(encoding="utf-8"))["baked"] is True


def test_example_scenes_build(words, tmp_path):
    spec = importlib.util.spec_from_file_location("scenes_example", ASSETS / "scenes.example.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    kinds = {}
    for fn in mod.SCENES:
        sc, _ = stage.fitted(fn)
        kinds[sc["name"]] = sc["kind"]
        assert stage.brief(sc) == [], sc["name"]
        if sc["kind"] != "tpl":
            assert stage.idle_gaps(sc, 2.0) == [], sc["name"]
            stage.project(sc, tmp_path / sc["name"])
    assert kinds == {"install": "full", "p-video": "tpl", "tools": "tpl", "flexible": "over"}
    assert not stage.WORDS.misses


def test_brief_catches_late_elements(words):
    s = stage.Ins("b", 0.0, "full")
    s.add('<div id="a"></div><div id="b"></div>', "a", "b").pop("#a", 0.5).pop("#b", 4.6).out("#a", 3.0)
    assert stage.brief(s.done(5.0)) == [("#b", 4.6, 0.4)]
    t = stage.Tpl("c", "wide_chips", 0.0, {"items": [{"at": 1.0}, {"at": 8.2}], "duration": 8.9})
    assert stage.brief(t.spec()) and not stage.brief(stage.Tpl("c", "wide_chips", 0.0, {"items": [{"at": 1.0}], "duration": 3.0}).spec())
