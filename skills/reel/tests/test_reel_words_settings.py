import os

import pytest

import settings
import words as wmod


def test_norm_strips_edges_keeps_inner_hyphen():
    assert wmod.norm("«Телеграм-канал»,") == "телеграм-канал"
    assert wmod.norm("Всё.") == "все"
    assert wmod.norm("-канал") == "канал"


def test_at_by_word_occurrence_and_shift(words):
    bez1 = wmod.find(words, "без")
    bez2 = wmod.find(words, "без", 2)
    assert bez2["start"] > bez1["start"]
    assert wmod.at(words, {"word": "Без", "n": 2, "shift": -0.1}) == round(bez2["start"] - 0.1, 3)
    assert wmod.at(words, {"word": "сервер", "edge": "end"}) == wmod.find(words, "сервер")["end"]
    assert wmod.at(words, 12.5) == 12.5
    assert wmod.at(words, "одну") == wmod.find(words, "одну")["start"]


def test_missing_word_says_how_many_found(words):
    with pytest.raises(KeyError, match="найдено вхождений: 2"):
        wmod.find(words, "без", 3)


def test_label():
    assert wmod.label({"word": "сервер", "n": 2}) == "«сервер»#2"
    assert wmod.label(3) == "3.00 с"


def test_resolve_maps_russian_keys(settings_file):
    s = settings.load(settings_file)
    assert s["captions"]["style"] == "word"
    assert s["captions"]["anim"] == "wave"
    assert s["captions"]["word_px"] == 80
    assert s["captions"]["top_px"] == 1250
    assert s["theme"]["font_main"] == settings_file.parent / "fonts" / "Main.ttf"
    assert s["theme"]["secondary"] == "#3366FF"
    assert s["folders"]["library"] == settings_file.parent / "lib"
    assert s["folders"]["brolls"] == [settings_file.parent / "brolls"]
    assert s["dictionary"] == {"лего": "СЛОВО"}
    assert s["edit"]["zoom_levels"] == [1.0, 1.2] and s["edit"]["punch_add"] == 0.1
    assert s["music"]["recipe"]["quiet_end"] == [32.0, 40.0] and s["music"]["recipe"]["min_start"] == 4.0
    assert s["lessons"] == settings_file.parent / "lessons.md"


def test_accent_gradient_falls_back_to_last_stop(settings_file):
    a = settings.load(settings_file)["theme"]["accent"]
    assert a["gradient"] == ["#00FFFF", "#AAFF00"]
    assert a["solid"] == "#AAFF00" and a["on_light"] == "#448800"


def test_accent_and_style_override_per_reel(settings_file):
    s = settings.load(settings_file, accent_name="плоский", caption_style="строки")
    assert s["theme"]["accent"]["solid"] == "#FF8800" and s["theme"]["accent"]["gradient"] is None
    assert s["captions"]["style"] == "lines" and s["captions"]["top_px"] == 1385


def test_find_order(tmp_path, settings_file, monkeypatch):
    monkeypatch.delenv("REEL_SETTINGS", raising=False)
    monkeypatch.setattr(settings, "load_env", lambda path=None: None)
    assert settings.find(cwd=tmp_path / "nowhere") is None
    studio = tmp_path / "studio"
    (studio / "reel").mkdir(parents=True)
    (studio / "reel" / "reel.settings.json").write_text("{}")
    assert settings.find(cwd=studio) == studio / "reel" / "reel.settings.json"
    monkeypatch.setenv("REEL_SETTINGS", str(settings_file))
    assert settings.find(cwd=studio) == settings_file
    assert settings.find("/x/y.json") == settings.Path("/x/y.json")


def test_default_is_neutral():
    s = settings.default()
    assert s["path"] is None and s["captions"]["style"] == "lines"
    assert s["theme"]["font_main"] is None


def test_load_env_does_not_override(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("REEL_SETTINGS=/from/file\n# коммент\n")
    monkeypatch.setenv("REEL_SETTINGS", "/from/shell")
    settings.load_env(env)
    assert os.environ["REEL_SETTINGS"] == "/from/shell"
