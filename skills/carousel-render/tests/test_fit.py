import pytest

import build_html
import fit
import theme


@pytest.fixture
def data(theme_file):
    return theme.load(theme_file)


def test_size_keys_is_shared_with_build_html():
    """Один источник истины: дублировать словарь между модулями нельзя."""
    assert fit.SIZE_KEYS is build_html.SIZE_KEYS


def test_sizes_for_cover_takes_both_keys(data):
    got = fit.sizes_for(data, "обложка", 0)
    assert got == {"заголовок": 200, "подзаголовок": 56}


def test_sizes_for_second_step_is_smaller(data):
    first = fit.sizes_for(data, "обложка", 0)
    second = fit.sizes_for(data, "обложка", 1)
    assert second["заголовок"] < first["заголовок"]


def test_sizes_for_body_list_uses_own_scale(data):
    assert fit.sizes_for(data, "тело-список", 0) == {"тело_список": 42}


def test_sizes_for_index_beyond_range_raises(data):
    with pytest.raises(IndexError):
        fit.sizes_for(data, "тело", 3)


def test_shortfall_zero_when_fits():
    assert fit.shortfall_chars(0, 70, 34) == 0


def test_shortfall_counts_whole_lines():
    """Переполнение в полторы строки — резать надо две строки."""
    assert fit.shortfall_chars(105, 70, 34) == 68


def test_shortfall_rounds_partial_line_up():
    assert fit.shortfall_chars(10, 70, 34) == 34


def test_shortfall_survives_zero_line_height():
    """Не делим на ноль, если замер не удался."""
    assert fit.shortfall_chars(100, 0, 34) == 0


def test_step_count_reads_theme(data):
    assert fit.step_count(data, "тело") == 3


def test_fit_slide_returns_first_step_when_it_fits(data, theme_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(fit.render, "measure",
                        lambda *a, **k: {"overflow_px": 0, "line_height_px": 70})
    slide = {"№": 2, "лейаут": "тело", "блоки": ["Коротко."]}
    got = fit.fit_slide(slide, data, "LI", theme_dir, tmp_path)
    assert got["ступень"] == 0
    assert got["переполнение"] == 0
    assert got["недобор_символов"] == 0
    assert got["html"].exists()


def test_fit_slide_steps_down_until_it_fits(data, theme_dir, tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_measure(*a, **k):
        calls["n"] += 1
        return {"overflow_px": 0 if calls["n"] >= 3 else 200, "line_height_px": 70}

    monkeypatch.setattr(fit.render, "measure", fake_measure)
    slide = {"№": 2, "лейаут": "тело", "блоки": ["Длинно " * 80]}
    got = fit.fit_slide(slide, data, "LI", theme_dir, tmp_path)
    assert got["ступень"] == 2
    assert got["переполнение"] == 0


def test_fit_slide_reports_shortfall_when_no_step_fits(data, theme_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(fit.render, "measure",
                        lambda *a, **k: {"overflow_px": 140, "line_height_px": 70})
    slide = {"№": 4, "лейаут": "тело", "блоки": ["Очень длинно " * 100]}
    got = fit.fit_slide(slide, data, "LI", theme_dir, tmp_path)
    assert got["ступень"] == 2
    assert got["переполнение"] == 140
    assert got["недобор_символов"] > 0


def test_fit_slide_html_reflects_chosen_step(data, theme_dir, tmp_path, monkeypatch):
    """Финальный HTML должен быть собран на той ступени, которую выбрали."""
    monkeypatch.setattr(fit.render, "measure",
                        lambda *a, **k: {"overflow_px": 500, "line_height_px": 70})
    slide = {"№": 2, "лейаут": "тело", "блоки": ["Длинно"]}
    got = fit.fit_slide(slide, data, "LI", theme_dir, tmp_path)
    smallest = theme.steps(data, "тело")[-1]
    assert f"--тело: {smallest}px" in got["html"].read_text(encoding="utf-8")
